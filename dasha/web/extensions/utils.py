#! /usr/bin/env python


__all__ = ['KeyDecorator', ]


class KeyDecorator(object):
    """A class to handle key prefixing and suffixing.

    Parameters
    ----------
    prefix : str or None
        Prefix to apply to key.

    suffix : str of None
        Suffix to apply to key.
    """

    def __init__(self, prefix=None, suffix=None):
        self._prefix = prefix or ''
        self._suffix = suffix or ''

    @property
    def prefix(self):
        return self._prefix

    @property
    def suffix(self):
        return self._suffix

    def _decorate(self, key):
        return f"{self._prefix}{key}{self._suffix}"

    def decorate(self, *keys):
        """Apply prefix and suffix to `keys`.

        """
        result = tuple(map(self._decorate, keys))
        if len(keys) == 1:
            return result[0]
        return result

    def _resolve(self, key):
        start = None
        stop = None
        if key.startswith(self._prefix):
            start = len(self._prefix)
        if key.endswith(self._suffix):
            stop = len(key) - len(self._suffix)
        return key[start:stop]

    def resolve(self, *keys):
        """Remove prefix and suffix from `keys`.

        """
        result = tuple(map(self._resolve, keys))
        if len(keys) == 1:
            return result[0]
        return result

    def __call__(self, *args):
        """Alias of `decorate`."""
        return self.decorate(*args)

    def r(self, *args):
        """Alias of `resolve`."""
        return self.resolve(*args)
