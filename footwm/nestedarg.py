"""
Nested sub-parser for use with argparse.

Creates a context manager so that argparse subparsers may be nested using 'with' statements.
This gives a visual indication for the hierarchy of command line options.

>>> parser = argparse.ArgumentParser()
... commands = NestedSubparser(parser.add_subparsers())
... with commands('command1', aliases=['c1'], help='command 1') as p:
...     p.set_defaults(subcommand=print_1)
... with commands('command2', aliases=['c2'], help='command 2') as p:
...     sub1 = NestedSubparser(p.add_subparsers())
...     with sub1('command2_1', help='Command 2, subcommand 1') as p2:
...         p2.set_defaults(subcommand=command2_1)
... args = parser.parse_args()
... args.subcommand()

Copyright (c) 2014-2016 Akce
"""

class NestedSubparser(object):
    """ Argparse add subparser convenience class. Creates contexts for adding subparser options. """
    def __init__(self, subparsers):
        self.subparsers = subparsers

    def __call__(self, *args, **kwargs):
        subparser = self.subparsers.add_parser(*args, **kwargs)
        subparser.set_defaults(errorhelp=subparser.print_usage)
        return _ContextDelegate(subparser)

class _ContextDelegate(object):

    def __init__(self, obj):
        self.__obj = obj

    def __getattr__(self, name):
        return getattr(self.__obj, name)

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_val, tb):
        if ex_type:
            # Exception occured, indicate not handled and pass up.
            ret = False
        else:
            ret = True
        return ret
