import pytest

from .main import app


@pytest.fixture()
def client():
    return app.test_client()


def test_request_example(client):
    response = client.get("/")
    assert response.status_code == 200
