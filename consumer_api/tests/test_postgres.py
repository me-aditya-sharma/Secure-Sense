"""Real PostgreSQL integration, using a new disposable schema in the new database."""
import os
from uuid import uuid4
import psycopg2
from psycopg2.extensions import make_dsn
import pytest
from fastapi.testclient import TestClient
from consumer_api.main import create_app
from consumer_api.storage import Store

@pytest.fixture
def store():
    dsn=os.getenv('SS_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set SS_TEST_DATABASE_URL to a dedicated test database')
    schema='ss2_test_'+uuid4().hex
    conn=psycopg2.connect(dsn)
    conn.autocommit=True
    with conn.cursor() as cur:
        cur.execute('CREATE SCHEMA '+schema)
    instance=Store(make_dsn(dsn,options='-csearch_path='+schema))
    instance.initialize()
    yield instance
    with conn.cursor() as cur:
        cur.execute('DROP SCHEMA '+schema+' CASCADE')
    conn.close()

def test_persistence_ownership_and_delete(store):
    app=create_app(store,session_secret='persistent-test-secret')
    h={'X-SecureSense':'1'}
    with TestClient(app) as alice, TestClient(app) as bob:
        result=alice.post('/api/v1/analyses/text',json={'text':'Tell me your OTP immediately.'},headers=h).json()
        assert alice.post('/api/v1/analyses/'+result['id']+'/save',headers=h).status_code==200
        assert len(alice.get('/api/v1/analyses').json())==1
        assert bob.get('/api/v1/analyses').json()==[]
        assert bob.get('/api/v1/analyses/'+result['id']).status_code==404
        assert bob.delete('/api/v1/analyses/'+result['id'],headers=h).status_code==404
        cookies=dict(alice.cookies)
    with TestClient(create_app(store,session_secret='persistent-test-secret')) as restarted:
        restarted.cookies.update(cookies)
        assert len(restarted.get('/api/v1/analyses').json())==1
        assert restarted.delete('/api/v1/analyses/'+result['id'],headers=h).status_code==200
        assert restarted.get('/api/v1/analyses').json()==[]

def test_expiry_and_redaction(store):
    with TestClient(create_app(store,session_secret='expiry-test')) as c:
        h={'X-SecureSense':'1'}
        item=c.post('/api/v1/analyses/text',json={'text':'Share the OTP immediately. My code is 123456 and password: hunter2'},headers=h).json()
        c.post('/api/v1/analyses/'+item['id']+'/save',headers=h)
        rows=store.query('SELECT payload FROM ss2_records')
        assert '123456' not in str(rows) and 'hunter2' not in str(rows)
        store.query("UPDATE ss2_records SET expires_at=now()-interval '1 second'")
        assert c.get('/api/v1/analyses').json()==[]
