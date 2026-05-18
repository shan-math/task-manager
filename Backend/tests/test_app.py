def test_index(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"Task Management System" in rv.data


def test_login_page(client):
    rv = client.get("/login")
    assert rv.status_code == 200
    assert b"Login" in rv.data


def test_signup_page(client):
    rv = client.get("/signup")
    assert rv.status_code == 200
    assert b"user" in rv.data.lower()


def test_admin_dashboard_requires_auth(client):
    rv = client.get("/admin/dashboard", follow_redirects=False)
    assert rv.status_code == 302


def test_api_unauthorized(client):
    rv = client.get("/api/tasks")
    assert rv.status_code == 401
