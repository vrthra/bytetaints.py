import fn
import dis
def x_(a, b):
    y = a + (b * 10)
    return y
mx_ = fn.Instrument.i(x_)
a = 100
fn.Instrument.mark(a)
r = mx_(a,200)
print("Tainted: %s" % fn.Instrument.is_tainted(r))

def y_(a):
    y = -a
    return y
my_ = fn.Instrument.i(y_)
a = 200
fn.Instrument.mark(a)
r = my_(a)
print(r)
print("Tainted: %s" % fn.Instrument.is_tainted(r))

def g(a, b):
    return a + b

def f(a, b):
    y = g(a, b)
    x = g(b, a)
    return x + y
 
m1 = fn.Instrument.i(f)
a = 100
b = 200
fn.Instrument.mark(a)
r = m1(a, b)
print(r)
print("Tainted: %s" % fn.Instrument.is_tainted(r))
