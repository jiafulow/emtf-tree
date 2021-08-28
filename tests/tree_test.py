"""Testing Tree."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from emtf_tree import Tree


def test_me():
    with pytest.raises(RuntimeError):
        tree = Tree(None)
        assert tree is not None
