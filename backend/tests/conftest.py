import os

import pytest

# Must be set before app modules are imported since settings are loaded at import time
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/athlete_manager_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SAAS_ADMIN_EMAIL", "admin@test.com")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
