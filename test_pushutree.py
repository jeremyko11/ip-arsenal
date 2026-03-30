import urllib.request, urllib.error, json

req = urllib.request.Request(
    'http://localhost:8765/api/pushutree/create',
    data=json.dumps({
        'source_id': '5e91f2b3-25a5-4a6f-be2f-f4acdef2e7f5',
        'episode_count': 4,
        'platform': 'test',
        'style': 'test'
    }).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    r = urllib.request.urlopen(req, timeout=10)
    print('OK:', r.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', 'replace')
    print(f'ERROR {e.code}:', body)
except Exception as ex:
    print('EXCEPTION:', ex)
