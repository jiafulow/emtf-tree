# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/tree/tree.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides Tree."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import fnmatch
from six.moves import range
from collections import OrderedDict

from .defaults import log
from .treebuffer import TreeBuffer


class BaseTree(object):
    """
    A base class for Tree.
    """
    def __init__(self, tree,
                 read_branches_on_demand=False,
                 always_read=None):
        self._tree = tree
        # only set _buffer if it does not exist
        if not hasattr(self, '_buffer'):
            self._buffer = TreeBuffer()
        self._read_branches_on_demand = read_branches_on_demand
        if always_read is None:
            self._always_read = []
        else:
            self._always_read = always_read
        #self._branch_cache = {}
        #self._current_entry = 0
        self.__extra_init()
        self._inited = True  # affects __setattr__ and __getattr__ behaviors

    def __extra_init(self):
        # Borrow certain functions from TTree
        self.GetBranch = self._tree.GetBranch
        self.GetBranchStatus = self._tree.GetBranchStatus
        self.GetListOfBranches = self._tree.GetListOfBranches
        self.GetEntry = self._tree.GetEntry
        self.GetEntries = self._tree.GetEntries
        self.GetEntriesFast = self._tree.GetEntriesFast
        self.GetWeight = self._tree.GetWeight
        self.SetBranchAddress = self._tree.SetBranchAddress
        self.SetBranchStatus = self._tree.SetBranchStatus
        self.SetCacheSize = self._tree.SetCacheSize
        self.SetCacheLearnEntries = self._tree.SetCacheLearnEntries
        self.AddBranchToCache = self._tree.AddBranchToCache
        self.DropBranchFromCache = self._tree.DropBranchFromCache
        self.PrintCacheStats = self._tree.PrintCacheStats

    @classmethod
    def branch_type(cls, branch):
        """
        Return the string representation for the type of a branch
        """
        typename = branch.GetClassName()
        if not typename:
            leaf = branch.GetListOfLeaves()[0]
            typename = leaf.GetTypeName()
            # check if leaf has multiple elements
            leaf_count = leaf.GetLeafCount()
            if leaf_count:
                length = leaf_count.GetMaximum()
            else:
                length = leaf.GetLen()
            if length > 1:
                typename = '{0}[{1:d}]'.format(typename, length)
        return typename

    @classmethod
    def branch_is_supported(cls, branch):
        """
        Currently the branch must only have one leaf but the leaf may have one
        or multiple elements
        """
        return branch.GetNleaves() == 1

    def create_buffer(self, ignore_unsupported=False):
        """
        Create this tree's TreeBuffer
        """
        bufferdict = OrderedDict()
        for branch in self.iterbranches():
            # only include activated branches
            if not self.GetBranchStatus(branch.GetName()):
                continue
            if BaseTree.branch_is_supported(branch):
                bufferdict[branch.GetName()] = BaseTree.branch_type(branch)
            elif not ignore_unsupported:
                raise TypeError(
                    "branch `{0}` is unsupported".format(branch.GetName()))
            else:
                log.warning(
                    "ignore unsupported branch `{0}`".format(branch.GetName()))
        self.set_buffer(TreeBuffer(
            bufferdict,
            ignore_unsupported=ignore_unsupported))

    def update_buffer(self, treebuffer, transfer_objects=False):
        """
        Merge items from a TreeBuffer into this Tree's TreeBuffer

        Parameters
        ----------
        buffer : rootpy.tree.buffer.TreeBuffer
            The TreeBuffer to merge into this Tree's buffer

        transfer_objects : bool, optional (default=False)
            If True then all objects and collections on the input buffer will
            be transferred to this Tree's buffer.
        """
        self.set_buffer(treebuffer, transfer_objects=transfer_objects)

    def set_buffer(self, treebuffer,
                   branches=None,
                   ignore_branches=None,
                   create_branches=False,
                   visible=True,
                   ignore_missing=False,
                   ignore_duplicates=False,
                   transfer_objects=False):
        """
        Set the Tree buffer

        Parameters
        ----------
        treebuffer : rootpy.tree.buffer.TreeBuffer
            a TreeBuffer

        branches : list, optional (default=None)
            only include these branches from the TreeBuffer

        ignore_branches : list, optional (default=None)
            ignore these branches from the TreeBuffer

        create_branches : bool, optional (default=False)
            If True then the branches in the TreeBuffer should be created.
            Use this option if initializing the Tree. A ValueError is raised
            if an attempt is made to create a branch with the same name as one
            that already exists in the Tree. If False the addresses of existing
            branches will be set to point at the addresses in this buffer.

        visible : bool, optional (default=True)
            If True then the branches will be added to the buffer and will be
            accessible as attributes of the Tree.

        ignore_missing : bool, optional (default=False)
            If True then any branches in this buffer that do not exist in the
            Tree will be ignored, otherwise a ValueError will be raised. This
            option is only valid when ``create_branches`` is False.

        ignore_duplicates : bool, optional (default=False)
            If False then raise a ValueError if the tree already has a branch
            with the same name as an entry in the buffer. If True then skip
            branches that already exist. This option is only valid when
            ``create_branches`` is True.

        transfer_objects : bool, optional (default=False)
            If True, all tree objects and collections will be transferred from
            the buffer into this Tree's buffer.
        """
        # determine branches to keep while preserving branch order
        if branches is None:
            branches = treebuffer.keys()
        if ignore_branches is not None:
            branches = [b for b in branches if b not in ignore_branches]

        for name in branches:
            value = treebuffer[name]
            if self.has_branch(name):
                self.SetBranchAddress(name, value)
            elif not ignore_missing:
                raise ValueError(
                    "Attempting to set address for "
                    "branch `{0}` which does not exist".format(name))
            else:
                log.warning(
                    "Skipping entry in buffer for which no "
                    "corresponding branch in the "
                    "tree exists: `{0}`".format(name))
        self._buffer.update(treebuffer)
        if transfer_objects:
            self._buffer.set_objects(treebuffer)

    def activate(self, branches, exclusive=False):
        """
        Activate branches

        Parameters
        ----------
        branches : str or list
            branch or list of branches to activate

        exclusive : bool, optional (default=False)
            if True deactivate the remaining branches
        """
        if exclusive:
            self.SetBranchStatus('*', 0)
        if isinstance(branches, str):
            branches = [branches]
        for branch in branches:
            if '*' in branch:
                matched_branches = self.glob(branch)
                for b in matched_branches:
                    self.SetBranchStatus(b, 1)
            elif self.has_branch(branch):
                self.SetBranchStatus(branch, 1)

    def deactivate(self, branches, exclusive=False):
        """
        Deactivate branches

        Parameters
        ----------
        branches : str or list
            branch or list of branches to deactivate

        exclusive : bool, optional (default=False)
            if True activate the remaining branches
        """
        if exclusive:
            self.SetBranchStatus('*', 1)
        if isinstance(branches, str):
            branches = [branches]
        for branch in branches:
            if '*' in branch:
                matched_branches = self.glob(branch)
                for b in matched_branches:
                    self.SetBranchStatus(b, 0)
            elif self.has_branch(branch):
                self.SetBranchStatus(branch, 0)

    @property
    def branches(self):
        """
        List of the branches
        """
        return [branch for branch in self.GetListOfBranches()]

    def iterbranches(self):
        """
        Iterator over the branches
        """
        for branch in self.GetListOfBranches():
            yield branch

    @property
    def branchnames(self):
        """
        List of branch names
        """
        return [branch.GetName() for branch in self.GetListOfBranches()]

    def iterbranchnames(self):
        """
        Iterator over the branch names
        """
        for branch in self.iterbranches():
            yield branch.GetName()

    def glob(self, patterns, exclude=None):
        """
        Return a list of branch names that match ``pattern``.
        Exclude all matched branch names which also match a pattern in
        ``exclude``. ``exclude`` may be a string or list of strings.

        Parameters
        ----------
        patterns: str or list
            branches are matched against this pattern or list of patterns where
            globbing is performed with '*'.

        exclude : str or list, optional (default=None)
            branches matching this pattern or list of patterns are excluded
            even if they match a pattern in ``patterns``.

        Returns
        -------
        matches : list
            List of matching branch names
        """
        if isinstance(patterns, str):
            patterns = [patterns]
        if isinstance(exclude, str):
            exclude = [exclude]
        matches = []
        for pattern in patterns:
            matches += fnmatch.filter(self.iterbranchnames(), pattern)
            if exclude is not None:
                for exclude_pattern in exclude:
                    matches = [match for match in matches
                               if not fnmatch.fnmatch(match, exclude_pattern)]
        return matches

    def __iter__(self):
        """
        Iterator over the entries in the Tree.
        """
        if not self._buffer:
            log.warning("buffer does not exist or is empty")
            self.create_buffer()
        if self._read_branches_on_demand:
            self._buffer.set_tree(self)
            # drop all branches from the cache
            self.DropBranchFromCache('*')
            for attr in self._always_read:
                try:
                    branch = self._branch_cache[attr]
                except KeyError:  # one-time hit
                    branch = self.GetBranch(attr)
                    if not branch:
                        raise AttributeError(
                            "branch `{0}` specified in "
                            "`always_read` does not exist".format(attr))
                    self._branch_cache[attr] = branch
                # add branches that we should always read to cache
                self.AddBranchToCache(branch)

            for i in range(self.GetEntries()):
                # Only increment current entry.
                # getattr on a branch will then GetEntry on only that branch
                # see ``TreeBuffer.get_with_read_if_cached``.
                self._current_entry = i
                self.LoadTree(i)
                for attr in self._always_read:
                    # Always read branched in ``self._always_read`` since
                    # these branches may never be getattr'd but the TreeBuffer
                    # should always be updated to reflect their current values.
                    # This is useful if you are iterating over an input tree
                    # and writing to an output tree that shares the same
                    # TreeBuffer but you don't getattr on all branches of the
                    # input tree in the logic that determines which entries
                    # to keep.
                    self._branch_cache[attr].GetEntry(i)
                self._buffer._entry.set(i)
                yield self._buffer
                self._buffer.next_entry()
                self._buffer.reset_collections()
        else:
            for i in range(self.GetEntries()):
                # Read all activated branches (can be slow!).
                self.GetEntry(i)
                self._buffer._entry.set(i)
                yield self._buffer
                self._buffer.reset_collections()

    def __setattr__(self, attr, value):
        # this test allows attributes to be set in the __init__ method
        # any normal attributes are handled normally
        if '_inited' not in self.__dict__ or attr in self.__dict__:
            super(BaseTree, self).__setattr__(attr, value)
            return
        try:
            setattr(self._buffer, attr, value)
        except AttributeError:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))

    def __getattr__(self, attr):
        if '_inited' not in self.__dict__:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))
        try:
            return getattr(self._buffer, attr)
        except AttributeError:
            raise AttributeError(
                "`{0}` instance has no attribute `{1}`".format(
                    self.__class__.__name__, attr))

    def __len__(self):
        """
        Same as GetEntries
        """
        return self.GetEntries()

    def __contains__(self, branch):
        """
        Same as has_branch
        """
        return self.has_branch(branch)

    def has_branch(self, branch):
        """
        Determine if this Tree contains a branch with the name ``branch``

        Parameters
        ----------
        branch : str
            branch name

        Returns
        -------
        has_branch : bool
            True if this Tree contains a branch with the name ``branch`` or
            False otherwise.
        """
        return not not self.GetBranch(branch)


class Tree(BaseTree):
    pass
