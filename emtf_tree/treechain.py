# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/tree/chain.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides TreeChain."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import multiprocessing
import multiprocessing.queues
import time

from .defaults import ROOT, log
from .io import root_open, DoesNotExist
from .memory import keepalive
from .tree import Tree
from .treefilter import EventFilterList


class BaseTreeChain(object):
    """
    A base class for TreeChain and TreeQueue.
    """
    def __init__(self, name,
                 treebuffer=None,
                 branches=None,
                 ignore_branches=None,
                 events=-1,
                 onfilechange=None,
                 read_branches_on_demand=False,
                 cache=False,
                 # 30 MB cache by default
                 cache_size=30000000,
                 learn_entries=10,
                 always_read=None,
                 ignore_unsupported=False,
                 filters=None):
        self._name = name
        self._buffer = treebuffer
        self._branches = branches
        self._ignore_branches = ignore_branches
        self._tree = None
        self._file = None
        self._events = events
        self._total_events = 0
        self._ignore_unsupported = ignore_unsupported
        if filters is None:
            self._filters = EventFilterList([])
        else:
            self._filters = filters
        if onfilechange is None:
            onfilechange = []
        self._filechange_hooks = onfilechange

        self._read_branches_on_demand = read_branches_on_demand
        self._use_cache = cache
        self._cache_size = cache_size
        self._learn_entries = learn_entries
        self._always_read = always_read

        if not self._rollover():
            raise RuntimeError("unable to initialize TreeChain")

    def __len__(self):
        """
        Override in subclasses
        """
        return 0

    def __nonzero__(self):
        return len(self) > 0

    __bool__ = __nonzero__

    def _next_file(self):
        """
        Override in subclasses
        """
        return NotImplemented

    def reset(self):
        # Note: self._buffer is not removed
        if self._tree is not None:
            self._tree = None
        if self._file is not None:
            self._file.Close()
            self._file = None

    def __getattr__(self, attr):
        try:
            return getattr(self._tree, attr)
        except AttributeError:
            raise AttributeError("`{0}` instance has no attribute `{1}`".format(
                self.__class__.__name__, attr))

    def __getitem__(self, item):
        return self._tree.__getitem__(item)

    def __contains__(self, branch):
        return self._tree.__contains__(branch)

    def __iter__(self):
        passed_events = 0
        self.reset()
        while self._rollover():
            entries = 0
            total_entries = float(self._tree.GetEntries())
            t1 = time.time()
            t2 = t1
            for entry in self._tree:
                entries += 1
                if self._filters(entry):
                    yield entry
                    passed_events += 1
                    if self._events == passed_events:
                        break
                if time.time() - t2 > 60:
                    entry_rate = int(entries / (time.time() - t1))
                    log.info(
                        "{0:d} entr{1} per second. "
                        "{2:.0f}% done current tree.".format(
                            entry_rate,
                            'ies' if entry_rate != 1 else 'y',
                            100 * entries / total_entries))
                    t2 = time.time()
            if self._events == passed_events:
                break
            log.info("{0:d} entries per second".format(
                int(entries / (time.time() - t1))))
            log.debug("read {0:d} bytes in {1:d} transactions".format(
                self._file.GetBytesRead(),
                self._file.GetReadCalls()))
            self._total_events += entries
        self._filters.finalize()

    def _rollover(self):
        filename = self._next_file()
        if filename is None:
            return False
        log.info("current file: {0}".format(filename))
        try:
            if self._file is not None:
                self._file.Close()
            self._file = root_open(filename)
        except IOError:
            self._file = None
            log.warning("could not open file {0} (skipping)".format(filename))
            return self._rollover()
        try:
            thing = self._file.Get(self._name)
            if not thing:
                raise DoesNotExist
            self._tree = thing
            keepalive(self._tree, self._file)
        except DoesNotExist:
            log.warning("tree {0} does not exist in file {1} (skipping)".format(
                self._name, filename))
            return self._rollover()
        if not isinstance(self._tree, ROOT.TTree):
            log.warning("{0} in file {1} is not a tree (skipping)".format(
                self._name, filename))
            return self._rollover()
        self._tree = Tree(
            self._tree,
            read_branches_on_demand=self._read_branches_on_demand,
            always_read=self._always_read)
        if len(self._tree.GetListOfBranches()) == 0:
            log.warning("tree with no branches in file {0} (skipping)".format(
                filename))
            return self._rollover()
        if self._branches is not None:
            self._tree.activate(self._branches, exclusive=True)
        if self._ignore_branches is not None:
            self._tree.deactivate(self._ignore_branches, exclusive=False)
        if self._buffer is None:
            self._tree.create_buffer(self._ignore_unsupported)
            self._buffer = self._tree._buffer
        else:
            self._tree.update_buffer(self._buffer, transfer_objects=True)
            self._buffer = self._tree._buffer
        if self._use_cache:
            # enable TTreeCache for this tree
            log.info(
                "enabling a {0} TTreeCache for the current tree "
                "({1:d} learning entries)".format(
                    humanize_bytes(self._cache_size),
                    self._learn_entries))
            self._tree.SetCacheSize(self._cache_size)
            self._tree.SetCacheLearnEntries(self._learn_entries)
        for target, args in self._filechange_hooks:
            # run any user-defined functions
            target(*args, name=self._name, file=self._file, tree=self._tree)
        return True


