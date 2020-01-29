#! /usr/bin/env python
import importlib
from abc import abstractmethod
from tollan.utils.registry import Registry
from functools import lru_cache
import inspect

import sys
from anytree import NodeMixin
from abc import ABCMeta
import weakref
from dash.development.base_component import Component as DashComponentBase
from dash.development.base_component import ComponentMeta as DashComponentMeta


class IdTreeMeta(type):

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls._idt_instances = weakref.WeakSet()
        cls._idt_instances_label_iter = cls._get_instance_label_iter()

    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        obj._idt_instance_label = next(cls._idt_instances_label_iter)
        cls._idt_instances.add(obj)
        return obj

    @property
    def _idt_class_label(cls):
        return cls.__name__.lower()

    @staticmethod
    def _get_instance_label_iter():
        h = 0
        while True:
            yield h
            h += 1


class IdTreeABCMeta(IdTreeMeta, ABCMeta):
    pass


class IdTree(NodeMixin, metaclass=IdTreeABCMeta):
    """A mixin class that provides unique ids for class instances.

    A hierarchy of ids are managed in a tree-like data structure,
    enabled by the underlying `NodeMixin` class. The id of each
    tree node is a compositions of the parent's id and the label of
    this node.
    """

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    @property
    def label(self):
        """The base name of the generated id."""
        sep = ''
        return f"{self.__class__._idt_class_label}{sep}" \
               f"{self._idt_instance_label}"

    @property
    def id(self):
        if self.parent is None or self.parent.id is None:
            return self.label
        sep = '-'
        return f"{self.parent.id}{sep}{self.label}"


class Template(IdTree):
    """An abstract class that defines an encapsulated entity
    around a functional group of dash components and the
    callbacks.

    One can do arbitrary nesting of the template through the `make_component`
    factory function, which setup the created instance as the child.

    The template instance serve as a lazy evaluation proxy around the wrapped
    Dash components. Modification to relevant Dash component properties
    are registered as kwargs that will pass to the constructor at evaluation
    time, which is when the `layout` property is queried.
    """

    _template_registry = Registry.create()
    """This keeps a record of loaded subclasses of this class."""

    _skip_template_register = False
    """If set to True, this class is skipped from registering
    to the template registry."""

    def __init_subclass__(cls):
        if not cls._skip_template_register:
            _template_registry_key = cls.__name__.lower()
            print(cls)
            print(cls.__name__)
            print(_template_registry_key)
            cls._template_registry.register(_template_registry_key, cls)

    @property
    @abstractmethod
    def layout(self):
        """Implement this to return a valid Dash layout object."""
        return NotImplemented

    @staticmethod
    def _load_template_cls(spec):
        """Return the template class specified as `spec`.

        The full format of `spec` is `module::label`, where
        ``::label`` can be omitted, in which case the label
        is the last part of mod path, i.e., 'a.b' is the
        same as 'a.b::b'.
        """
        sep = '::'
        if sep not in spec:
            spec = f"{spec}{sep}{spec.rsplit('.', 1)[-1]}"
        mod, label = spec.split(sep)
        # load module, first absolute, then relative to this
        module = None
        for mod_name, package in ((mod, None), (f'.{mod}', __package__)):
            try:
                module = importlib.import_module(mod_name, package=package)
                break
            except ModuleNotFoundError:
                continue
        if module is None:
            raise RuntimeError(
                    f"not able to load template module from spec {spec}")
        # at this point the template class should already be
        # registered
        if label not in Template._template_registry:
            raise RuntimeError(
                    f"not able to find template class from spec {spec}"
                    )
        return Template._template_registry[label]

    @staticmethod
    def from_dict(config, **kwargs):
        template_cls = Template._load_template_cls(config['template'])
        for k, v in config.items():
            kwargs.setdefault(k, v)
        return template_cls(**kwargs)

    def child(self, component, *args, **kwargs):
        """Return a child template object.

        The actual creation of the object is delegated to the appropriate
        subclass based on the component type.
        """

        if isinstance(component, Template):
            if args or kwargs:
                raise ValueError("args and kwargs shall not be specified")
            component.parent = self
            return component

        # dispatch to other subclasses
        module = sys.modules[__name__]

        if isinstance(component, DashComponentMeta):
            # component cls
            template_cls = module.ComponentTemplate.make_template_cls(
                    component)
        elif isinstance(component, DashComponentBase):
            # component instance
            if args or kwargs:
                raise ValueError("args and kwargs shall not be specified")
            args = (component, )
            template_cls = module.ComponentWrapper
        else:
            raise ValueError(
                    f"unable to create component of type {type(component)}")
        return template_cls(*args, **kwargs, parent=self)


class ComponentWrapper(Template):
    """A class that wraps an existing Dash component."""

    def __init__(self, component, parent=None):
        super().__init__(parent=parent)
        self._component = component

    @property
    def label(self):
        self.id

    @property
    def id(self):
        return getattr(self._component, "id", str(self._component))

    @property
    def layout(self):
        return self._component


class ComponentTemplate(Template):
    """A base class that wraps a Dash component type.

    Instances of this class is typically created from calling the
    ``make_component`` class method of the `Template` class, allowing
    one to declare as tree of components with automatic unique ids. The
    actual Dash components are only be created at the moment `layout`
    attribute is accessed. This makes the same template object re-usable
    in multiple parts of a single page application."""

    _component_cls = NotImplemented

    def __init_subclass__(cls):
        super().__init_subclass__()

        def _get_component_prop_names(component_cls):
            if issubclass(component_cls, DashComponentBase):
                return inspect.getfullargspec(component_cls.__init__).args[1:]
            return NotImplemented

        prop_names = _get_component_prop_names(
                cls._component_cls)
        cls._component_prop_names = prop_names

    def __init__(self, *args, **kwargs):
        for i, arg in enumerate(args):
            prop_name = self._component_prop_names[i]
            if prop_name in kwargs:
                raise ValueError(
                    f"duplicated argument {prop_name} in args and kwargs.")
            kwargs[prop_name] = arg
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def _ensure_template(cls, value):
        if isinstance(value, ComponentTemplate):
            return value
        return ComponentWrapper(value)

    @IdTree.parent.setter
    def parent(self, value):
        # we make sure the value set here is wrapped as a template
        IdTree.parent.fset(self, self._ensure_template(value))

    @IdTree.children.setter
    def children(self, children):
        # we make sure the value set here is wrapped as a template
        IdTree.children.fset(self, map(self._ensure_template, children))

    @property
    def layout(self):

        component_kwargs = dict()
        for prop_name in self._component_prop_names:
            if not hasattr(self, prop_name):
                continue
            prop_value = getattr(self, prop_name)
            if prop_name == 'children':
                prop_value = tuple(c.layout for c in prop_value)
            component_kwargs[prop_name] = prop_value

        return self._component_cls(**component_kwargs)

    @classmethod
    @lru_cache(maxsize=None)
    def make_template_cls(cls, component_cls):
        # here we use the lru_cache to make sure the class is created once
        return type(
                f"{component_cls.__name__}",
                (cls, ), dict(
                    _component_cls=component_cls,
                    _skip_template_register=False
                    ))
