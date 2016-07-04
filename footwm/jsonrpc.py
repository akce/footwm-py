"""
JSON RPC code/decoder (CODEC).

Copyright (c) 2016 Akce
"""
# Python standard modules.
import functools
import json

def encode_command(cmd, *args, **kwargs):
    """ Encode python function call to our JSON RPC format. """
    d = {
            'cmd': cmd,
            'args': args,
            'kwargs': kwargs
        }
    s = json.dumps(d)
    return s

def make_encode_and_post(funcname):
    def encode_and_post(self, *args, **kwargs):
        d = encode_command(funcname, *args, **kwargs)
        self.post(d)
    return encode_and_post

class JsonClient(object):
    """
    Client interface that encodes/decodes over a socket using JSON.
    Decode JSON messages from the remote object for self.local object.
    Encode commands for public methods of self.remote in JSON and send.
    """
    def __init__(self, cloneclass):
        # Clone the public interface of cloneclass.
        public = [x for x in dir(cloneclass) if x[0] != '_']
        for f in public:
            eap = make_encode_and_post(f)
            setattr(self, f, functools.partial(eap, self))

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
            # XXX log this.
            pass
        else:
            try:
                cmdname = cmddict['cmd']
                method = getattr(self.local, cmdname)
            except KeyError:
                # XXX cmd not defined.
                # XXX log something here...
                pass
            except AttributeError:
                # XXX log something here...
                pass
            else:
                # XXX should args default to [] and kwargs default to {}?
                args = cmddict.get('args', None)
                kwargs = cmddict.get('kwargs', None)
                method(*args, **kwargs)
        return ret
