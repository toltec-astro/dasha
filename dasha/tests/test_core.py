#!/usr/bin/env python

from ..core import Extension, Site


class MockExt:

    config = dict()

    @classmethod
    def init_app(cls):
        pass

    @classmethod
    def init_ext(cls, config):
        cls.config.update(config)
        return cls.config


def test_ext():
    ext = Extension.from_dict(dict(module=MockExt, config={'a': 1}))

    assert ext.config == {'a': 1}

    ext = Extension.from_dict(dict(
        module='dasha.tests.test_core:MockExt', config={'b': 2}))

    assert ext.config == {'b': 2}
    assert ext.ext == {'a': 1, 'b': 2}


def test_site():
    MockExt.config.clear()

    server = 1
    site = Site.from_dict({
        'extensions': [
            {
                'module': MockExt,
                'config': {'a': 1}
                },
            {
                'module': 'dasha.tests.test_core:MockExt',
                'config': {'b': 2}
                },
            ],
        'server': server,
        'server_config': {
            'c': 3
            }
        })

    assert site.extensions[0].module is MockExt
    assert site.extensions[0].ext == {'a': 1, 'b': 2}
    assert site.server == 1
    assert site.server_config == {'c': 3}

    def server2():
        return 2

    class C:
        DASHA_SITE = {
            'extensions': [
                {
                    'module': MockExt,
                    'config': {'a': 1}
                    },
                {
                    'module': 'dasha.tests.test_core:MockExt',
                    'config': {'b': 2}
                    },
                ],
            'server': server2,
            }

    site = Site.from_object(C)

    assert site.extensions[0].module is MockExt
    assert site.extensions[0].ext == {'a': 1, 'b': 2}
    assert site.server == 2
    assert site.server_config == dict()
