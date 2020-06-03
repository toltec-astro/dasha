#! /usr/bin/env python

from ..ipc_backends.rejson import JsonPath, RejsonIPC
import redis
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


def test_rejson_ipc_offline():
    inst = RejsonIPC('test')

    assert RejsonIPC._make_redis_key('test') == '_ipc_test'
    assert inst.label == 'test'
    assert inst.redis_key == '_ipc_test'

    assert inst._create_rejson_data(obj=123, time=456) == {
            '_ipc_meta': {
                'key': '_ipc_test',
                'rev': 0,
                'created_at': 456,
                'updated_at': 456,
                },
            '_ipc_obj': 123
            }
    assert inst._resolve_obj_path('.') == '._ipc_obj'
    assert inst._resolve_obj_path('.key') == '._ipc_obj.key'
    assert inst._resolve_obj_path('key') == '._ipc_obj.key'
    assert inst._resolve_obj_path('') == '._ipc_obj'
    assert inst._resolve_meta_path('key') == '._ipc_meta.key'
    assert inst._resolve_meta_path('') == '._ipc_meta'


@pytest.fixture
def rejson_ipc_conn():
    inst = RejsonIPC('test')
    inst.init_ipc('redis://localhost/15')
    conn = inst._connection
    conn.flushdb()
    return conn, inst


def test_rejson_ipc_check_conn(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    conn.set('test_redis', 'good')
    assert conn.get('test_redis') == 'good'


def test_rejson_ipc_data_layout(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    inst.ensure_obj(obj=123)

    data = conn.jsonget(inst.redis_key, '.')

    assert data['_ipc_obj'] == 123
    assert data['_ipc_meta']['key'] == inst.redis_key
    assert data['_ipc_meta']['rev'] == 0

    assert inst.get_rejson_data() == data

    assert inst.get_meta() == data['_ipc_meta']
    assert inst.get_meta('rev') == 0


def test_rejson_ipc_op_uninitialized(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    data = conn.jsonget(inst.redis_key, '.')
    assert data is None
    assert inst.get_rejson_data() is None
    assert inst.get_meta() is None
    assert not inst.is_initialized()
    assert inst.type() is None
    assert inst.is_null() is None


def test_rejson_ipc_op_null(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    inst.ensure_obj()
    assert inst.is_initialized()
    assert inst.type() == 'null'
    assert inst.is_null()

    obj = inst.get()
    assert inst.get() is None

    meta = inst.get_meta()
    assert meta['rev'] == 0

    # check repeated get
    assert obj is inst.get()
    assert meta == inst.get_meta()


def test_rejson_ipc_op_ensure_obj_exist(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    inst.set(123)
    inst.ensure_obj('str')

    assert inst.is_initialized()
    assert inst.type() == 'integer'
    assert not inst.is_null()

    obj = inst.get()
    assert inst.get() == 123

    meta = inst.get_meta()
    assert meta['rev'] == 0

    # check repeated get
    assert obj is inst.get()
    assert meta == inst.get_meta()


def test_rejson_ipc_op_update_obj(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn
    inst.ensure_obj({'a': 123})

    assert inst.is_initialized()
    assert inst.type() == 'object'
    assert inst.type('a') == 'integer'
    assert not inst.is_null()

    obj = inst.get()
    assert inst.get() == {'a': 123}

    meta = inst.get_meta()
    assert meta['rev'] == 0

    # check repeated get
    assert obj == inst.get()
    assert meta == inst.get_meta()

    # update data
    inst.set('str', path='a')

    assert inst.is_initialized()
    assert inst.type() == 'object'
    assert inst.type('a') == 'string'
    assert not inst.is_null()

    obj = inst.get()
    assert inst.get() == {'a': 'str'}

    meta1 = inst.get_meta()
    assert meta1['rev'] == 1
    assert meta1['created_at'] == meta['created_at']
    assert (meta1['updated_at'][0] + meta1['updated_at'][1] * 1e-6) > \
           (meta['updated_at'][0] + meta['updated_at'][1] * 1e-6)


def test_rejson_ipc_op_subpath(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn

    with pytest.raises(
            redis.exceptions.ResponseError):
        inst.set(123, path='a')
    inst.set({'a': 123})
    inst.set({'b': 'str'}, path='b')
    obj = inst.get()
    assert obj == {
            'a': 123,
            'b': {'b': 'str'}
            }
    meta = inst.get_meta()
    assert meta['rev'] == 1


def test_rejson_ipc_op_pipeline(rejson_ipc_conn):
    conn, inst = rejson_ipc_conn

    inst.set(dict())
    for i in range(10):
        inst.set(i, path=f'k{i}')
    obj = inst.get()
    assert obj == {f'k{i}': i for i in range(10)}
    meta = inst.get_meta()
    assert meta['rev'] == 10

    with inst.pipeline as p:
        inst.reset(dict())
        for i in range(10):
            inst.set(i * 2, path=f'k{i}')
        p.execute()
    obj = inst.get()
    assert obj == {f'k{i}': i * 2 for i in range(10)}
    meta = inst.get_meta()
    assert meta['rev'] == 10

    assert inst.query_obj('objkeys', path='.') == [f'k{i}' for i in range(10)]
    # pipeline get
    with inst.pipeline as p:
        for i in range(10):
            inst.get(f'k{i}')
        result = p.execute()
    assert result == [i * 2 for i in range(10)]
    meta = inst.get_meta()
    assert meta['rev'] == 10
