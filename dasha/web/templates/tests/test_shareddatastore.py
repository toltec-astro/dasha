#! /usr/bin/env python

from ..slapdash import SharedDataStore


class TestSharedDataStore(object):

    def setup_class(self):
        pass

    def test_make_unique(self):
        ul, idx = SharedDataStore._make_unique([1, 1, 2])
        print(ul, idx)
        assert ul == [1, 2]
        assert idx == [0, 0, 1]
