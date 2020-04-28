#! /usr/bin/env python

import wrapt


__all__ = ['ExtensionProxy', ]


class ExtensionProxy(wrapt.ObjectProxy):
    """This class provide lazy initialization of extension.

    For example of usage, see `db.py`.
    """

    def __init__(self, cls, ext):
        """Create a proxy object.

        Two special attributes in the `ext` module are expected. ``ext.init``
        shall be a function that takes `cls` as the sole argument and
        actually create the extension object. ``ext.init_app`` shall be
        a function that takes ``server`` and initialize the extension.

        Parameters
        ----------
        cls: type
            The extension class.

        ext: module
            A module in which the extension related code resides.

        """
        self._self_cls = cls
        self._self_ext = ext
        self._self_initialized = False
        super().__init__(None)

    @property
    def _extension(self):
        return self._self_ext

    def __getattr__(self, name, *args):
        if not self._self_initialized:
            # initialize extension
            ext = self._self_ext.init(self._self_cls)
            self.__wrapped__ = ext
            self._self_initialized = True
        return super().__getattr__(name, *args)
