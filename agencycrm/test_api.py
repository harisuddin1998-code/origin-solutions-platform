import urllib.request, json

# Test health
r = urllib.request.urlopen('http://127.0.0.1:8001/api/health')
print('Health:', json.loads(r.read()))

# Test login
data = json.dumps({'email': 'admin@agencycrm.com', 'password': 'admin123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8001/api/auth/login', data=data, headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print('Login:', d['name'], d['role'])
token = d['token']

# Test dashboard
req = urllib.request.Request('http://127.0.0.1:8001/api/dashboard/summary', headers={'Authorization': f'Bearer {token}'})
r = urllib.request.urlopen(req)
print('Dashboard:', json.loads(r.read()))

# Test contacts
req = urllib.request.Request('http://127.0.0.1:8001/api/contacts/', headers={'Authorization': f'Bearer {token}'})
r = urllib.request.urlopen(req)
print('Contacts:', json.loads(r.read()))

print('\n✅ All API tests passed!')