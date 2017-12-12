# vim: set nospell:
# TODO: consider using xdis rather than munge it myself.

import dis
import types

class TaintEx(AssertionError):
    def __init__(self, err):
        self.err = err

class Function:
    def __init__(self, func):
        #import pudb; pudb_set.trace()
        self.func = func
        self.docstring = func.__doc__
        self.consts = list(func.__code__.co_consts[1:])
        self.co_names = list(func.__code__.co_names)
        self.co_varnames = list(func.__code__.co_varnames)
        self.opcodes = list(dis.get_instructions(self.func.__code__))
        self.update_bytecode()

    def update_bytecode(self):
        self.ops = [x.opcode for x in self.opcodes]
        self.args = [x.arg for x in self.opcodes]

    def build(self):
        code = bytes([i if i is not None else 0 for i in sum(zip(self.ops, self.args), ())])
        consts = [self.docstring]
        consts.extend(self.consts)
        fc = self.func.__code__ if type(self.func) == types.FunctionType else self.func.im_func.__code__
        newfc = type(fc)(fc.co_argcount, fc.co_kwonlyargcount, fc.co_nlocals, fc.co_stacksize,
                         fc.co_flags, code, tuple(consts), tuple(self.co_names),
                         tuple(self.co_varnames), fc.co_filename, fc.co_name,
                         fc.co_firstlineno, fc.co_lnotab, fc.co_freevars,
                         fc.co_cellvars)

        new_func = types.FunctionType(newfc, self.func.__globals__,
                                      name=self.func.__name__,
                                      argdefs=self.func.__defaults__,
                                      closure=self.func.__closure__)

        if type(self.func) == types.MethodType:
            new_func = types.MethodType(new_func, None, self.func.im_class)
        return new_func

    def name(self):
        return self.func.__qualname__

tainted = {}
binops = {
          'BINARY_ADD': lambda a, b: a + b,
          'BINARY_SUBTRACT': lambda a, b: a - b,
          'BINARY_MULTIPLY':  lambda a, b: a * b,
          'BINARY_MATRIX_MULTIPLY':  lambda a, b: a @ b,
          'BINARY_TRUE_DIVIDE': lambda a, b: a / b,
          'BINARY_MODULO': lambda a, b: a % b,
          'BINARY_POWER': lambda a, b: a ** b,
          'BINARY_LSHIFT':  lambda a, b: a << b,
          'BINARY_RSHIFT': lambda a, b: a >> b,
          'BINARY_OR': lambda a, b: a | b,
          'BINARY_XOR': lambda a, b: a ^ b,
          'BINARY_AND': lambda a, b: a & b,
          'BINARY_FLOOR_DIVIDE': lambda a, b: a // b,
          }
unaryops = {
          'UNARY_POSITIVE': lambda a: a,
          'UNARY_NEGATIVE': lambda a: -a,
          'UNARY_NOT': lambda a: not a,
          'UNARY_INVERT': lambda a: ~a
        }

def __call(fn, tupl):
    return Instrument.i(fn)(*tupl)

def __unary(a, op):
    v = unaryops[op](a)
    if Instrument.is_tainted(a):
        Instrument.mark(v)
    return v

def __bin(a,b, op):
    v = binops[op](a,b)
    if Instrument.is_tainted((a, b)):
        Instrument.mark(v)
    return v

