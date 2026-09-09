import urllib.request
import json
import urllib.error

data = json.dumps({'user_id': 1, 'audio_data': 'dummy'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/analyze', data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Body:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("Status:", e.code)
    print("Body:", e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
