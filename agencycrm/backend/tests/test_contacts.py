from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_contacts_endpoint():
    response = client.get('/api/contacts')
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]['name']


def test_contact_crud_round_trip():
    create_payload = {
        'name': 'Ava Brooks',
        'company': 'Northwind Labs',
        'email': 'ava@example.com',
        'status': 'New',
        'phone': '5551234',
        'website': 'https://northwind.com',
        'social_links': ['https://linkedin.com/in/ava'],
    }
    create_response = client.post('/api/contacts', json=create_payload)
    assert create_response.status_code == 200
    created = create_response.json()
    contact_id = created['id']

    update_response = client.put(
        f'/api/contacts/{contact_id}',
        json={
            **create_payload,
            'company': 'Northwind Studio',
            'status': 'Qualified',
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated['company'] == 'Northwind Studio'
    assert updated['status'] == 'Qualified'

    delete_response = client.delete(f'/api/contacts/{contact_id}')
    assert delete_response.status_code == 200


def test_lead_generation_endpoint():
    response = client.post(
        '/api/leads/generate',
        json={'api_key': 'demo-key', 'niche': 'software agency', 'city': 'Austin', 'state': 'TX'},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['generated'] >= 0
    assert payload['leads']
    assert payload['leads'][0]['company_name']
