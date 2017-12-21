import sys
import fn
import dis

def myinput(): return 'hello'
def cleaner(a): return a
def log(v): print(v)

fn.Instrument.add_source(myinput)
fn.Instrument.add_sink(log)
fn.Instrument.add_cleaner(cleaner)

def x(a, b):
    z = a + (b * 10)
    if len(z) > 0:
        return a
    return z

def main(args):
    # this will fail
    #print(">", a)
    a = myinput()
    b = ' world'
    z = x(a,b)
    log("> %s" % cleaner(z))
    z = x(a,b)
    log("> %s" % z)


if __name__ == '__main__':
    try:
        # myinput() here will not taint.
        fn.Instrument.i(main)(sys.argv)
    except fn.TaintEx as err:
        print("Tainted: {0}".format(err))
