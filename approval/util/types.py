# coding: utf-8

from django.db.models.query import QuerySet


def make_iterable(value, output_type=list):
    """
    Return an iterable of provided type, starting from an object or an iterable

    :type value: list|set|tuple|django.db.models.QuerySet
    :param output_type: list|tuple|set or any compatible iterable type

    If value is None, the function returns an empty iterable.
    """
    if type(value) is output_type:
        return value
    if isinstance(value, (list, set, tuple, QuerySet)) and type(value) != output_type:
        return output_type(value)
    return output_type([value]) if value is not None else output_type()
