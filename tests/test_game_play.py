import pytest


@pytest.fixture()
def registered_players():
    from ..main import registered_players

    return registered_players


@pytest.fixture()
def logged_on_client_factory():
    """return a client that has logged and ready to play"""
    from ..main import app

    def client(player_name):
        flask_test_client = app.test_client()
        flask_test_client.post("/", data={"player_name": player_name})
        return flask_test_client

    return client


@pytest.fixture()
def game_clients_factory(logged_on_client_factory):
    def game_clients(no_of_players):
        clients = []
        for i in range(no_of_players):
            clients.append(logged_on_client_factory(i))
        return clients

    return game_clients


@pytest.fixture()
def players():
    from ..main import players

    return players


@pytest.fixture()
def votes():
    from ..main import votes

    return votes


def test_game_play(logged_on_client_factory, game_clients_factory, registered_players, players, votes):
    import random

    from ..main import admin

    # player with admin name can start date
    admin_client = logged_on_client_factory(admin)
    no_of_players = 20
    clients = game_clients_factory(no_of_players - 1)
    clients.append(admin_client)
    # minimum 1 player voted off per round
    # max_no_rounds = 20 / 1
    min_player_vote_off = 0
    max_player_vote_off = 0

    assert len(registered_players) == len(clients)

    # admin starts the game
    response = admin_client.post("/start_game", data={})
    assert response.status_code == 302
    assert response.headers["Location"] == "/game"

    # round 1, everyone chooses
    for client in clients:
        response = client.post("/game", data={"vote": str(random.choice(players))})
        assert response.status_code == 200
    min_player_vote_off += 1
    max_player_vote_off += 1
