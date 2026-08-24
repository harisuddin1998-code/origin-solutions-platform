from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_dashboard_summary_endpoint():
    response = client.get('/api/dashboard/summary')
    assert response.status_code == 200
    payload = response.json()
    assert payload['agency_name']
    assert payload['contact_count'] >= 0
    assert payload['deal_count'] >= 0
