#! /usr/bin/env python
import importlib
from abc import abstractmethod
from tollan.utils.registry import Registry
import inspect

import sys
from anytree import NodeMixin
from abc import ABCMeta
from collections.abc import Iterable
import weakref
from dash.development.base_component import Component as DashComponentBase
from dash.development.base_component import ComponentMeta as DashComponentMeta
from dash.dependencies import Input, State, Output


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
    def idbase(self):
        """The base name of the generated id."""
        sep = ''
        return f"{self.__class__._idt_class_label}{sep}" \
               f"{self._idt_instance_label}"

    @property
    def id(self):
        if self.parent is None or self.parent.id is None:
            return self.idbase
        sep = '-'
        return f"{self.parent.id}{sep}{self.idbase}"


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
            # if _template_registry_key not in cls._template_registry:
            cls._template_registry.register(_template_registry_key, cls)

    @property
    @abstractmethod
    def layout(self):
        """Implement this to return a valid Dash layout object."""
        return NotImplemented

    @abstractmethod
    def setup_layout(self, app):
        """Implement this to declare layout components and their callbacks."""
        for child in self.children:
            child.setup_layout(app)

    @staticmethod
    def _load_template_cls(spec):
        """Return the template class specified as `spec`.

        The full format of `spec` is `module::label`, where
        ``::label`` can be omitted, in which case the label
        is the last part of mod path, i.e., 'a.b' is the
        same as 'a.b::b'.
        """
        sep = ':'
        if sep not in spec:
            spec = f"{spec}{sep}{spec.rsplit('.', 1)[-1]}"
        mod, label = spec.split(sep)
        label = label.lower()
        # load module, first absolute, then relative to this
        module = None
        for mod_name, package in ((mod, None), (f'.{mod}', __package__)):
            print(mod, package)
            try:
                module = importlib.import_module(mod_name, package=package)
                break
            except ModuleNotFoundError as e:
                print(e)
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
        self._component = component
        super().__init__(parent=parent)

    @property
    def idbase(self):
        self.id

    @property
    def id(self):
        return self._component.id

    def setup_layout(self, app):
        super().setup_layout(app)

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
        print(f"component template init cls {cls}")
        super().__init_subclass__()

        def _get_component_prop_names(component_cls):
            print(component_cls)
            if issubclass(component_cls, DashComponentBase):
                return inspect.getfullargspec(component_cls.__init__).args[1:]
            return None

        print(cls._component_cls)
        if cls._component_cls is not NotImplemented:
            prop_names = _get_component_prop_names(
                    cls._component_cls)
            cls._component_prop_names = prop_names
            print(f"set component prop_names {cls._component_prop_names}")

    def __init__(self, *args, **kwargs):
        # put args in to kwargs
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
        if value is None:
            return None
        if isinstance(value, ComponentTemplate):
            return value
        return ComponentWrapper(value)

    @IdTree.parent.setter
    def parent(self, value):
        # we make sure the value set here is wrapped as a template
        IdTree.parent.fset(self, self._ensure_template(value))

    @property
    def id(self):
        if hasattr(self, "_static_id"):
            return self._static_id
        return IdTree.id.fget(self)

    @id.setter
    def id(self, value):
        self._static_id = value

    @IdTree.children.setter
    def children(self, children):
        # we make sure the value set here is wrapped as a template
        if not isinstance(children, Iterable) or isinstance(
                children, (str, DashComponentBase)):
            children = [children]
        children = list(map(self._ensure_template, children))
        IdTree.children.fset(self, children)

    def setup_layout(self, app):
        super().setup_layout(app)

    @property
    def layout(self):

        component_kwargs = dict()
        for prop_name in self._component_prop_names:
            if not hasattr(self, prop_name):
                continue
            prop_value = getattr(self, prop_name)
            if prop_name == 'children':
                prop_value = tuple(c.layout for c in prop_value)
                if len(prop_value) == 1:
                    # let dash handle the re-wrapping
                    prop_value = prop_value[0]
            if callable(prop_value):
                prop_value = prop_value()
            component_kwargs[prop_name] = prop_value
        return self._component_cls(**component_kwargs)

    @classmethod
    def make_template_cls(cls, component_cls):
        # here we use the lru_cache to make sure the class is created once
        registry_key = component_cls.__name__.lower()
        if registry_key in cls._template_registry:
            return cls._template_registry[registry_key]
        return type(
                f"{component_cls.__name__}",
                (cls, ), dict(
                    _component_cls=component_cls,
                    _skip_template_register=False
                    ))


