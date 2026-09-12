import urllib.request
import json

def test_api(name):
    req = urllib.request.Request(
        'http://localhost:8000/api/resolve',
        data=json.dumps({'name': name}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f'=== Query: "{name}" ===')
        print(json.dumps(data['decision'], indent=2))

if __name__ == '__main__':
    test_api('Open AI, Inc.')
    test_api('dopemind')
    test_api('Something Random')
