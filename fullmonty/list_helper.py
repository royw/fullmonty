# coding=utf-8
"""
Helpers for list manipulation.  Basically modelled from ruby's Array.compress, Array.uniq

Add the following to your *requirements.txt* file:

* ordereddict; python_version < '3.1'

"""
import collections
import sys

if sys.version_info[0] >= 3:
    # noinspection PyShadowingBuiltins
    unicode = str

__docformat__ = 'restructuredtext en'

try:
    try:
        # noinspection PyUnresolvedReferences
        from ordereddict import OrderedDict
    except ImportError:
        # noinspection PyUnresolvedReferences
        from collections import OrderedDict

    def unique_list(src_list):
        """
        returns a new list without any duplicates

        :param src_list: source list
        :type src_list: list
        :return: unique list
        :rtype: list
        """
        if src_list is None:
            src_list = []
        return list(OrderedDict.fromkeys(src_list).keys())

except ImportError:
    print("ordereddict not installed!")
    exit(1)


def compress_list(src_list):
    """
    Removes None or empty items from the list

    :param src_list: source list
    :type src_list: list
    :return: compressed list
    :rtype: list
    """
    if src_list is None:
        return []
    return [item for item in src_list if item]


def is_sequence(item):
    """
    tests if an item behaves like a list, but is not a string

    :param item: the item to test
    :type item: object
    :return: Asserted if the item behaves like a list but is not a string
    :rtype: bool
    """
    return (not hasattr(item, "strip") and
            (hasattr(item, "__getitem__") or hasattr(item, "__iter__")))


# noinspection PyShadowingBuiltins
def flatten(src_list):
    """
    Flatten a list containing lists.

    Example::

        assert flatten([1, 2, [3, 4, [5]]]) == [1, 2, 3, 4, 5]

    :param src_list: the list that can contain embedded list(s)
    :type src_list: iterable
    :return: flattended list
    :rtype: iterable
    """
    try:
        # noinspection PyUnboundLocalVariable
        basestring = basestring
    except NameError:
        basestring = (str, unicode)

    if src_list is None:
        src_list = []

    for item in src_list:
        if isinstance(item, collections.Iterable) and not isinstance(item, basestring):
            for sub in flatten(item):
                yield sub
        else:
            yield item
