import random

from flask import Flask, redirect, render_template, request, session
from flask_socketio import SocketIO, join_room, leave_room

app = Flask(__name__)
app.secret_key = "some_secret"
app.static_folder = "static"
socketio = SocketIO(app, async_mode="threading")


registered_players = []
min_no_players = 3
max_no_games = 10
end_game_option_label = "End game"
auto_send_name = "info"
default_chat_room = "All"
rooms = {default_chat_room: 0}

games = [None] * 10


def get_available_game_id():
    for i, g in enumerate(games):
        if not g:
            return i
    return -1


class Game:
    def __init__(self, id, admin: "Player"):
        self.players = [admin]
        self.vote_off = []
        self.traitors = []
        self.votes = 0
        self.game_started = False
        self.admin = admin
        self.traitor_result = None
        self.game_id = id
        self.ended = False

    @property
    def game_name(self):
        return f"{self.admin.player_name}'s game"


# {room_name: [{sender: message, etc}]}, room_name_2: etc
chat_messages = [(default_chat_room, {"sender": auto_send_name, "message": "Welcome to The Traitors!"})]


class Player:
    def __init__(self, player_name):
        self.player_name = str(player_name)
        self.sid = None
        self.previous_sid = None
        self.joined_rooms = [default_chat_room]
        self.is_admin = False
        self.vote = None
        self.game = None

    def __repr__(self):
        return f"Player({self.player_name})"

    def __str__(self):
        return self.player_name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.player_name == other
        return self.player_name == other.player_name


def get_player_by_name(player_name):
    if player_name in registered_players:
        return registered_players[registered_players.index(player_name)]
    else:
        return register_player(player_name)


def register_player(player_name):
    player = Player(player_name)
    registered_players.append(player)
    session["player_name"] = player_name
    return player


@app.route("/", methods=["GET", "POST"])
def index():
    if session.get("player_name"):
        get_player_by_name(session["player_name"])
        return redirect("/join_game")

    if request.method == "POST":
        requested_player_name = request.form["player_name"]
        if requested_player_name in registered_players:
            message = f"Requested player name '{requested_player_name}' is taken. Please choose another name."
            return render_template("index.html", player_count=len(game.players), message=message)
        register_player(requested_player_name)
        return redirect("/join_game")

    return render_template("index.html", player_count=len(registered_players), message="Logon to play")


@app.route("/join_game", methods=["GET", "POST"])
def join_game():
    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])
    id = get_available_game_id()

    if player.game:
        return redirect("/wait")

    if request.method == "POST":
        if "host_game" in request.form:
            if id > -1:
                player.is_admin = True
                game = Game(id, player)
                games[id] = game
                player.game = game
                return redirect("/wait")
            else:
                return redirect("/join_game")
        if "join_game" in request.form:
            game_id = request.form["join_game"]
            game = games[int(game_id)]
            player.game = game
            game.players.append(player)
            return redirect("/wait")

    message = ""
    available_games = [{"id": g.game_id, "name": g.game_name} for g in games if g and not g.ended and not g.game_started]
    return render_template(
        "join_game.html", player_joined_game=bool(player.game), available_games=available_games, message=message
    )


@app.route("/wait", methods=["GET", "POST"])
def wait():
    """Wait page until game starts"""
    message = None
    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])
    if not player.game:
        return redirect("/join_game")
    game = player.game

    if player.is_admin:
        can_start_game = True
        if len(game.players) < min_no_players:
            message = "Recommend waiting until the minimum number of players have joined"
    else:
        can_start_game = False

    return render_template("wait.html", players=game.players, can_start_game=can_start_game, message=message)


@app.route("/start_game", methods=["POST"])
def start_game():
    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])
    if not player.game:
        return redirect("/join_game")
    game = player.game
    if game.game_started:
        return redirect("/game")

    game.game_started = True
    game.traitor_count = min(len(game.players) // 3, 1)
    game.traitors.extend(random.sample(game.players, game.traitor_count))
    socketio.emit("start-game")
    return redirect("/game")


@app.route("/game", methods=["GET", "POST"])
def game():
    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])
    if not player.game:
        return redirect("/join_game")
    game = player.game

    if not game.game_started:
        return redirect("/wait")

    if request.method == "GET":
        if player in game.traitors:
            message = "Traitor, all you need to do to win is work with your fellow Traitors to survive the eliminations"
        else:
            message = "Faithful, you need to work with your fellow Faithfuls to vote off the Traitors to win"

    if request.method == "POST":
        # player = session["player_name"]
        if player.vote:
            message = "You have already voted"
        # eliminate traitor voted player when they try and vote
        elif game.traitor_result and player == game.traitor_result:
            game.players.remove(player)
            game.vote_off.append(player)
            message = f"{player.player_name} has been eliminated by the Traitors!"
            handle_message({"sender": auto_send_name, "message": message})
            socketio.emit("next-round")
            return redirect("/you-lost")
        else:
            vote = request.form["vote"]
            player.vote = vote
            game.votes += 1
            message = f"You voted for {vote}"

            if game.votes == len(game.players):
                all_player_result = round_result([player.vote for player in game.players])
                traitor_votes = [player.vote for player in game.players if player in game.traitors]
                game.traitor_result = round_result(traitor_votes) if traitor_votes else None

                if all_player_result == end_game_option_label:
                    socketio.emit("end-game")
                    return redirect("/results")

                if all_player_result in game.traitors:
                    message = (
                        f"Congratulations Faithfuls, you have eliminated player '{all_player_result}' "
                        f"who was a Traitor"
                    )
                else:
                    message = f"Faithfuls, you voted off player '{all_player_result}' who was a Faithful"

                game.players.remove(all_player_result)
                game.vote_off.append(get_player_by_name(all_player_result))
                game.votes = 0
                for p in game.players:
                    p.vote = None

                handle_message({"sender": auto_send_name, "message": message})
                socketio.emit("next-round")

    if player in game.vote_off:
        return redirect("/you-lost")

    player_voting_option = [p.player_name for p in game.players if p is not player] + [end_game_option_label]
    player_traitor_list = [p.player_name for p in game.traitors if player in game.traitors]
    player_messages = [m[1] for m in chat_messages if m[0] in player.joined_rooms]

    return render_template(
        "game.html",
        voting_options=player_voting_option,
        traitors=player_traitor_list,
        message=message,
        chat_messages=player_messages,
        auto_send_name=auto_send_name,
        end_game_option_label=end_game_option_label,
        player_vote=player.vote,
    )


