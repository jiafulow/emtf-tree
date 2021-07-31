# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/tree/treebuffer.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides TreeBuffer."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import six
from collections import OrderedDict

from .defaults import log
from .registry import lookup_by_name, create
from .treetypes import Scalar, Array, Int, BaseCharArray
from .treeobject import TreeCollection, TreeObject


class TreeBuffer(OrderedDict):
    """
    A dictionary mapping branch names to values
    """
    ARRAY_PATTERN = re.compile('^(?P<type>[^\[]+)\[(?P<length>\d+)\]$')  # noqa:W605

    def __init__(self,
                 branches=None,
                 tree=None,
                 ignore_unsupported=False):
        super(TreeBuffer, self).__init__()
        self._fixed_names = {}
        self._branch_cache = {}
        self._branch_cache_event = {}
        self._tree = tree
        self._ignore_unsupported = ignore_unsupported
        self._current_entry = 0
        self._collections = {}
        self._objects = []
        self._entry = Int(0)  # is this actually needed?
        self.__process(branches)
        self._inited = True  # affects __setattr__ and __getattr__ behaviors

    @classmethod
    def __clean(cls, branchname):
        # Replace invalid characters with '_'
        branchname = re.sub('[^0-9a-zA-Z_]', '_', branchname)
        # Remove leading characters until we find a letter or underscore
        return re.sub('^[^a-zA-Z_]+', '', branchname)

    def __process(self, branches):
        if not branches:
            return
        if not isinstance(branches, dict):
            try:
                branches = dict(branches)
            except TypeError:
                raise TypeError(
                    "branches must be a dict or anything "
                    "the dict constructor accepts")
        processed = []
        # ``name`` is the branch name
        # ``vtype`` is the string representation of branch type
        for name, vtype in six.iteritems(branches):
            if name in processed:
                raise ValueError(
                    "duplicate branch name `{0}`".format(name))
            processed.append(name)
            obj = None
            if not isinstance(vtype, str):
                raise TypeError(
                    "unexpected branch type `{0}`".format(vtype))

            array_match = re.match(TreeBuffer.ARRAY_PATTERN, vtype)
            if array_match:
                vtype = array_match.group('type') + '[]'
                length = int(array_match.group('length'))
                # try to lookup type in registry
                cls = lookup_by_name(vtype)
                if cls is not None:
                    # special case for [U]Char and [U]CharArray with
                    # null-termination
                    if issubclass(cls, BaseCharArray):
                        if length == 2:
                            obj = cls.scalar()
                        elif length == 1:
                            raise ValueError(
                                "char branch `{0}` is not "
                                "null-terminated".format(name))
                        else:
                            # leave slot for null-termination
                            obj = cls(length)
                    else:
                        obj = cls(length)
            else:
                # try to lookup type in registry
                cls = lookup_by_name(vtype)
                if cls is not None:
                    obj = cls()
                else:
                    # try to create ROOT.'vtype'
                    obj = create(vtype)

            if obj is not None:
                self[name] = obj  # calls __setitem__
            elif not self._ignore_unsupported:
                raise TypeError(
                    "branch `{0}` has unsupported "
                    "type `{1}`".format(name, vtype))
            else:
                log.warning(
                    "ignoring branch `{0}` with "
                    "unsupported type `{1}`".format(name, vtype))

    def reset(self):
        for value in six.itervalues(self):
            if isinstance(value, (Scalar, Array)):
                value.reset()
            else:
                # there should be no other types of objects in the buffer
                raise TypeError(
                    "cannot reset object of type `{0}`".format(type(value)))

    def update(self, branches=None):
        if isinstance(branches, TreeBuffer):
            self._entry = branches._entry
            for name, value in six.iteritems(branches):
                super(TreeBuffer, self).__setitem__(name, value)
            self._fixed_names.update(branches._fixed_names)
        else:
            raise TypeError(
                "cannot update object of type `{0}`".format(type(branches)))

    def set_tree(self, tree=None):
        self._branch_cache = {}
        self._branch_cache_event = {}
        self._tree = tree
        self._current_entry = 0

    def next_entry(self):
        super(TreeBuffer, self).__setattr__('_branch_cache_event', {})
        self._current_entry += 1

    def get_with_read_if_cached(self, attr):
        if self._tree is not None:
            try:
                branch = self._branch_cache[attr]
            except KeyError:
                # branch is being accessed for the first time
                branch = self._tree.GetBranch(attr)
                if not branch:
                    raise AttributeError(
                        "branch `{0}` does not exist".format(attr))
                self._branch_cache[attr] = branch
                self._tree.AddBranchToCache(branch)
            if branch not in self._branch_cache_event:
                # branch is being accessed for the first time in this entry
                branch.GetEntry(self._current_entry)
                self._branch_cache_event[branch] = None
        try:
            return super(TreeBuffer, self).__getitem__(attr)
        except KeyError:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))

    def __setitem__(self, name, value):
        # for a key to be used as an attr it must be a valid Python identifier
        fixed_name = TreeBuffer.__clean(name)
        if fixed_name in dir(self) or fixed_name.startswith('_'):
            raise ValueError("illegal branch name: `{0}`".format(name))
        if fixed_name != name:
            self._fixed_names[fixed_name] = name
        super(TreeBuffer, self).__setitem__(name, value)

    def __getitem__(self, name):
        return self.get_with_read_if_cached(name)

    def __setattr__(self, attr, value):
        """
        Maps attributes to values.
        Only if we are initialized
        """
        # this test allows attributes to be set in the __init__ method
        # any normal attributes are handled normally
        if '_inited' not in self.__dict__ or attr in self.__dict__:
            super(TreeBuffer, self).__setattr__(attr, value)
            return
        try:
            variable = self.get_with_read_if_cached(attr)
            if isinstance(variable, (Scalar, Array)):
                variable.set(value)
            else:
                raise TypeError(
                    "cannot set attribute `{0}` of `{1}` instance".format(
                        attr, self.__class__.__name__))
        except AttributeError:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))

    def __getattr__(self, attr):
        if '_inited' not in self.__dict__:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))
        if attr in self._fixed_names:
            attr = self._fixed_names[attr]
        try:
            variable = self.get_with_read_if_cached(attr)
            if isinstance(variable, Scalar):
                return variable.value
            return variable
        except AttributeError:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))

    def reset_collections(self):
        for coll in six.iterkeys(self._collections):
            coll.reset()

    def define_collection(self, name, prefix, size, mix=None):
        coll = TreeCollection(self, name, prefix, size, mix=mix)
        object.__setattr__(self, name, coll)
        self._collections[coll] = (name, prefix, size, mix)
        return coll

    def define_object(self, name, prefix):
        obj = TreeObject(self, name, prefix)
        object.__setattr__(self, name, obj)
        self._objects.append((name, prefix))
        return obj

    def set_objects(self, other):
        for args in other._objects:
            self.define_object(*args)
        for args in six.itervalues(other._collections):
            self.define_collection(*args)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = ''
        for name, value in six.iteritems(self):
            rep += '{0} -> {1}\n'.format(name, repr(value))
        return rep
