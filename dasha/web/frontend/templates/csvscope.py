#! /usr/bin/env python

#from ....utils.nc import ncopen, ncinfo, ncstr
#from ....utils.log import get_logger
from contextlib import ExitStack
from pathlib import Path
from functools import lru_cache
from collections import OrderedDict
import pandas as pd

class CsvScope(ExitStack):
    """A class that provides live view to csv file."""

    #logger = get_logger()

    cache_size = 128

    def __init__(self, source):
        super().__init__()
        self._open_csv(source)

    def _open_csv(self, source):
        df = pd.read_csv(source, header=None, delim_whitespace=True)
        self.df = df
        self.filepath = source
        # get length of df's columns
        num_cols = len(list(df))
        self.num_cols = num_cols
        rng = range(0, num_cols)
        new_cols = [str(i) for i in rng]
        df.columns = new_cols[:num_cols]

    def sync(self):
        self._open_csv(self.filepath)

    def var(self, name):
        return self.df[name]

    def dim(self, name):
        return 1

    @classmethod
    @lru_cache(maxsize=cache_size)
    def from_filepath(cls, filepath):
        return cls(source=filepath)

    @classmethod
    def from_link(cls, link):
        return cls.from_filepath(Path(link).resolve())

    
if __name__ == '__main__':
    c = CsvScope('/data_lmt/tempsens/tempsens.csv')
    print(c.df['0'])
    print(c.df['1'])
    print(c.df['63'])
    
    
    
