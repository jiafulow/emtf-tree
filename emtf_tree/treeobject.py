# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/tree/treeobject.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides TreeObject and TreeCollection."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from six.moves import range, zip


class TreeObject(object):

    def __init__(self, tree, name, prefix):
        self.tree = tree
        self.name = name
        self.prefix = prefix
        self._inited = True  # affects __setattr__ behaviors

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.name == other.name and
                self.prefix == other.prefix)

    def __hash__(self):
        return hash((
            self.__class__.__name__,
            self.name,
            self.prefix))

    def __getitem__(self, attr):
        return getattr(self, attr)

    def __setitem__(self, attr, value):
        setattr(self.tree, self.prefix + attr, value)

    def __getattr__(self, attr):
        return getattr(self.tree, self.prefix + attr)

    def __setattr__(self, attr, value):
        if '_inited' not in self.__dict__:
            object.__setattr__(self, attr, value)
            return
        try:
            setattr(self.tree, self.prefix + attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)


class TreeCollectionObject(TreeObject):

    def __init__(self, tree, name, prefix, index):
        self.index = index
        super(TreeCollectionObject, self).__init__(tree, name, prefix)

    def __eq__(self, other):
        return TreeObject.__eq__(self, other) and self.index == other.index

    def __hash__(self):
        return hash((
            self.__class__.__name__,
            self.name,
            self.prefix,
            self.index))

    def __getattr__(self, attr):
        try:
            return getattr(self.tree, self.prefix + attr)[self.index]
        except IndexError:
            raise IndexError(
                "index {0:d} out of range for "
                "attribute `{1}` of collection `{2}` of size {3:d}".format(
                    self.index, attr, self.prefix,
                    len(getattr(self.tree, self.prefix + attr))))

    def __setattr__(self, attr, value):
        if '_inited' not in self.__dict__:
            object.__setattr__(self, attr, value)
            return
        try:
            getattr(self.tree, self.prefix + attr)[self.index] = value
        except IndexError:
            raise IndexError(
                "index {0:d} out of range for "
                "attribute `{1}` of collection `{2}` of size {3:d}".format(
                    self.index, attr, self.prefix,
                    len(getattr(self.tree, self.prefix + attr))))
        except AttributeError:
            object.__setattr__(self, attr, value)


class TreeCollection(object):

    def __init__(self, tree, name, prefix, size, mix=None, cache=True):
        self.tree = tree
        self.name = name
        self.prefix = prefix
        self.size = size
        self.selection = None

        self._use_cache = cache
        self._cache = {}
        # A TreeCollectionObject is constructed on-the-fly and cached for reuse
        self.tree_object_cls = TreeCollectionObject

    def __nonzero__(self):
        return len(self) > 0

    __bool__ = __nonzero__

    def reset(self):
        self.reset_selection()
        self.reset_cache()

    def reset_selection(self):
        self.selection = None

    def reset_cache(self):
        self._cache = {}

    def remove(self, thing):
        if self.selection is None:
            self.selection = range(len(self))
        for i, other in enumerate(self):
            if thing == other:
                self.selection.pop(i)
                break

    def pop(self, index):
        if self.selection is None:
            self.selection = range(len(self))
        thing = self[index]
        self.selection.pop(index)
        return thing

    def select(self, func):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection = [
            i for i, thing in zip(self.selection, self)
            if func(thing)]

    def select_indices(self, indices):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection = [self.selection[i] for i in indices]

    def mask(self, func):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection = [
            i for i, thing in zip(self.selection, self)
            if not func(thing)]

    def mask_indices(self, indices):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection = [
            j for i, j in enumerate(self.selection)
            if i not in indices]

    def _wrap_sort_key(self, key):
        def wrapped_key(index):
            return key(self.getitem(index))
        return wrapped_key

    def sort(self, key, **kwargs):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection.sort(key=self._wrap_sort_key(key), **kwargs)

    def slice(self, start=0, stop=None, step=1):
        if self.selection is None:
            self.selection = range(len(self))
        self.selection = self.selection[slice(start, stop, step)]

    def make_persistent(self):
        """
        Perform actual selection and sorting on underlying
        attribute vectors
        """
        pass

    def getitem(self, index):
        """
        direct access without going through self.selection
        """
        if index >= len(self):
            raise IndexError(
                "index {0:d} out of range for "
                "collection `{1}` of size {2:d}".format(
                    self.index, self.name, len(self)))
        if self._use_cache and index in self._cache:
            return self._cache[index]
        obj = self.tree_object_cls(self.tree, self.name, self.prefix, index)
        if self._use_cache:
            self._cache[index] = obj
        return obj

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if index >= len(self):
            raise IndexError(
                "index {0:d} out of range for "
                "collection `{1}` of size {2:d}".format(
                    self.index, self.name, len(self)))
        if self.selection is not None:
            index = self.selection[index]
        if self._use_cache and index in self._cache:
            return self._cache[index]
        obj = self.tree_object_cls(self.tree, self.name, self.prefix, index)
        if self._use_cache:
            self._cache[index] = obj
        return obj

    def __len__(self):
        if self.selection is not None:
            return len(self.selection)
        return getattr(self.tree, self.size)

    def __iter__(self):
        for index in range(len(self)):
            yield self.__getitem__(index)
