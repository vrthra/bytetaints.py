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
    def __init__(self, func):
        self.fn = Function(func)
        lst = []
        for i in self.fn.opcodes:
            if i.opname in binops:
                op = i.opname
                self.fn.co_names.extend(['fn', '__bin'])
                self.fn.consts.append(op)
                glob  = dis.Instruction(opname='LOAD_GLOBAL', opcode=116,
                        arg=len(self.fn.co_names) - 2, argval='fn', argrepr='fn', offset=0, starts_line=0, is_jump_target=False)
                attr = dis.Instruction(opname='LOAD_ATTR', opcode=106,
                        arg=len(self.fn.co_names) - 1, argval='__bin', argrepr='__bin', offset=2, starts_line=None, is_jump_target=False)
                rot  = dis.Instruction(opname='ROT_THREE', opcode=3,
                        arg=None, argval=None, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                con1 = dis.Instruction(opname='LOAD_CONST', opcode=100,
                        arg=len(self.fn.consts), argval=op, argrepr="'%s'" % op, offset=8, starts_line=None, is_jump_target=False)
                call = dis.Instruction(opname='CALL_FUNCTION', opcode=131,
                        arg=3, argval=3, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                lst.extend([glob, attr, rot, con1, call])
            elif i.opname in unaryops:
                op = i.opname
                self.fn.co_names.extend(['fn', '__unary'])
                self.fn.consts.append(op)
                glob  = dis.Instruction(opname='LOAD_GLOBAL', opcode=116,
                        arg=len(self.fn.co_names) - 2, argval='fn', argrepr='fn', offset=0, starts_line=0, is_jump_target=False)
                attr = dis.Instruction(opname='LOAD_ATTR', opcode=106,
                        arg=len(self.fn.co_names) - 1, argval='__unary', argrepr='__unary', offset=2, starts_line=None, is_jump_target=False)
                rot  = dis.Instruction(opname='ROT_TWO', opcode=2,
                        arg=None, argval=None, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                con1 = dis.Instruction(opname='LOAD_CONST', opcode=100,
                        arg=len(self.fn.consts), argval=op, argrepr="'%s'" % op, offset=8, starts_line=None, is_jump_target=False)
                call = dis.Instruction(opname='CALL_FUNCTION', opcode=131,
                        arg=2, argval=2, argrepr='', offset=6, starts_line=None, is_jump_target=False)
                lst.extend([glob, attr, rot, con1, call])
            else:
                lst.append(i)
        self.fn.opcodes = lst
        self.fn.update_bytecode()
        self.function = self.fn.build()

