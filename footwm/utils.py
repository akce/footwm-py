"""
Decorator utilities.

"""

import functools

def memoise(func):
    results = {}
    @functools.wraps(func)
    def memoiser(*args, **kwargs):
        nonlocal results
        # kwargs is a dict and can't be hashed. Trialling id as a workaround.
        key = (args, id(kwargs))
        if key not in results:
            results[key] = func(*args, **kwargs)
            #print('memoise: added result {} for key {}'.format(results[key], key))
        return results[key]
    return memoiser