class TreeChain(BaseTreeChain):
    """
    A ROOT.TChain replacement
    """
    def __init__(self, name, files, **kwargs):
        if isinstance(files, tuple):
            files = list(files)
        elif not isinstance(files, list):
            files = [files]
        else:
            files = files[:]
        if not files:
            raise RuntimeError(
                "unable to initialize TreeChain: no files")
        self._files = files
        self._curr_file_idx = 0
        super(TreeChain, self).__init__(name, **kwargs)
        self._tchain = ROOT.TChain(name)
        for filename in self._files:
            self._tchain.Add(filename)

    def GetEntries(self, *args, **kwargs):
        return self._tchain.GetEntries(*args, **kwargs)

    def GetEntriesFast(self, *args, **kwargs):
        return self._tchain.GetEntriesFast(*args, **kwargs)

    def reset(self):
        """
        Reset to the first file
        """
        super(TreeChain, self).reset()
        self._curr_file_idx = 0

    def __len__(self):
        return len(self._files)

    def _next_file(self):
        if self._curr_file_idx >= len(self._files):
            return None
        filename = self._files[self._curr_file_idx]
        nfiles_remaining = len(self._files) - self._curr_file_idx
        log.info("{0:d} file{1} remaining".format(
            nfiles_remaining,
            's' if nfiles_remaining > 1 else ''))
        self._curr_file_idx += 1
        return filename


class TreeQueue(BaseTreeChain):
    """
    A chain of files in a multiprocessing Queue.

    Note that asking for the number of files in the queue with len(treequeue)
    can be unreliable. Also, methods not overridden by TreeQueue will always be
    called on the current tree, so GetEntries will give you the number of
    entries in the current tree.
    """
    SENTINEL = None

    def __init__(self, name, files, **kwargs):
        if not isinstance(files, multiprocessing.queues.Queue):
            raise TypeError("`files` must be an instance of multiprocessing.Queue")
        self._files = files
        self._curr_file_idx = 0
        self._seen_files = []
        super(TreeQueue, self).__init__(name, **kwargs)

    def reset(self):
        """
        Reset to the first file
        """
        super(TreeQueue, self).reset()
        self._curr_file_idx = 0

    def __len__(self):
        # not reliable
        log.warning("len() of `{0}` instance is not reliable".format(
            self.__class__.__name__))
        return self._files.qsize()

    def __nonzero__(self):
        # not reliable
        log.warning("bool() of `{0}` instance is not reliable".format(
            self.__class__.__name__))
        return not self._files.empty()

    __bool__ = __nonzero__

    def _next_file(self):
        if self._curr_file_idx >= len(self._seen_files):
            filename = self._files.get()
            if filename == self.SENTINEL:
                return None
            self._seen_files.append(filename)
        else:
            filename = self._seen_files[self._curr_file_idx]
        self._curr_file_idx += 1
        return filename


def humanize_bytes(value, precision=1):
    abbrevs = (
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'bytes'))
    if value == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if value >= factor:
            return '%.*f %s' % (precision, value / factor, suffix)
