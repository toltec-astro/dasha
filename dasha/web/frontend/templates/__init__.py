#! /usr/bin/env python
from ....utils.log import get_logger
from ....utils.fmt import pformat_dict
from ..utils import odict_from_list
import importlib
from copy import deepcopy

from ..common import SimplePage


class SimplePageTemplate(object):

    _template_params = list()

    logger = get_logger()

    def __init__(self, **params):
        for k, v in params.items():
            if k == 'sources':
                if isinstance(v, list):
                    v = odict_from_list(v, key=lambda i: i['label'])
            if k in self.__class__._template_params:
                setattr(self, k, deepcopy(v))
            else:
                self.logger.warning(
                        f"unrecognized template param {k}={v}")


def _get_template_cls(name):
    module = importlib.import_module(
            f".{name}", package=__package__)
    return module.template_cls


def create_page_from_dict(config, **kwargs):
    logger = get_logger()
    # print(config)
    logger.debug(f"create page from dict: {pformat_dict(config)}")
    template_cls = _get_template_cls(config.pop('template'))
    return SimplePage(
        label=config['label'],
        module=template_cls(**config),
        **kwargs)
