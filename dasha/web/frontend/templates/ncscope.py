#! /usr/bin/env python

from tolteca.utils.nc import ncopen, ncinfo, ncstr
from tolteca.utils.log import get_logger
from contextlib import ExitStack
from pathlib import Path
from functools import lru_cache
from collections import OrderedDict


class NcScope(ExitStack):
    """A class that provides live view to netCDF file."""

    logger = get_logger()

    cache_size = 128

    def __init__(self, source):
        super().__init__()
        self._open_nc(source)

    def _open_nc(self, source):
        nc, _close = ncopen(source)
        self.push(_close)
        self.logger.debug("ncinfo: {}".format(ncinfo(nc)))
        self.nc = nc
        self.filepath = Path(nc.filepath())

    def sync(self):
        self.nc.sync()

    def var(self, name):
        return self.nc.variables[name]

    def dim(self, name):
        return self.nc.dimensions[name].size

    def read_as_dict(self, keys):
        return OrderedDict([(k, self._read_key(k)) for k in keys])

    def _read_key(self, key):

        def read_var(key):
            var = self.var(key)
            if not var.dimensions or (var.dtype == '|S1' and len(
                    var.dimensions) == 1):
                v = var[:]
                try:
                    if var.dtype == "|S1":
                        return ncstr(var)
                    return "{:g}".format(v)
                except ValueError:
                    return v
            if var.size < 20:
                return var[:]
            return "[{}]".format(", ".join(d for d in var.dimensions))

        def read_dim(key):
            dim = self.dimensions[key]
            return dim.size

        def read_attr(key):
            return self.nc.getncattr(key)

        if key in self.nc.variables:
            return read_var(key)
        elif key in self.nc.dimensions:
            return read_dim(key)
        elif key in self.nc.ncattrs():
            return read_attr(key)
        else:
            return None

    @classmethod
    @lru_cache(maxsize=cache_size)
    def from_filepath(cls, filepath):
        return cls(source=filepath)

    @classmethod
    def from_link(cls, link):
        return cls.from_filepath(Path(link).resolve())
