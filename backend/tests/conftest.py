import os
import tempfile
from pathlib import Path
from uuid import uuid4

# Isolate the test suite from the configured database (backend/.env may point at Neon).
_test_database = Path(tempfile.gettempdir()) / f"codeprince-tests-{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database.as_posix()}"
os.environ["SESSION_COOKIE_NAME"] = "codeprince_test_session"
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "admin-test-password")


def pytest_sessionfinish(session, exitstatus):
    try:
        from app.main import engine

        engine.dispose()
    except Exception:
        pass
    try:
        _test_database.unlink(missing_ok=True)
    except PermissionError:
        pass
