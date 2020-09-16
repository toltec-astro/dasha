#! /usr/bin/env python
from abc import abstractmethod
from tollan.utils.registry import Registry
from tollan.utils.log import get_logger
from tollan.utils import getobj, rupdate
import inspect

from anytree import NodeMixin
from abc import ABCMeta
from collections.abc import Iterable
import weakref
from dash.development.base_component import Component as DashComponentBase
from dash.development.base_component import ComponentMeta as DashComponentMeta
from dash.dependencies import Input, State, Output
import dash_bootstrap_components as dbc
import numpy as np
from tollan.utils.namespace import NamespaceMixin
from schema import Schema, Optional, And
from cached_property import cached_property


__all__ = [
        'IdTreeMeta', 'IdTree', 'Template',
        'ComponentWrapper', 'ComponentRoot', 'ComponentTemplate',
        'ComponentGroup', ]


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


class _IdTreeABCMeta(IdTreeMeta, ABCMeta):
    pass


class IdTree(NodeMixin, metaclass=_IdTreeABCMeta):
    """A mixin class that provides unique ids for class instances.

    A hierarchy of ids are managed in a tree-like data structure,
    enabled by the underlying `~anytree.node.nodemixin.NodeMixin` class.
    The id of each tree node is a compositions of the parent's id and
    the label of this node.

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

    @cached_property
    def _id_cached(self):
        """The unique id, cached to avoid repeated computation."""
        if self.parent is None or self.parent.id is None:
            return self.idbase
        sep = '-'
        return f"{self.parent.id}{sep}{self.idbase}"

    # these hooks is need to allow one invalidate the id
    def _pre_detach(self, parent):
        self.__dict__.pop('_id_cached', None)

    def _post_detach(self, parent):
        self.__dict__.pop('_id_cached', None)

    def _pre_attach(self, parent):
        self.__dict__.pop('_id_cached', None)

    def _post_attach(self, parent):
        self.__dict__.pop('_id_cached', None)

    @property
    def id(self):
        """The unique id."""
        return self._id_cached


class Template(IdTree, NamespaceMixin):
    """An abstract class that defines an encapsulated entity
    around a functional group of dash components and the
    callbacks.

    One can do arbitrary nesting of templates through the `child`
    factory function, which returns a child template instance.
    """

    _template_registry = Registry.create()
    """This keeps a record of imported subclasses of this class."""

    _template_is_final = NotImplemented
    """If set to True, this class is considered "concrete" and is
    registered in the `_template_registry`.
    """

    _namespace_type_key = 'template'

    @classmethod
    def _namespace_from_dict_op(cls, d):
        # we resolve the namespace template here so that we can allow
        # one use only the module path to specify a template class.
        if cls._namespace_type_key not in d:
            raise ValueError(
                    f'unable to load template: '
                    f'missing required key "{cls._namespace_type_key}"')
        template_cls = cls._resolve_template_cls(d[cls._namespace_type_key])
        return dict(d, **{cls._namespace_type_key: template_cls})

    @classmethod
    def _namespace_check_type(cls, ns_type):
        # this allows from_dict return subclass instances.
        return issubclass(ns_type, cls)

    def __init_subclass__(cls):
        # register if cls is marked as final
        if cls._template_is_final:
            cls._template_registry.register(
                    cls._make_registry_key(cls), cls)

    @staticmethod
    def _make_registry_key(template_cls):
        if hasattr(template_cls, '_template_registry_key'):
            return template_cls._template_registry_key
        return f"{template_cls.__module__}.{template_cls.__qualname__}"

    @classmethod
    def clear_registry(cls):
        """Reset the template subclass registry.

        This is useful to make fresh reload of the flask instance.
        """
        cls._template_registry.clear()

    @property
    @abstractmethod
    def layout(self):
        """Implement this to return a valid Dash layout object."""
        return NotImplemented

    def before_setup_layout(self, app):
        """Hook that run before the `setup_layout` function call."""
        pass

    def after_setup_layout(self, app):
        """Hook that run after the `setup_layout` function call."""
        pass

    @abstractmethod
    def setup_layout(self, app):
        """Implement this to declare layout components and their callbacks."""
        self.before_setup_layout(app)
        for child in self.children:
            child.setup_layout(app)
        self.after_setup_layout(app)

    @classmethod
    def from_dict(cls, d, **kwargs):
        """Return a template instance specified by dict `d`.

        `ValueError` is raised if "template" is not in `d`.
        """
        return super().from_dict(d, **kwargs)

    def child(self, factory, *args, **kwargs):
        """Return a child template object.

        The actual creation of the object is delegated to the appropriate
        subclass based on the type of `factory`:

        1. `factory` is a `~dasha.web.templates.Template` instance. The
        instance is added as-is as the child of this object. `ValueError`
        is raised if `args` or `kwargs` are set.

        2. `factory` is a Dash component class, (e.g.,
        `~dash_html_components.Div`). A
        `~dasha.web.templates.ComponentTemplate` object is created and
        returned. `args` and `kwargs` are passed to the constructor.

        3. `factory` is a Dash component instance. The instance is wrapped in a
        `~dasha.web.templates.ComponentWrapper` object and returned.
        `ValueError` is raised if `args` or `kwargs` are set.

        `ValueError` is raised if `factory` does not conform to the cases
        listed above.

        """
        def ensure_no_extra_args():
            if args or kwargs:
                raise ValueError(
                    f"child args and kwargs shall not"
                    f" be specified for {type(factory)}")

        if isinstance(factory, Template):
            ensure_no_extra_args()
            factory.parent = self
            return factory

        if isinstance(factory, DashComponentMeta):
            # dash component cls
            template_cls = _make_component_template_cls(factory)
        elif isinstance(factory, DashComponentBase):
            # dash component instance
            ensure_no_extra_args()
            args = (factory, )
            template_cls = ComponentWrapper
        else:
            raise ValueError(
                    f"unable to create child template"
                    f" from type {type(factory)}")
        return template_cls(*args, **kwargs, parent=self)

    def grid(self, nrows, ncols, squeeze=True):
        """Return a grid layout."""
        result = np.full((nrows, ncols), None, dtype=object)
        current_row = None
        for i in range(nrows):
            for j in range(ncols):
                if j == 0:
                    current_row = self.child(dbc.Row)
                result[i, j] = current_row.child(dbc.Col)
        if squeeze:
            if nrows == 1 or ncols == 1:
                result = result.ravel()
            if nrows == 1 and ncols == 1:
                result = result[0]
        return result

    @staticmethod
    def _resolve_template_cls(arg):
        """Return a template class specified by `arg`.

        First, `arg` is resolved to an object using `tollan.utils.getobj`,
        then it is checked against the following cases:

        1. `~dasha.web.templates.Template`. `arg` is returned if it
        is a final template class.

        2. `~types.ModuleType`. The last module attribute that is a
        `~dasha.web.templates.Template` and is marked final is returned.
        In particular, if attribute ``_resolve_template_cls`` is
        present in the module, the value is used.

        3. `ValueError` is raised if none of the above.

        """
        logger = get_logger()

        _arg = arg  # for logging
        if isinstance(arg, str):
            arg = getobj(arg)
        # check if _resolve_template_cls attribute is present
        if inspect.ismodule(arg) and hasattr(arg, "_resolve_template_cls"):
            arg = getattr(arg, '_resolve_template_cls')

        if _is_final_template_cls(arg):
            template_cls = arg
        elif inspect.ismodule(arg):
            template_cls_members = list(filter(
                        # this is to get member attributes that
                        # are defined in this module, and is a valid
                        # template class.
                        lambda m: (
                            _is_final_template_cls(m[1]) and
                            m[1].__module__ == arg.__name__),
                        inspect.getmembers(arg)
                        ))
            if not template_cls_members:
                raise ValueError(
                        f"no valid final template class found in {arg}")
            # sort and return the last
            # issue a warning if multiple template class are found
            # but the actual class name is omitted
            template_cls = sorted(
                    template_cls_members,
                    key=lambda o: inspect.getsourcelines(o[1])[1])[-1][1]
            if len(template_cls_members) > 1:
                logger.warning(
                    f"multiple final template class found in {arg}, "
                    f"the last one is used. Specify the class name to "
                    f"suppress this warning.")
        else:
            raise ValueError(f"cannot resolve template class from {arg}")
        logger.debug(
                f"resolved template {_arg} as {template_cls}")
        # By design, importing the final template class will register the
        # subclass in the template registry. So we just retrieve it from the
        # registry.
        key = Template._make_registry_key(template_cls)
        assert key in Template._template_registry
        return Template._template_registry[key]


def _is_final_template_cls(m):
    """Returns True if `m` is a template class and is marked final.

    Final template classes are registered to
    `~dasha.templates.Template._template_registry` when declared.

    Non-final template classes shall not be used directly.
    """
    return (inspect.isclass(m) and issubclass(m, Template) and
            m._template_is_final)


class ComponentWrapper(Template):
    """A class that wraps a Dash component instance."""

    _template_is_final = True

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


class ComponentRoot(Template):
    """A class that serves as a virtual root component.

    This is useful to define dynamic layout within callbacks."""

    _template_is_final = True

    def __init__(self, id):
        self._rootid = id
        super().__init__(parent=None)

    @property
    def idbase(self):
        self._rootid

    @property
    def id(self):
        return self._rootid

    def setup_layout(self, app):
        super().setup_layout(app)

    @property
    def layout(self):
        return [c.layout for c in self.children]


class ComponentTemplate(Template):
    """A class that wraps a Dash component type.

    Instances of this class is typically created from calling the
    :meth:`~dasha.web.templates.Template.child` method, which allows declaring
    a tree of components with automatic unique ids.

    Instances of this class serves as a lazy evaluation proxy around a native
    Dash components. Dash component properties on the template instance are
    passed to the actual component constructor when the `layout` property is
    queried.

    This allows one to define a set of interrelated components as a "template"
    and use multiple instances of it in a single page application, without the
    need to worrying about possible confliction in the ids.

    Furthermore, the easy-to-create tree structure through (chaining of)
    :meth:`~dasha.web.templates.Template.child` allows arbitrarily complex
    layouts to be created in a relatively compact syntax.

    """

    _component_cls = NotImplemented
    """To be overridden with Dash component type in subclasses."""
    _component_schema = None
    """To be overridden with custom schema in subclasses."""

    _component_prop_names = None
    _template_is_final = False

    _reserved_prop_names = ('layout', 'height')

    def __init_subclass__(cls):

        def _get_component_prop_names(component_cls):
            if issubclass(component_cls, DashComponentBase):
                return inspect.getfullargspec(component_cls.__init__).args[1:]
            return None

        # here we tag the finalness according to presence of _component_cls
        if cls._component_cls is NotImplemented:
            cls._component_prop_names = None
            cls._template_is_final = False
        else:
            # generate property list
            prop_names = _get_component_prop_names(
                    cls._component_cls)
            cls._component_prop_names = prop_names
            cls._template_is_final = True
        # here we generate the namespace schema based on the component schema
        if cls._component_schema is not None:
            _schema = {
                        # we need to exclude the _namespace_* entries
                        # to avoid override the subclass settings.
                        Optional(And(
                            str,
                            lambda s: not s.startswith('_namespace_')
                            )): object
                        }
            rupdate(_schema, cls._component_schema.schema)
            cls._namespace_from_dict_schema = Schema(
                    _schema,
                    ignore_extra_keys=True)
        super().__init_subclass__()

    def __init__(self, *args, **kwargs):
        # put args in to kwargs by inspect the prop list.
        # this allows the syntax of creating template similar to
        # creating the underlying Dash components.
        for i, arg in enumerate(args):
            prop_name = self._component_prop_names[i]
            if prop_name in kwargs:
                raise ValueError(
                    f"duplicated argument {prop_name} in args and kwargs.")
            kwargs[prop_name] = arg
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)

        for k, v in kwargs.items():
            if k in self._reserved_prop_names:
                # use a alias version of it.
                k = f'{k}_'
            setattr(self, k, v)

    @classmethod
    def _ensure_template(cls, value):
        if value is None:
            return None
        if isinstance(value, Template):
            return value
        return ComponentWrapper(value)

    @IdTree.parent.setter
    def parent(self, value):
        # we make sure the value set here is wrapped as a template
        IdTree.parent.fset(self, self._ensure_template(value))

    @property
    def id(self):
        return getattr(self, '_static_id', IdTree.id.fget(self))

    @id.setter
    def id(self, value):
        self._static_id = value

    @IdTree.children.setter
    def children(self, children):
        """Setter to ensure the children is also a `Template` instance."""
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
        """The layout generated from traversing the component tree.

        The traversing is depth first.

        .. note::
            Properties with callable values are evaluated the time the property
            is queried.
        """

        component_kwargs = dict()
        for prop_name in self._component_prop_names:
            if prop_name in self._reserved_prop_names:
                attr_name = f'{prop_name}_'
            else:
                attr_name = prop_name
            if not hasattr(self, attr_name):
                continue
            prop_value = getattr(self, attr_name)
            if prop_name == 'children':
                prop_value = tuple(c.layout for c in prop_value)
                if len(prop_value) == 1:
                    # let dash handle the re-wrapping
                    prop_value = prop_value[0]
            if callable(prop_value):
                prop_value = prop_value()
            component_kwargs[prop_name] = prop_value
        return self._component_cls(**component_kwargs)


def _make_component_template_cls(component_cls):
    """Return a `~dasha.web.templates.ComponentTemplate` subclass for given
    Dash component type."""
    # here we try get the created classes from the registry
    registry_key = Template._make_registry_key(component_cls)
    if registry_key in Template._template_registry:
        return Template._template_registry[registry_key]

    # create if not exists
    # this will automatically register to _template_registry
    return type(
            f"{component_cls.__name__}",
            (ComponentTemplate, ), dict(
                _component_cls=component_cls,
                _template_registry_key=registry_key,
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
    # TODO rewrite this to use namespace schema.

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
