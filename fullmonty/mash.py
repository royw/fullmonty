# coding=utf-8

"""
A Mash behaves like both a dictionary and a NameSpace.  This is a very simple implementation,
attribute accessors are just added onto a dictionary.  So a['foo'] == a.foo

Keys must be hashable.  If a key is not a valid attribute name, then it can only be accessed
using dict accessors.


For example:

..code-block:: python

    a = Mash()
    a['foo'] = 'bar'
    assert a['foo'] == 'bar'
    assert a.foo == 'bar'
    a.foo = 'fig'
    assert a['foo'] == 'fig'
    assert a.foo == 'fig'

"""
import collections

__docformat__ = 'restructuredtext en'


class Mash(dict):
    """
    dictionary keys must be hashable.

    Inherits dict behavior so we just extend by adding attribute accessing.
    """
    def __getattr__(self, key):
        """
        Support self.key read access

        :param key: the mash dictionary key
        :type key: collections.Hashable
        :return: the value or None
        :rtype: object|None
        :raises: TypeError
        """
        if not isinstance(key, collections.Hashable):
            raise TypeError("The key ({key}) is not hashable".format(key=str(key)))
        if key not in self:
            self[key] = None
        # noinspection PyTypeChecker
        return self[key]

    def __setattr__(self, key, value):
        """
        Support self.key write access

        :param key: the mash dictionary key
        :type key: collections.Hashable
        :param value: the value to associate with the key
        :type value: object
        :return: this instance
        :rtype: Mash
        :raises: TypeError
        """
        if not isinstance(key, collections.Hashable):
            raise TypeError("The key ({key}) is not hashable".format(key=str(key)))
        self[key] = value
        return self

    def __delattr__(self, key):
        """
        Support deleting: del self.key

        :param key: the mash dictionary key
        :type key: collections.Hashable
        :return: this instance
        :rtype: Mash
        :raises: TypeError
        """
        if not isinstance(key, collections.Hashable):
            raise TypeError("The key ({key}) is not hashable".format(key=str(key)))
        # noinspection PyTypeChecker
        del self[key]
        return self