class Instrument:
    cache = {}
    sources = {}
    sinks = {}
    cleaners = {}
    def i_(self, opname, arg=None, argval=None, argrepr=''):
        if arg is not None and argval is None: argval = arg
        return dis.Instruction(opname=opname, opcode=dis.opmap[opname],
                        arg=arg, argval=argval, argrepr=argrepr,
                        offset=0, starts_line=None, is_jump_target=False)

    def i_load_global(self):          return self.i_('LOAD_GLOBAL', len(self.fn.co_names) - 2, 'fn')
    def i_load_attr(self, attr):      return self.i_('LOAD_ATTR', len(self.fn.co_names) - 1, attr)
    def i_rot_three(self):            return self.i_('ROT_THREE')
    def i_rot_two(self):              return self.i_('ROT_TWO')
    def i_call_function(self, nargs): return self.i_('CALL_FUNCTION', nargs)
    def i_load_const(self, op):       return self.i_('LOAD_CONST', len(self.fn.consts), op, "'%s'" % op)
    def i_build_tuple(self, nargs):   return self.i_('BUILD_TUPLE', nargs)

    @classmethod
    def mark(cls, i):
        global tainted
        tainted[id(i)] = True

    @classmethod
    def unmark(cls, i):
        global tainted
        if id(i) in tainted:
            del tainted[id(i)]

    @classmethod
    def add_source(cls, func):
        cls.sources[func.__qualname__] = True
        return Instrument.i(func)
    @classmethod
    def add_sink(cls, func):
        cls.sinks[func.__qualname__] = True
        return Instrument.i(func)
    @classmethod
    def add_cleaner(cls, func):
        cls.cleaners[func.__qualname__] = True
        return Instrument.i(func)

    @classmethod
    def is_tainted(cls, obj):
        global tainted
        if id(obj) in tainted: return True
        elif isinstance(obj, dict):
           for k,v in obj.items():
               if cls.is_tainted(k) or cls.is_tainted(v): return True 
        elif isinstance(obj, tuple):
           for v in obj:
               if cls.is_tainted(v): return True 
        elif isinstance(obj, list):
           for v in obj:
               if cls.is_tainted(v): return True
        else:
           return False

    @classmethod
    def i(cls, func):
        if func.__qualname__ in cls.sources:
            def myfun(*tupl):
                """ MyFun Sources %s """ % func.__qualname__
                # a source will always taint its output. So no instrumentation
                # necessary.
                v = func(*tupl)
                cls.mark(v)
                return v
            return myfun
        elif func.__qualname__ in cls.cleaners:
            def myfun(*tupl):
                """ MyFun Cleaners %s """ % func.__qualname__
                # a cleaner cleans up what ever gets passed in. Its results are
                # always untainted
                v = func(*tupl)
                cls.unmark(v)
                return v
            return myfun
        elif func.__qualname__ in cls.sinks:
            def myfun(*tupl):
                """ MyFun Sinks %s """ % func.__qualname__
                if Instrument.is_tainted(tupl):
                    raise TaintEx('Tainted data reached sink: %s(%s)' % (func.__qualname__, str(tupl)))
                # none of the arguments were tainted. Hence there is no point
                # in instrumenting the remaining call chain.
                return func(*tupl)
            return myfun

        elif func.__qualname__ in Instrument.cache:
            # TODO for students. We need to use the instrumented version only until
            # we have figured out the semantics. The semantics is of the form
            # if any(tainted(a) in my_args): taint(result)
            # So if one of the arguments previously known to propagate taint to
            # result is tainted, then the result is tainted, and we can return
            # 'result is_tainted' after running the native function.
            # similarly, we can mark result not tainted if we have complete branch
            # coverage (which is sufficient for taint inference -- TODO to explain)
            # and none of the previous taing propagator arguments are tainted
            # and execute the native version.
            return Instrument.cache[func.__qualname__].function
        elif str(type(func)) == "<class 'builtin_function_or_method'>":
            def myfun(*tupl):
                v = func(*tupl)
                if Instrument.is_tainted(tupl):
                    Instrument.mark(v)
                return v
            return myfun
        ins = Instrument(func)
        Instrument.cache[func.__qualname__] = ins
        return Instrument.cache[func.__qualname__].function

    def __init__(self, func):
        self.fn = Function(func)
        lst = []
        for i in self.fn.opcodes:
            op = i.opname
            if op in binops:
                self.fn.co_names.extend(['fn', '__bin'])
                self.fn.consts.append(op)
                lst.extend([self.i_load_global(),
                            self.i_load_attr('__bin'),
                            self.i_rot_three(),
                            self.i_load_const(op),
                            self.i_call_function(3)])
            elif i.opname in unaryops:
                self.fn.co_names.extend(['fn', '__unary'])
                self.fn.consts.append(op)
                lst.extend([self.i_load_global(),
                            self.i_load_attr('__unary'),
                            self.i_rot_two(),
                            self.i_load_const(op),
                            self.i_call_function(2)])
            elif i.opname == 'CALL_FUNCTION':
                nargs = i.arg
                self.fn.co_names.extend(['fn', '__call'])
                self.fn.consts.append(op)
                lst.extend([self.i_build_tuple(nargs),
                            self.i_load_global(),
                            self.i_load_attr('__call'),
                            self.i_rot_three(),
                            self.i_call_function(2)])
            else:
                lst.append(i)

        self.fn.opcodes = lst
        self.fn.update_bytecode()
        self.function = self.fn.build()

