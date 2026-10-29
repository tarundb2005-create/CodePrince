from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

def credentials():
    return {"email": f"test-{uuid4().hex}@gmail.com", "password": "superSecret!A", "registration_number": "41142" + str(uuid4().int % 1_000_000).zfill(6), "full_name": "Test Student", "academic_year": "1st year", "section": "A", "department": "CSE"}

def test_auth_and_private_tests():
    with TestClient(app) as c:
        assert c.post('/api/auth/register', json=credentials()).status_code == 201
        q = c.get('/api/questions').json()['items'][0]
        detail = c.get('/api/questions/' + q['slug']).json()
        assert len(detail['tests']) == 5

def test_custom_question_and_progress():
    with TestClient(app) as c:
        assert c.post('/api/auth/register', json=credentials()).status_code == 201
        r = c.post('/api/questions', json={
            'title': 'My original problem', 'statement': 'Print hello',
            'tests': [{'input': '', 'expected_output': 'hello', 'is_hidden': True}],
        })
        assert r.status_code == 201
        assert c.get('/api/questions/' + r.json()['slug']).json()['tests'] == []

def test_student_profile_summary_is_safe_and_public():
    with TestClient(app) as client:
        assert client.post('/api/auth/register', json=credentials()).status_code == 201
        profile = client.get('/api/profile/me')
        assert profile.status_code == 200
        body = profile.json()
        assert body['username'].startswith('student-')
        assert 'email' not in body
        public = client.get('/api/u/' + body['username'])
        assert public.status_code == 200
        assert public.json()['username'] == body['username']
