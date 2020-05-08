#! /usr/bin/env python

from ..ipc_backends.rejson import JsonPath, RejsonIPC
import pytest


def test_jsonpath_construct():
    assert JsonPath().strPath == JsonPath.root
    assert JsonPath('').strPath == ''
    assert JsonPath(JsonPath('')).strPath == ''
    with pytest.raises(
            ValueError, match='path cannot be ends with'
            ):
        JsonPath('..')


def test_jsonpath_str():
    assert str(JsonPath('')) == ''
    assert str(JsonPath('abc')) == 'abc'
    assert f"{JsonPath('.abc')}" == '.abc'


def test_jsonpath_is_absolute():
    check = [
            ('.', True),
            ('.abc', True),
            ('', False),
            ('abc', False)
            ]
    for p, v in check:
        assert JsonPath(p).is_absolute() is v


def test_jsonpath_is_root():
    check = [
            ('.', True),
            ('.abc', False),
            ('', False),
            ('abc', False)
            ]
    for p, v in check:
        assert JsonPath(p).is_root() is v


def test_jsonpath_is_empty():
    check = [
            ('.', False),
            ('.abc', False),
            ('', True),
            ('abc', False)
            ]
    for p, v in check:
        assert JsonPath(p).is_empty() is v


def test_jsonpath_eq():
    assert JsonPath('abc') == JsonPath('abc')
    assert JsonPath('abc') != JsonPath('.abc')
    assert JsonPath(JsonPath.root) == JsonPath()
    assert 'abc' == JsonPath('abc')
    assert JsonPath.root == JsonPath()
    with pytest.raises(
            AttributeError, match="has no attribute 'strPath'"
            ):
        assert 1 == JsonPath('abc')


def test_jsonpath_joinpath():
    assert JsonPath().joinpath('') == '.'
    assert JsonPath().joinpath('a') == '.a'
    assert JsonPath('.b').joinpath('a') == '.b.a'
    assert JsonPath('.b').joinpath('') == '.b'
    assert JsonPath('b').joinpath('c') == 'b.c'

    with pytest.raises(
            ValueError, match='Only can join relative path'
            ):
        assert JsonPath().joinpath('.a')


def test_jsonpath_relative_to():
    assert JsonPath(JsonPath.root).relative_to(JsonPath.root) == ''
    assert JsonPath('.a.c').relative_to(JsonPath.root) == 'a.c'
    assert JsonPath('.a.c').relative_to('.a') == 'c'
    assert JsonPath('a.c').relative_to(JsonPath('a')) == 'c'

    with pytest.raises(
            ValueError, match='both paths should be relative or absolute'
            ):
        JsonPath('.a.c').relative_to('')
        JsonPath('a.c').relative_to(JsonPath.root)

    with pytest.raises(
            ValueError, match='unable to compute relative path'
            ):
        JsonPath('.a.b').relative_to('.a.c')


def test_jsonpath_parent():
    assert JsonPath('.a.b.c').parent == '.a.b'
    assert JsonPath('a.b.c').parent == 'a.b'
    assert JsonPath('').parent is None
    assert JsonPath(JsonPath.root).parent is None


def test_jsonpath_name():
    assert JsonPath('.').name == '.'
    assert JsonPath('').name == ''
    assert JsonPath('.a.b.c').name == 'c'
    assert JsonPath('a.b.c').name == 'c'


def test_rejson_ipc():
    inst = RejsonIPC('test')

    assert RejsonIPC._make_redis_key('test') == '_ipc_test'
    assert inst.label == 'test'
    assert inst.redis_key == '_ipc_test'

    assert RejsonIPC._ensure_entry(dict(_ipc_rev=0), '_ipc_rev', 1) == {
            '_ipc_rev': 0
            }
    assert RejsonIPC._ensure_entry(dict(), '_ipc_rev', 1) == {
            '_ipc_rev': 1
            }
    assert inst._ensure_metadata(dict()) == {
            '_ipc_rev': 0,
            '_ipc_obj': None,
            '_ipc_key': '_ipc_test',
            }
    assert inst._ensure_metadata(dict(_ipc_obj=1, _ipc_key='_ipc_test')) == {
            '_ipc_rev': 0,
            '_ipc_obj': 1,
            '_ipc_key': '_ipc_test',
            }
    with pytest.raises(
            ValueError, match='inconsistent obj key'
            ):
        inst._ensure_metadata(dict(_ipc_key='_ipc_abc'))

    assert inst._get_redis_path('.') == '._ipc_obj'
    assert inst._get_redis_path('.key') == '._ipc_obj.key'
    assert inst._get_redis_path('key') == '._ipc_obj.key'
    assert inst._get_redis_path('') == '._ipc_obj'
