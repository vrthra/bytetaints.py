import fn
import dis
def x_(a, b):
    y = a + (b * 10)
    return y
mx_ = fn.Instrument.i(x_)
a = 100
fn.tainted[id(a)] = True
r = mx_(a,200)
print("Tainted: %s" % (id(r) in fn.tainted))

def y_(a):
    y = -a
    return y
my_ = fn.Instrument.i(y_)
a = 200
fn.tainted[id(a)] = True
r = my_(a)
print("Tainted(%d): %s" % (r, id(r) in fn.tainted))

def g(a, b):
    return a + b

def f(a, b):
    y = g(a, b)
    x = g(b, a)
    return x + y
 
m1 = fn.Instrument.i(f)
a = 100
b = 200
fn.tainted[id(a)] = True
r = m1(a, b)
print(r)
print("Tainted(%d): %s" % (r, id(r) in fn.tainted))
