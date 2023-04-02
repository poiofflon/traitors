import pytest


@pytest.fixture()
def client():
    from ..main import app
    return app.test_client()


@pytest.fixture()
def random_username():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters, k=5))


@pytest.fixture()
def registered_players():
    from ..main import registered_players
    return registered_players


def test_logon(client, random_username, registered_players):
    response = client.post("/", data={
        "player_name": random_username
    })
    # test redirects user to wait page after entering username
    assert response.status_code == 302
    assert response.headers["Location"] == "/wait"
    # test user registered to play
    assert random_username in registered_players

