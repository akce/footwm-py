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
            result = func(*args, **kwargs)
            # Only store non None results. Having a problem where
            # we're memoising a bit too early still so make sure we
            # only store worthwhile values.
            if result is not None:
                results[key] = result
            #print('memoise: added result {} for key {}'.format(result, key))
        return results.get(key, None)
    return memoiser
