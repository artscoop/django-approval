# coding: utf-8
from typing import Any, Iterable, Type

from django.db.models.query import QuerySet


def make_iterable(
    value: Any[object, Iterable, QuerySet], output_type: Type = list
) -> Iterable:
    """
    Returns an iterable of provided type, starting from an object or an iterable.

    Notes:
        If value is None, the function returns an empty iterable.

    """
    if isinstance(value, output_type):
        return value
    elif isinstance(value, (list, set, tuple, QuerySet)):
        return output_type(value)
    return output_type([value]) if value is not None else output_type()
