from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_email_cadences_endpoint_returns_seed_data():
    response = client.get('/api/email/cadences')
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]['name']


def test_email_cadence_can_be_created():
    payload = {
        'name': 'Welcome series',
        'subject': 'Welcome',
        'channel': 'Email',
        'days_after': 3,
        'status': 'Draft',
    }
    response = client.post('/api/email/cadences', json=payload)
    assert response.status_code == 200
    created = response.json()
    assert created['name'] == payload['name']


def test_email_settings_can_be_updated_by_manager():
    payload = {
        'smtp_host': 'smtp.example.com',
        'from_email': 'ops@example.com',
        'reply_to': 'support@example.com',
        'role': 'Manager',
    }
    response = client.post('/api/email/settings', json=payload)
    assert response.status_code == 200
    assert response.json()['smtp_host'] == payload['smtp_host']


def test_email_settings_reject_non_manager_update():
    payload = {
        'smtp_host': 'smtp.example.com',
        'from_email': 'ops@example.com',
        'reply_to': 'support@example.com',
        'role': 'Sales',
    }
    response = client.post('/api/email/settings', json=payload)
    assert response.status_code == 403
