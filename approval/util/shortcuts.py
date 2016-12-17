# coding: utf-8


def addattr(**kwargs):
    """ Définir des attributs à une méthode ou fonction """

    def decorator(func):
        for key in kwargs:
            setattr(func, key, kwargs[key])
        return func

    return decorator
