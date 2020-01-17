#! /usr/bin/env python
import importlib
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from ...utils.registry import Registry
from functools import lru_cache
import inspect
from ...utils.log import get_logger


class Template(ABC):
    """An abstract class that defines an encapsulated entity
    around a functional group of dash components and the
    callbacks.

    The child component ids are automatically namespace-d to
    allow re-use of the same template in multiple parts of
    a single page application.
    """

    _template_registry = Registry.create()

    _skip_template_register = False
    """If set to True, this class is skipped from registering
    to the template registry."""

    @staticmethod
    def _make_label(cls):
        return cls.__name__.lower()

    @staticmethod
    def _get_uid_iter():
        uid = 0
        while True:
            yield uid
            uid += 1

    def __init_subclass__(cls):
        if not cls._skip_template_register:
            cls._template_registry.register(cls._make_label(cls), cls)
        cls._uid_iter = cls._get_uid_iter()

    def __init__(self, *, parent=None):
        self._parent = parent
        self._hash = self._make_hash()

    def _prefix_label_with_parent(self, label):
        if self._parent is not None:
            if self._parent._hash is None:
                return label
            return f"{self._parent._hash}-{label}"
        return label

    def _make_hash(self):
        label = f"{self._make_label(self.__class__)}{next(self._uid_iter)}"
        return self._prefix_label_with_parent(label)

    @staticmethod
    @lru_cache(maxsize=None)
    def _make_component_factory(component_cls, static=False):

        class _ComponentWrapper(Template):
            _skip_template_register = True
            _component_cls = component_cls
            _component_prop_names = inspect.getfullargspec(
                       _component_cls.__init__).args[1:]

            logger = get_logger()

            @staticmethod
            def _make_label(cls):
                return f"{cls._component_cls.__name__}"

            def __init__(self, *args, label=None, parent=None, **kwargs):
                super().__init__(parent=parent)
                self._label = label
                for k, v in kwargs.items():
                    if k not in self._component_prop_names:
                        raise RuntimeError(f"invalid prop name {k}")
                    self.logger.debug("set {k} to {v}")
                    setattr(self, k, v)
                self._args = args

            @property
            def layout(self):

                def _get_layout(v):
                    if isinstance(v, Template):
                        print(v.layout)
                        return v.layout
                    return v

                kwargs = {}
                for prop in self._component_prop_names:
                    if hasattr(self, prop):
                        v = getattr(self, prop)
                        if prop == 'children' and isinstance(
                                v, (tuple, MutableSequence)):
                            v = tuple(map(_get_layout, v))
                        else:
                            v = _get_layout(v)
                        kwargs[prop] = v

                if self._label is not None:
                    kwargs['id'] = self._hash
                self.logger.debug(
                        f"create {self._component_cls} with {kwargs}")
                return self._component_cls(*self._args, **kwargs)

        if static:
            # This item is static, i.e., no id is need
            # no hash is used here
            class StaticComponent(_ComponentWrapper):
                _skip_template_register = False

                @staticmethod
                def _make_label(cls):
                    return f"{cls._component_cls.__name__}*"

                # we override the make_hash func so that it
                # use the parent's hash if availabel
                def _make_hash(self):
                    if self._parent is not None:
                        if self._parent._hash is None:
                            return None
                        return f"{self._parent._hash}"
                    return None

            template_cls = StaticComponent

        else:
            class DynamicComponent(_ComponentWrapper):

                _skip_template_register = False

            template_cls = DynamicComponent

        def factory(*args, **kwargs):
            return template_cls(*args, **kwargs)

        return factory

    def make_component(
            self, component_cls,
            *args, label=None, **kwargs):
        cls = self._make_component_factory(
                component_cls, static=label is None)
        return cls(*args, label=label, parent=self, **kwargs)

    @property
    @abstractmethod
    def layout(self):
        return NotImplemented

    @classmethod
    def _get_template_cls(cls, spec):
        """Return the template class specified as `spec`.

        The full format of `spec` is `mod::label`, where
        ``::label`` can be omitted, in which case the label
        is the last part of mod path, i.e., 'a.b' is the
        same as 'a.b::b'
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
        if label not in cls._template_registry:
            raise RuntimeError(
                    f"not able to find template class from spec {spec}"
                    )
        return cls._template_registry[label]

    @classmethod
    def from_dict(cls, config):
        cls = cls._get_template_cls(config['template'])
        return cls.from_dict(config)
