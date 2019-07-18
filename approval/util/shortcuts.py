# coding: utf-8


def addattr(**kwargs):
    """
    Add attributes to a function.

    Notes:
        Eliminates the need to write things such as
        `func.short_description = "This func does this"`

    """

    def decorator(func):
        for key in kwargs:
            setattr(func, key, kwargs[key])
        return func

    return decorator
