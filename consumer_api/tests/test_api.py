import io
import time
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from consumer_api.main import create_app
from consumer_api.storage import Store

HEADERS={'X-SecureSense':'1'}

@pytest.fixture
def client():
    with TestClient(create_app(Store(''),session_secret='audit-test-secret')) as client:
        yield client

def wav(silent=False):
    stream=io.BytesIO()
    t=np.arange(32000)/16000
    sf.write(stream,np.zeros(32000) if silent else .25*np.sin(t*2*np.pi*220),16000,format='WAV')
    return stream.getvalue()

def test_health_and_capabilities(client):
    assert client.get('/api/v1/health').json()['database']=='unavailable'
    assert client.get('/api/v1/capabilities').json()['speaker_verification'] is False

@pytest.mark.parametrize('payload',[{}, {'text':''},{'text':'  '},{'text':'x'*12001},{'text':'Hello world','context':'invalid'},{'text':'Hello world','extra':True}])
def test_validation(client,payload):
    response=client.post('/api/v1/analyses/text',json=payload,headers=HEADERS)
    assert response.status_code==422
    assert 'input' not in response.json()

def test_origin_and_session(client):
    assert client.post('/api/v1/analyses/text',json={'text':'test'}).status_code==403
    assert client.post('/api/v1/analyses/text',json={'text':'test'},headers={**HEADERS,'Origin':'https://attacker.invalid'}).status_code==403
    response=client.get('/api/v1/health')
    assert response.headers['cache-control']=='no-store'
    assert client.cookies.get('ss_session')

def test_text_and_unavailable_storage(client):
    result=client.post('/api/v1/analyses/text',json={'text':'Tell me your OTP immediately. Code is 123456'},headers=HEADERS)
    assert result.status_code==200
    item=result.json()
    assert item['level']=='high' and '123456' not in str(item)
    assert client.get('/api/v1/analyses/'+item['id']).status_code==200
    assert client.post('/api/v1/analyses/'+item['id']+'/save',headers=HEADERS).status_code==503
    assert client.get('/api/v1/analyses').status_code==503

def test_invalid_audio_never_gets_a_score(client):
    for filename,content,status in [('bad.exe',b'invalid',415),('bad.wav',b'invalid',422),('quiet.wav',wav(True),422)]:
        res=client.post('/api/v1/analyses/audio',files={'audio':(filename,content)},headers=HEADERS)
        assert res.status_code==status
        assert 'score' not in res.text

def test_audio_with_reviewed_transcript(client):
    response=client.post('/api/v1/analyses/audio',files={'audio':('test.wav',wav(),'audio/wav')},data={'transcript':'Tell me your OTP immediately.'},headers=HEADERS)
    assert response.status_code==202
    for _ in range(50):
        data=client.get('/api/v1/jobs/'+response.json()['id']).json()
        if data['stage']=='completed':break
        time.sleep(.01)
    assert data['result']['provenance']=='user_supplied_transcript'
    assert data['result']['level']=='high'
    assert data['result']['voice']['speaker_verification']=='unavailable'

def test_model_unavailable(client,monkeypatch):
    monkeypatch.setattr('consumer_api.main.asr_available',lambda:False)
    response=client.post('/api/v1/analyses/audio',files={'audio':('test.wav',wav(),'audio/wav')},headers=HEADERS)
    assert response.status_code==503
    assert 'transcript' in response.json()['detail']

def test_no_secret_echo(client):
    response=client.post('/api/v1/analyses/text',json={'text':123456789,'password':'secret123'},headers=HEADERS)
    assert 'secret123' not in response.text and '123456789' not in response.text

def test_complaint_and_rights(client):
    response=client.post('/api/v1/complaint-drafts',json={'category':'consumer','details':'The refund has not arrived after the return.','resolution':'Please review the refund.'},headers=HEADERS)
    assert response.status_code==200
    assert response.json()['submitted'] is False
    assert 'refund has not arrived' in response.json()['text']
    assert len(client.get('/api/v1/rights').json())==6
    channels=client.get('/api/v1/reporting-channels').json()
    assert {c['id'] for c in channels}=={'consumer','commission','cybercrime'}

def test_unknown_job(client):
    assert client.get('/api/v1/jobs/00000000-0000-0000-0000-000000000000').status_code==404
