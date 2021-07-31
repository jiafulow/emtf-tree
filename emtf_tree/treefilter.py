# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/tree/filtering.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module defines a framework for filtering Trees."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .defaults import log


class Filter(object):
    """
    The base class from which all filter classes must inherit from.
    The derived class must override the passes method which returns True
    if ths event passes and returns False if not.
    The number of passing and failing events are recorded and may be used
    later to create a cut-flow.
    """
    def __init__(self,
                 hooks=None,
                 passthrough=False):
        self.total = 0
        self.passing = 0
        self.hooks = hooks
        self.passthrough = passthrough
        if self.passthrough:
            log.info(
                "Filter {0} will run in pass-through mode".format(
                    self.__class__.__name__))
        else:
            log.info(
                "Filter {0} is activated".format(
                    self.__class__.__name__))

    def passed(self, event):
        self.total += 1
        self.passing += 1

    def failed(self, event):
        self.total += 1


class FilterHook(object):
    def __init__(self, target, args):
        self.target = target
        self.args = args

    def __call__(self):
        self.target(*self.args)


class EventFilter(Filter):
    def __call__(self, event):
        if self.passthrough:
            if self.hooks:
                for hook in self.hooks:
                    hook()
            self.passed(event)
            return True
        _passes = self.passes(event)
        if _passes is None:
            # event is not counted in total
            log.warning(
                "Filter {0} returned None so event will not "
                "contribute to cut-flow. Use True to accept event, "
                "otherwise False.".format(self.__class__.__name__))
            return False
        elif _passes:
            if self.hooks:
                for hook in self.hooks:
                    hook()
            self.passed(event)
            return True
        self.failed(event)
        return False

    def passes(self, event):
        """
        You should override this method in your derived class
        """
        return True

    def finalize(self):
        """
        You should override this method in your derived class
        """
        pass


class EventFilterList(object):
    def __init__(self, initlist=None):
        self.data = []
        if initlist is not None:
            if isinstance(initlist, list):
                self.data[:] = initlist
            else:
                self.data = list(initlist)

    def __call__(self, event):
        for filt in self.data:
            if not filt(event):
                return False
        return True

    def append(self, filt):
        if not isinstance(filt, EventFilter):
            raise TypeError(
                "EventFilterList can only hold objects "
                "inheriting from EventFilter")
        self.data.append(filt)

    def finalize(self):
        for filt in self.data:
            filt.finalize()
