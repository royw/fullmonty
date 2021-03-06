# coding=utf-8

"""
Helper for changing the current directory within a context.

"""

import os

__docformat__ = 'restructuredtext en'
__all__ = ('cd',)


# yes, I know "cd" is a bad class name.  I just like:  "with cd(path):"
# pylint: disable=C0103
# noinspection PyPep8Naming
class cd(object):
    """
    Change directory, execute block, restore directory.

    Usage:

        .. code-block:: python

            with cd(path):
                pass
    """

    def __init__(self, new_path, verbose=False):
        self.new_path = new_path
        self.saved_path = None
        self.verbose = verbose

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)
        if self.verbose:
            print("cd %s" % self.new_path)

    # noinspection PyUnusedLocal
    def __exit__(self, etype, value, traceback):
        # noinspection PyTypeChecker
        os.chdir(self.saved_path)
        if self.verbose:
            print("cd %s" % self.saved_path)
