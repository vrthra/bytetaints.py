import fn
import dis

fn.Instrument.add_source(input)
fn.Instrument.add_sink(print)
def cleaner(a):
    return a
fn.Instrument.add_cleaner(cleaner)

def x(a, b):
    z = a + (b * 10)
    return z


def main(args):
    a = input()
    # this will fail
    #print(">", a)
    b = ' world'
    z = x(a,b)
    print("> %s" % cleaner(z))
    z = x(a,b)
    print("> %s" % z)


if __name__ == '__main__':
    try:
        fn.Instrument.i(main)([])
    except fn.TaintEx as err:
        print("Tainted: {0}".format(err))
