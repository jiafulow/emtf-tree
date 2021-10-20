# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/io/file.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module enhances IO-related ROOT functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from .defaults import ROOT, log


def _expand_path(s):
    return os.path.expanduser(os.path.expandvars(s))


def root_open(filename, mode=''):
    """
    Open a ROOT file via ROOT's static ROOT.TFile.Open [1] function and return
    an asrootpy'd File.

    Parameters
    ----------

    filename : string
        The absolute or relative path to the ROOT file.

    mode : string, optional (default='')
        Mode indicating how the file is to be opened.  This can be either one
        of the options supported by ROOT.TFile.Open [2], or one of `a`, `a+`,
        `r`, `r+`, `w` or `w+`, with meanings as for the built-in `open()`
        function [3].

    Returns
    -------

    root_file : File
        an instance of rootpy's File subclass of ROOT's TFile.

    References
    ----------

    .. [1] http://root.cern.ch/root/html/TFile.html#TFile:Open
    .. [2] http://root.cern.ch/root/html/TFile.html#TFile:TFile@2
    .. [3] https://docs.python.org/2/library/functions.html#open

    """
    mode_map = {'a': 'UPDATE',
                'a+': 'UPDATE',
                'r': 'READ',
                'r+': 'UPDATE',
                'w': 'RECREATE',
                'w+': 'RECREATE'}

    if mode in mode_map:
        mode = mode_map[mode]

    filename = _expand_path(filename)
    log.debug("Opening file '{0}'".format(filename))
    root_file = ROOT.TFile.Open(filename, mode)
    if not root_file:
        raise IOError("could not open file: '{0}'".format(filename))
    # give Python ownership of the TFile so we can delete it
    ROOT.SetOwnership(root_file, True)
    return root_file


class DoesNotExist(Exception):
    """
    This exception is raised if an attempt is made to access an object
    that does not exist in a directory.
    """
    pass
