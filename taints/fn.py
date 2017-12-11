# vim: set nospell:
# based on mutant by "Michael Stephens <me@mikej.st>" BSD License
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

__tainted = {}

def __add(a,b):
    global __tainted
    v = a+b
    if id(a) in __tainted or id(b) in __tainted:
        __tainted[id(v)] = True
    return v
def __sub(a,b):
    global __tainted
    v = a - b
    if id(a) in __tainted or id(b) in __tainted:
        __tainted[id(v)] = True
    return v


class Instrument:
    def __init__(self, func):
        self.fn = Function(func)
        lst = []
        for i in self.fn.opcodes:
            if i.opname == 'BINARY_ADD':
                self.fn.co_names.append('__add',)
                add = dis.Instruction(opname='LOAD_GLOBAL', opcode=116, arg=len(self.fn.co_names) - 1, argval='__add', argrepr='__add', offset=0, starts_line=2, is_jump_target=False)
                rot = dis.Instruction(opname='ROT_THREE', opcode=3, arg=None, argval=None, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                call = dis.Instruction(opname='CALL_FUNCTION', opcode=131, arg=2, argval=2, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                lst.extend([add, rot, call])
            elif i.opname == 'BINARY_SUBTRACT':
                self.fn.co_names.append('__sub',)
                add = dis.Instruction(opname='LOAD_GLOBAL', opcode=116, arg=len(self.fn.co_names) - 1, argval='__sub', argrepr='__sub', offset=0, starts_line=2, is_jump_target=False)
                rot = dis.Instruction(opname='ROT_THREE', opcode=3, arg=None, argval=None, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                call = dis.Instruction(opname='CALL_FUNCTION', opcode=131, arg=2, argval=2, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                lst.extend([add, rot, call])
            else:
                lst.append(i)
        self.fn.opcodes = lst
        self.fn.update_bytecode()
        self.x = self.fn.build()


def g(a, b):
   y = a - b
   return y

def f(a, b):
   y = a + b
   return y

m1 = Instrument(f)
dis.dis(m1.x)
a = 100
b = 200
__tainted[id(a)] = True
r = m1.x(a, b)
print("Tainted: %s" % (id(r) in __tainted))
print("_"*10)
__tainted = {}
m2 = Instrument(g)
dis.dis(m2.x)
r = m2.x(2, 1)
print("Tainted: %s" % (id(r) in __tainted))

