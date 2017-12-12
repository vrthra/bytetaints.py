import fn
import dis
# def x(a,b):
#     z = 100
#     y = fn.__bin(a,b, 'BINARY_ADD')
#     return y
# 
# dis.dis(x)
# mx = fn.Instrument(x)
# 
# print(mx.function(1,2))
# 
# 
# def x_(a, b):
#     y = a + (b * 10)
#     return y
# mx_ = fn.Instrument(x_)
# dis.dis(mx_.function)
# a = 100
# fn.tainted[id(a)] = True
# r = mx_.function(a,200)
# print("Tainted: %s" % (id(r) in fn.tainted))
# 
# def y_(a):
#     y = -a
#     return y
# my_ = fn.Instrument(y_)
# dis.dis(my_.function)
# a = 200
# fn.tainted[id(a)] = True
# r = my_.function(a)
# print("Tainted(%d): %s" % (r, id(r) in fn.tainted))

def g(a, b):
    return a + b

def f(a, b):
    y = g(a, b)
    return y
 
m1 = fn.Instrument(f)
dis.dis(m1.function)
a = 100
b = 200
fn.tainted[id(a)] = True
r = m1.function(a, b)
print(r)
print("Tainted(%d): %s" % (r, id(r) in fn.tainted))