# @socketio.on("next-round")
# def next_round():
#     redirect("/game")


def max_votes(vote_list):
    vote_set = set(vote_list)
    max_count = max([vote_list.count(v) for v in vote_set])
    return [v for v in vote_set if vote_list.count(v) == max_count]


def round_result(vote_list):
    # who got the most votes
    max_vote_list = max_votes(vote_list)

    # resolve tied result
    if len(max_vote_list) > 1:
        if end_game_option_label in max_vote_list:
            result = end_game_option_label
        else:
            # pick at random
            result = random.sample(max_vote_list, 1)[0]
    else:
        result = max_vote_list[0]

    return result


@app.route("/results", methods=["GET", "POST"])
def results():
    global chat_messages

    if not session.get("player_name"):
        return redirect("/")

    player = get_player_by_name(session["player_name"])
    game = player.game

    if not game or not game.game_started:
        return redirect("/wait")

    # final result
    if any([t in games.players for t in game.traitors]):
        message = "The Traitors have won!"
    else:
        message = "The Faithful have won!"

    # player play again
    if request.method == "POST":
        # for player in game.players:
        player.vote = None
        player.admin = None
        player.game = None
        return redirect("/")

    # game.votes = 0
    # games.vote_off.clear()
    # game.game_started = False
    # games.players.clear()
    # games.traitors.clear()
    # chat_messages = [(default_chat_room, {"sender": auto_send_name, "message": "Welcome to The Traitors!"})]
    # for player in games.players:
    # player.vote = None
    # player.admin = None
    # player.game = None

    game.ended = True
    games[game.game_id] = None

    return render_template("game_over.html", message=message)


@app.route("/you-lost", methods=["GET"])
def you_lost():
    global chat_messages

    if not session.get("player_name"):
        return redirect("/")

    player = get_player_by_name(session["player_name"])
    game = player.game

    if not game.game_started:
        return redirect("/wait")

    return render_template("you_lost.html")


@socketio.on("message")
def handle_message(data, to_players=None):
    """receive messages data from client, store server side, push to all clients"""
    if to_players:
        data["sender"] = data["sender"] + " (" + ", ".join(to_players) + ")"
        # include current player name in private chat rooms
        to_players.append(session.get("player_name"))
        to_players.sort()
        room_key = tuple(to_players)
    else:
        room_key = default_chat_room

    if room_key == default_chat_room:
        chat_messages.append((room_key, data))
        socketio.emit("message", data)
    else:
        if room_key in rooms:
            room_name = rooms[room_key]
        if room_key not in rooms:
            room_name = str(len(rooms) + 1)
            rooms[room_key] = room_name
            for player_name in to_players:
                player = get_player_by_name(player_name)
                join_room(room=room_name, sid=player.sid)
                player.joined_rooms.append(room_key)
        chat_messages.append((room_key, data))
        socketio.emit("message", data, to=room_name)


@socketio.event
def connect(**kwargs):
    if "player_name" not in session:
        return redirect("/")

    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])

    if player.sid != request.sid:
        player.previous_sid = player.sid
        player.sid = request.sid

    for room_key in player.joined_rooms:
        room = rooms[room_key]
        join_room(room, player.sid)
        if player.previous_sid:
            leave_room(room, player.previous_sid)


@socketio.event
def disconnect(**kwargs):
    if not session.get("player_name") or session["player_name"] not in registered_players:
        return redirect("/")
    player = get_player_by_name(session["player_name"])
    for room_key in player.joined_rooms:
        leave_room(room_key, player.sid)
    player.previous_sid = player.sid
    player.sid = None


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, allow_unsafe_werkzeug=True)
