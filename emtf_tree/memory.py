# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/memory/keepalive.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import weakref

from .defaults import log

KEEPALIVE = weakref.WeakKeyDictionary()
DISABLED = 'NO_ROOTPY_KEEPALIVE' in os.environ


def hashable(v):
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


def keepalive(nurse, *patients):
    """
    Keep ``patients`` alive at least as long as ``nurse`` is around using a
    ``WeakKeyDictionary``.
    """
    if DISABLED:
        return
    if hashable(nurse):
        hashable_patients = []
        for p in patients:
            if hashable(p):
                log.debug("Keeping {0} alive for lifetime of {1}".format(p, nurse))
                hashable_patients.append(p)
            else:
                log.warning("Unable to keep unhashable object {0} "
                            "alive for lifetime of {1}".format(p, nurse))
        KEEPALIVE.setdefault(nurse, set()).update(hashable_patients)
    else:
        log.warning("Unable to keep objects alive for lifetime of "
                    "unhashable object {0}".format(nurse))
