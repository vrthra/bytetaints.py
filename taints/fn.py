# vim: set nospell:
# TODO: consider using xdis rather than munge it myself.

import dis
import types


class Function:
    """
    Make modifying functions a little nicer.
    """

    def __init__(self, func):
        self.func = func
        self.docstring = func.__doc__
        self.consts = list(func.__code__.co_consts[1:])
        self.co_names = list(func.__code__.co_names)
        self.co_varnames = list(func.__code__.co_varnames)
        self.parse_bytecode()
        self.update_bytecode()

    def parse_bytecode(self):
        self.opcodes = list(dis.get_instructions(self.func.__code__))

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
        return self.func.__name__

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
#cmpops = {
#          # cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn
#          'Eq': lambda a, b: a == b,
#          'NotEq': lambda a, b: a != b,
#          'Lt': lambda a, b: a < b,
#          'LtE': lambda a, b: a <= b,
#          'Gt': lambda a, b: a > b,
#          'GtE': lambda a, b: a >= b,
#          'Is': lambda a, b: a is b,
#          'IsNot': lambda a, b: a is not b,
#          'In': lambda a, b: a in b,
#          'NotIn': lambda a, b: a not in b
#          }
#boolops = {
#          # boolop = And | Or
#          'And': lambda a, b: a and b,
#          'Or': lambda a, b: a or b
#        }

def __call(fn, tupl):
    global tainted
    if type(fn) is "<class 'builtin_function_or_method'>":
        # TODO: for each builtin used, define the taint semantics
        # and use it here.
        for i in tupl:
            v = fn(*tupl)
            if id(i) in tainted:
                tainted[id(v)] = True
            return v
    else:
        # if not built in, we should use the instrumented version.
        # The instrumentation takes care of propagating taints
        return Instrument.i(fn)(*tupl)

def __unary(a, op):
    global tainted
    v = unaryops[op](a)
    if id(a) in tainted:
        tainted[id(v)] = True
    return v

def __bin(a,b, op):
    global tainted
    v = binops[op](a,b)
    if id(a) in tainted or id(b) in tainted:
        tainted[id(v)] = True
    return v

class Instrument:
    cache = {}
    def i_(self, opname, arg=None, argval=None, argrepr=''):
        if arg is not None and argval is None: argval = arg
        return dis.Instruction(opname=opname, opcode=dis.opmap[opname],
                        arg=arg, argval=argval, argrepr=argrepr,
                        offset=0, starts_line=None, is_jump_target=False)

    def i_global(self):      return self.i_('LOAD_GLOBAL', len(self.fn.co_names) - 2, 'fn')
    def i_attr(self, attr):  return self.i_('LOAD_ATTR', len(self.fn.co_names) - 1, attr)
    def i_rot3(self):        return self.i_('ROT_THREE')
    def i_rot2(self):        return self.i_('ROT_TWO')
    def i_call(self, nargs): return self.i_('CALL_FUNCTION', nargs)
    def i_const(self, op):   return self.i_('LOAD_CONST', len(self.fn.consts), op, "'%s'" % op)
    def i_tuple(self, nargs):return self.i_('BUILD_TUPLE', nargs)

    @classmethod
    def i(cls, func):
        if func.__name__ in Instrument.cache:
            return Instrument.cache[func.__name__]
        ins = Instrument(func)
        Instrument.cache[func.__name__] = ins.function
        return Instrument.cache[func.__name__]

    def __init__(self, func):
        self.fn = Function(func)
        lst = []
        for i in self.fn.opcodes:
            op = i.opname
            if op in binops:
                self.fn.co_names.extend(['fn', '__bin'])
                self.fn.consts.append(op)
                lst.extend([self.i_global(), self.i_attr('__bin'), self.i_rot3(), self.i_const(op), self.i_call(3)])
            elif i.opname in unaryops:
                self.fn.co_names.extend(['fn', '__unary'])
                self.fn.consts.append(op)
                lst.extend([self.i_global(), self.i_attr('__unary'), self.i_rot2(), self.i_const(op), self.i_call(2)])
            elif i.opname == 'CALL_FUNCTION':
                nargs = i.arg
                self.fn.co_names.extend(['fn', '__call'])
                self.fn.consts.append(op)
                lst.extend([self.i_tuple(nargs), self.i_global(), self.i_attr('__call'), self.i_rot3(), self.i_call(2)])
            else:
                lst.append(i)

        self.fn.opcodes = lst
        self.fn.update_bytecode()
        self.function = self.fn.build()

