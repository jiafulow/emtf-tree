# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/__init__.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""Registry for classes that are registered at runtime."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .defaults import ROOT, log

REGISTRY = {}


class register(object):
    def __init__(self, names=None, builtin=False):
        if names is not None:
            if not isinstance(names, (list, tuple)):
                names = [names]
        self.names = names
        self.builtin = builtin

    def __call__(self, cls):
        cls_names = [cls.__name__]
        if self.names is not None:
            cls_names += self.names

        for name in cls_names:
            if name in REGISTRY:
                log.debug("duplicate registration of "
                          "class `{0}`".format(name))
            REGISTRY[name] = cls
        return cls


def lookup_by_name(cls_name):
    if cls_name in REGISTRY:
        return REGISTRY[cls_name]
    return None


def create(cls_name, *args, **kwargs):
    cls = getattr(ROOT, cls_name, None)
    if cls is None:
        return None
    try:
        obj = cls(*args, **kwargs)
        return obj
    except TypeError:
        return None
