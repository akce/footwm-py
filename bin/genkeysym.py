#! /usr/bin/env python3

import os
import re
import sys

def parsexf86(xincludesdir):
    p = re.compile(r'#define XF86XK_([a-zA-Z_0-9]+)\s+0x([0-9a-fA-F]+)\s*')
    with open(os.path.join(xincludesdir, 'XF86keysym.h')) as f:
        for x in f:
            m = p.match(x)
            if m:
                yield "XF86{}".format(m.group(1)), int(m.group(2), 16)

def parsexorg(xincludesdir):
    p = re.compile(r'#define XK_([a-zA-Z_0-9]+)\s+0x([0-9a-f]+)\s*')
    with open(os.path.join(xincludesdir, 'keysymdef.h')) as f:
        for x in f:
            m = p.match(x)
            if m:
                yield m.group(1), int(m.group(2), 16)

def keymappairs(xincludesdir):
    ## Base X key defines.
    yield from parsexorg(xincludesdir)
    ## XF86 key extensions.
    yield from parsexf86(xincludesdir)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--xincludesdir', default='/usr/include/X11', help='X includes directory. Default: %(default)s')
    parser.add_argument('out', nargs='?', default='-', help='Output file. Default: stdout')
    args = parser.parse_args()
    if args.out == '-':
        p = print
    else:
        import functools
        p = functools.partial(print, file=open(args.out, 'w'))
    p('# Autogenerated by {}. DO NOT EDIT.'.format(sys.argv[0]))
    keypairs = [('NoSymbol', 0)] + [(key, num) for key, num in keymappairs(args.xincludesdir)]
    # Output the keysym ids dict.
    p('keysymids = dict([')
    for k, v in keypairs:
        p("        ('{}', 0x{:08x}),".format(k, v))
    p('        ])')
    # Output the keysym names dict.
    # Note that some keycodes have multiple keysyms!!
    # We'll keep only the first definition and discard the rest.
    keycodes = dict()
    p('keysymnames = dict([')
    for k, v in keypairs:
        if v in keycodes:
            msg = "keycode 0x{:08x} already has keysym {}. Ignoring new keysym {}".format(v, keycodes[v], k)
            print(msg, file=sys.stderr)
            p('# {}'.format(msg))
        else:
            p("        (0x{:08x}, '{}'),".format(v, k))
            keycodes[v] = k
    p('        ])')
