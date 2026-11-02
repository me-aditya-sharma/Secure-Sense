import pytest
from consumer_api.analysis import analyze, redact

@pytest.mark.parametrize('text,expected',[
 ('Never share your OTP with anyone.',None),
 ('Never share the OTP with callers.',None),
 ('Do not share your password with anyone.',None),
 ("Don't give your PIN to a caller.",None),
 ('We will not ask for your verification code.',None),
 ('No need to pay a fee for your refund.',None),
 ('Avoid installing remote access tools.',None),
 ('Your refund has been processed to the original payment method.',None),
 ('Please process a refund for my returned order.',None),
 ('Your order will arrive tomorrow afternoon.',None),
 ('The package has been delivered to reception.',None),
 ('Check your refund in the official app.',None),
 ('I would like a written receipt for this purchase.',None),
 ('Please contact customer support through the official app.',None),
 ('You may return the item within thirty days.',None),
 ('Tell me your OTP immediately.','credentials'),
 ('Share the OTP with me.','credentials'),
 ('Give me your password please.','credentials'),
 ('Please provide your verification code.','credentials'),
 ("What's your PIN?",'credentials'),
 ('Read me the code you just received.','credentials'),
 ('Pay a processing fee to release your refund.','refund_payment'),
 ('Your refund requires a payment fee.','refund_payment'),
 ('Install AnyDesk to receive support.','remote_access'),
 ('Download TeamViewer so we can help.','remote_access'),
 ('Share your screen with me.','remote_access'),
 ('Transfer money to the new account.','payment'),
 ('Your account will be blocked.','threat'),
 ("Don't tell your family about this.",'isolation'),
 ('Do not contact the bank yourself.','isolation'),
 ('This is your bank calling.','identity_claim'),
 ('Click https://example.com to check.','link'),
 ('Never share your OTP, but tell me your PIN now.','credentials'),
 ('Never share your OTP. Transfer money right now.','payment'),
])
def test_context_rules(text,expected):
    result=analyze(text)
    ids={f['id'] for f in result['evidence']}
    if expected is None:
        assert not ids
    else:
        assert expected in ids
        for finding in result['evidence']:
            assert result['transcript'][finding['start']:finding['end']]==finding['excerpt']

def test_insufficient():
    assert analyze('Hi')['level']=='insufficient'
    assert analyze('कृपया मुझे अपना कोड दें')['level']=='insufficient'

def test_monotonic_and_deterministic():
    message='Tell me your OTP immediately.'
    a=analyze(message)
    b=analyze(message)
    assert a['score']==b['score'] and a['evidence']==b['evidence']
    assert a['level']=='high'
    assert analyze(message+' This is your bank calling.')['score']>=a['score']

def test_redaction():
    text=redact('OTP is 123456. My password: hunter2 email me a@example.com or call +91 98765 43210')
    for secret in ['123456','hunter2','a@example.com','98765']:
        assert secret not in text

def test_no_numeric_confidence_or_voice_claim():
    result=analyze('Your order will arrive tomorrow.')
    assert result['voice']['synthetic_speech']=='unavailable'
    assert 'confidence' not in result
    assert 'does not' in result['summary']
