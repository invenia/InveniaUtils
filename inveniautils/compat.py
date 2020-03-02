def cmp(a, b):
    """Mimics PY2 cmp.

    See https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
    """
    if hasattr(a, "__cmp__") and type(a) == type(b):
        return a.__cmp__(b)
    else:
        if a is None and b is None:
            return 0
        elif a is None:
            return -1
        elif b is None:
            return 1

        return (a > b) - (a < b)
