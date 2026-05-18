import pytest

from app import create_app
from config import Config


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


@pytest.fixture
def app():
    application = create_app(TestConfig)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
