# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/__init__.py
# https://github.com/rootpy/rootpy/blob/master/rootpy/defaults.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides the default configurations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
from collections import namedtuple

from .logger import log

try:
    import ROOT
except ImportError:
    raise ImportError('Could not import ROOT')


def configure_defaults():
    """
    This function is executed immediately after ROOT's finalSetup
    """
    if not os.environ.get('NO_ROOTPY_BATCH', False):
        ROOT.gROOT.SetBatch(True)
        log.debug("ROOT is running in batch mode")

    #ROOT.gErrorAbortLevel = ROOT.kError
    ROOT.gErrorIgnoreLevel = 0


configure_defaults()


class ROOTVersion(namedtuple('_ROOTVersionBase',
                             ['major', 'minor', 'micro'])):

    def __new__(cls, version):
        if version < 1E4:
            raise ValueError(
                "{0:d} is not a valid ROOT version integer".format(version))
        return super(ROOTVersion, cls).__new__(
            cls,
            int(version / 1E4), int((version / 1E2) % 100), int(version % 100))

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '{0:d}.{1:02d}/{2:02d}'.format(*self)


ROOT_VERSION = ROOTVersion(ROOT.gROOT.GetVersionInt())


class ROOTError(RuntimeError):
    """
    Exception class representing a ROOT error/warning message.
    """
    pass
