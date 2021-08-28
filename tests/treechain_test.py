"""Testing TreeChain."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from emtf_tree import TreeChain


def test_me():
    with pytest.raises(RuntimeError):
        treechain = TreeChain('ntupler/tree', 'ntuple.root')
        assert treechain is not None
