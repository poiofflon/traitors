import pytest


@pytest.fixture()
def client():
    from ..main import app
    return app.test_client()


@pytest.fixture()
def logged_on_client_factory():
    """ return a client that has logged and ready to play"""
    from ..main import app
    def client(player_name):
        flask_test_client = app.test_client()
        flask_test_client.post("/", data={"player_name": player_name})
        return flask_test_client
    return client


def test_lots_of_player_register(logged_on_client_factory, registered_players):
    for i in range(1000):
        logged_on_client_factory(str(i))
    assert len(registered_players) == 1000


def test_player_name_already_registered(logged_on_client_factory, client, registered_players):
    """ should reload the index / logon page and prompt for another name """
    player_name = "any_name"
    logged_on_client_factory(player_name)
    response = client.post("/", data={"player_name": player_name})
    assert response.status_code == 200
    assert len(registered_players) == 1


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

