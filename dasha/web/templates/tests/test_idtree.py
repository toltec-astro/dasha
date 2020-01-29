#! /usr/bin/env python

from .. import IdTree


class TestIdTree(object):

    class ClassWithIdTree(IdTree):
        pass

    def setup_class(self):
        self.objs = [self.ClassWithIdTree() for _ in range(2)]

    def test_idt_class_label(self):
        assert self.ClassWithIdTree._idt_class_label == \
                "classwithidtree"

    def test_idt_instance_label(self):
        for i, obj in enumerate(self.objs):
            assert obj._idt_instance_label == i

    def test_idt_instances(self):
        for obj in self.objs:
            assert obj in self.ClassWithIdTree._idt_instances

    def test_label(self):
        assert self.objs[0].label == 'classwithidtree0'
        assert self.objs[1].label == 'classwithidtree1'

    def test_id(self):
        for i in range(2):
            self.objs[i].parent = None
            assert self.objs[i].id == self.objs[i].label == \
                f'classwithidtree{i}'
        self.objs[1].parent = self.objs[0]
        assert self.objs[1].id == 'classwithidtree0-classwithidtree1'
