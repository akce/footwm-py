"""
JSON RPC code/decoder (CODEC).

Copyright (c) 2016 Akce
"""
# Python standard modules.
import functools
import json

from . import log as loghelp

log = loghelp.make(name=__name__)

def encode_command(cmd, *args, **kwargs):
    """ Encode python function call to our JSON RPC format. """
    d = {
            'cmd': cmd,
            'args': args,
            'kwargs': kwargs
        }
    s = json.dumps(d)
    return s

def make_encode_and_post(funcname, postfunc):
    def encode_and_post(self, *args, **kwargs):
        d = encode_command(funcname, *args, **kwargs)
        postfunc(d)
    return encode_and_post

def publicmethodnames(obj):
    """ Return a list of public method names for obj(ect). Public methods are
    those that do NOT start with an underscore '_' character. """
    return [x for x in dir(obj) if x[0] != '_']

class RemoteObject:
    """ Clone a remote object for JSON RPC. Method calls to this object will be
    converted to JSON and posted via the postfunc. """

    def __init__(self, funcnames, postfunc):
        """ Create method call functions from funcnames that call to the post function. """
        for f in funcnames:
            setattr(self, f, functools.partial(make_encode_and_post(f, postfunc), self))

class LocalObject:
    """ Receive JSON RPC method invocations and pass on to obj(ect). """

    def __init__(self, obj):
        self._obj = obj

    def decode_msg_and_call(self, msg):
        """
        Called by the select loop message assembler when we have received a complete message.
        Convert msg from json string to dictionary and then call into self.local.
        """
        ret = True
        try:
            cmddict = json.loads(msg)
        except ValueError as e:
            # Problem converting msg to json struct.
            log.warn('Could not convert from JSON. data="%s"', msg)
        else:
            try:
                cmdname = cmddict['cmd']
                method = getattr(self._obj, cmdname)
            except KeyError:
                # cmd not defined.
                log.warn("'cmd' key not in JSON cmddict %s", str(list(cmddict.keys())))
            except AttributeError:
                log.warn('method %s not found in object', cmdname)
            else:
                # XXX should args default to [] and kwargs default to {}?
                args = cmddict.get('args', None)
                kwargs = cmddict.get('kwargs', None)
                method(*args, **kwargs)
        return ret
