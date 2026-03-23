import json
from app.models import ParkingRecord, Whitelist, db

def test_process_entry_manual(auth_client, app):
    """Test manual entry (typing plate number)"""
    response = auth_client.post('/api/process_entry', data={'plate': '苏A11111'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'Welcome' in data['message']
    
    with app.app_context():
        record = ParkingRecord.query.filter_by(plate_number='苏A11111', status='parked').first()
        assert record is not None
        assert record.entry_image == ""

def test_process_entry_duplicate(auth_client):
    """Test preventing double entry"""
    auth_client.post('/api/process_entry', data={'plate': '苏A22222'})
    response = auth_client.post('/api/process_entry', data={'plate': '苏A22222'})
    data = json.loads(response.data)
    assert data['success'] == False
    assert 'already in garage' in data['message']

def test_process_exit_normal(auth_client, app):
    """Test normal exit with fee"""
    # Entry
    auth_client.post('/api/process_entry', data={'plate': '苏A33333'})
    
    # Manually backdate the entry time to simulate parking duration (e.g., 2 hours)
    from datetime import datetime, timedelta
    with app.app_context():
        record = ParkingRecord.query.filter_by(plate_number='苏A33333').first()
        record.entry_time = datetime.now() - timedelta(hours=2)
        db.session.commit()
    
    # Exit
    response = auth_client.post('/api/process_exit', data={'plate': '苏A33333'})
    data = json.loads(response.data)
    
    assert data['success'] == True
    assert data['fee'] > 0 # Should be charged (default free is 30 mins)
    
    with app.app_context():
        record = ParkingRecord.query.filter_by(plate_number='苏A33333').first()
        assert record.status == 'exited'
        assert record.exit_time is not None

def test_process_exit_whitelist(auth_client, app):
    """Test whitelist vehicle exit (should be free)"""
    # Add to whitelist using the CORRECT route /admin/whitelist
    auth_client.post('/admin/whitelist', data={'action': 'add_whitelist', 'plate': '苏A88888', 'owner': 'Boss'})
    
    # Entry
    auth_client.post('/api/process_entry', data={'plate': '苏A88888'})
    
    # Backdate
    from datetime import datetime, timedelta
    with app.app_context():
        record = ParkingRecord.query.filter_by(plate_number='苏A88888').first()
        record.entry_time = datetime.now() - timedelta(hours=5)
        db.session.commit()
        
    # Exit
    response = auth_client.post('/api/process_exit', data={'plate': '苏A88888'})
    data = json.loads(response.data)
    
    assert data['success'] == True
    assert data['fee'] == 0