class ComponentGroup(ComponentTemplate):
    """This is a base class for managing a set of components as one unit.

    The elements in the group is defined in the `_component_group` class
    attribute. It is a list of dicts which shall contain the follows:

    * key: The unique key of the component.
    * type: The type of the component. Choose from
            "input", "states", "output", "static"
    * prop: The property name to use for Input, Output, or State.

    """

    _component_types = ('output', 'input', 'state', 'static')
    _component_types_pl = ('outputs', 'inputs', 'states', 'statics')
    _compoent_attrs = ('key', 'prop', )
    _compoent_attrs_pl = ('keys', 'props', )

    _component_cls = NotImplemented
    _component_group = NotImplemented
    """This defines the components in this group."""

    def __init_subclass__(cls):
        super().__init_subclass__()
        # we need to check the keys does not conflict with the container cls
        component_keys = tuple(c['key'] for c in cls._component_group)
        conflict = set(component_keys).intersection(
                set(cls._component_prop_names))
        if len(conflict) > 0:
            raise ValueError(
                    f"conflicting component key in group: {conflict}.")
        cls._component_keys = component_keys

        dispatch_deps = {
                'output': Output,
                'input': Input,
                'state': State,
                }
        # generate key props
        for type_, type_pl in zip(
                cls._component_types, cls._component_types_pl):
            for attr, attr_pl, value in zip(
                    cls._compoent_attrs,
                    cls._compoent_attrs_pl,
                    zip(*(
                        tuple(c[a] for a in cls._compoent_attrs)
                        for i, c in enumerate(cls._component_group)
                        if c['type'] == type_
                        ))
                    ):
                if type_ == 'static' and attr_pl == 'props':
                    # static does not have props
                    continue
                setattr(cls, f"_{type_}_{attr_pl}", tuple(value))
            # component objects
            setattr(cls, f"{type_}_components", property(
                lambda self, type_=type_: (
                    getattr(
                        self,
                        cls._make_component_obj_attr(k)
                        )
                    for k in getattr(cls, f'_{type_}_keys')
                    )))
            if type_ != 'static':
                # dependencies object
                setattr(cls, type_pl, property(
                    lambda self, type_=type_: (
                        dispatch_deps[type_](
                            getattr(
                                self,
                                cls._make_component_obj_attr(k)).id,
                            p)
                        for k, p in zip(
                            getattr(cls, f'_{type_}_keys'),
                            getattr(cls, f'_{type_}_props')
                            )
                        )
                    ))

    def __init__(self, **kwargs):
        for g in self._component_group:
            key = g['key']
            default = dict() if g.get('required', False) else None
            setattr(
                    self,
                    self._make_component_args_attr(key),
                    kwargs.pop(key, default))
        super().__init__(**kwargs)

    @staticmethod
    def _make_component_args_attr(key):
        return f'_{key}_args'

    @staticmethod
    def _make_component_obj_attr(key):
        return f'{key}'

    def _make_component_obj(self, key):

        def decorator(func):
            # A None existing arg means this component won't be created
            args = getattr(self, self._make_component_args_attr(key))
            component_attr = self._make_component_obj_attr(key)
            if args is None:
                return None
            if isinstance(args, tuple):
                kwargs = dict()
            elif isinstance(args, dict):
                args, kwargs = tuple(), args
            else:
                args, kwargs = tuple([args]), dict()
            setattr(self, component_attr, func(self, *args, **kwargs))
        return decorator

    def setup_layout(self, app):
        super().setup_layout(app)

    @property
    def layout(self):
        return super().layout
