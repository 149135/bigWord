def test_login_logout(client):
    # Test valid login
    response = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    html = response.data.decode('utf-8')
    assert 'Log Out' in html or '退出登录' in html
    
    # Test invalid login
    response = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid username or password' in response.data

    # Test logout
    response = client.get('/logout', follow_redirects=True)
    html = response.data.decode('utf-8')
    assert 'Login' in html or '登录' in html

def test_admin_access(client):
    # Try accessing protected route without login
    response = client.get('/', follow_redirects=True)
    html = response.data.decode('utf-8')
    assert 'Login' in html or '登录' in html










