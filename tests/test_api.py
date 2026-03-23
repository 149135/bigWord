import json
from unittest.mock import patch

def test_stats_api(auth_client):
    response = auth_client.get('/api/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'traffic_dates' in data
    assert 'traffic_counts' in data

def test_history_data_api(auth_client):
    # Add some data
    auth_client.post('/api/process_entry', data={'plate': '苏A_HIST'})
    
    response = auth_client.get('/api/history_data')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['data']) >= 1
    assert data['data'][0]['plate'] == '苏A_HIST'

    # Test Filter
    response = auth_client.get('/api/history_data?plate=NOTFOUND')
    data = json.loads(response.data)
    assert len(data['data']) == 0

@patch('app.app.OpenAI')
def test_chat_api_no_key(mock_openai, auth_client):
    """Test chat without API Key configured"""
    response = auth_client.post('/api/chat', json={'message': 'hello'})
    data = json.loads(response.data)
    # Should fail or ask for key because we haven't set it in conftest
    assert '请先' in data['reply'] or 'Key' in data['reply']










