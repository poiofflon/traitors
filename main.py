import random

from flask import Flask, redirect, render_template, request, session
from flask_socketio import SocketIO, join_room, leave_room

app = Flask(__name__)
app.secret_key = "some_secret"
app.static_folder = "static"
socketio = SocketIO(app, async_mode="threading")


registered_players = []
players = []
vote_off = []
traitors = []
votes = 0
game_started = False
admin = "Offlon"
enable_multi_browser_logon = False
min_no_players = 3
end_game_option_label = "End game"
auto_send_name = "info"
traitor_result = None
default_chat_room = "All"
rooms = {default_chat_room: 0}

# global
traitor_result = None

# {room_name: [{sender: message, etc}]}, room_name_2: etc
chat_messages = [(default_chat_room, {"sender": auto_send_name, "message": "Welcome to The Traitors!"})]


class Player:
    def __init__(self, player_name):
        self.player_name = str(player_name)
        self.sid = None
        self.previous_sid = None
        self.joined_rooms = [default_chat_room]
        # self.current_chat_room = default_chat_room
        self.is_admin = player_name == admin
        self.vote = None

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
        player_name = session.get("player_name")
        player = get_player_by_name(player_name)
        if player not in players:
            players.append(player)
        return redirect("/wait")

    if request.method == "POST":
        requested_player_name = request.form["player_name"]
        if requested_player_name in registered_players:
            message = f"Requested player name '{requested_player_name}' is taken. Please choose another name."
            return render_template("index.html", player_count=len(players), message=message)
        player = register_player(requested_player_name)
        players.append(player)
        return redirect("/wait")

    return render_template("index.html", player_count=len(players), message="Logon to play")


@app.route("/wait", methods=["GET", "POST"])
def wait():
    """Wait page until game starts"""
    global admin
    if not session.get("player_name") or session["player_name"] not in players:
        return redirect("/")
    message = None
    player = get_player_by_name(session["player_name"])
    if player.is_admin:
        can_start_game = True
        if len(players) < min_no_players:
            message = "Recommend waiting until the minimum number of players have joined"
    else:
        can_start_game = False
    return render_template("wait.html", players=players, admin=admin, can_start_game=can_start_game, message=message)


@app.route("/start_game", methods=["POST"])
def start_game():
    global game_started, admin
    game_started = True
    traitor_count = min(len(players) // 3, 1)
    traitors.extend(random.sample(players, traitor_count))
    socketio.emit("start-game")
    return redirect("/game")


@app.route("/game", methods=["GET", "POST"])
def game():
    global traitors, game_started, votes, vote_off, players, traitor_result
    message = ""
    if not game_started:
        return redirect("/wait")
    if not session.get("player_name"):
        return redirect("/")

    player = get_player_by_name(session["player_name"])

    if request.method == "GET":
        if player in traitors:
            message = "Traitor, all you need to do to win is work with your fellow Traitors to survive the eliminations"
        else:
            message = "Faithful, you need to work with your fellow Faithfuls to vote off the Traitors to win"

    if request.method == "POST":
        # player = session["player_name"]
        if player.vote:
            message = "You have already voted"
        # eliminate traitor voted player when they try and vote
        elif traitor_result and player == traitor_result:
            players.remove(player)
            vote_off.append(player)
            message = f"{player.player_name} has been eliminated by the Traitors!"
            handle_message({"sender": auto_send_name, "message": message})
            socketio.emit("next-round")
            return redirect("/you-lost")
        else:
            vote = request.form["vote"]
            player.vote = vote
            votes += 1
            message = f"You voted for {vote}"

            if votes == len(players):
                all_player_result = round_result([player.vote for player in players])
                traitor_votes = [player.vote for player in players if player in traitors]
                traitor_result = round_result(traitor_votes) if traitor_votes else None

                if all_player_result == end_game_option_label:
                    socketio.emit("end-game")
                    return redirect("/results")

                if all_player_result in traitors:
                    message = (
                        f"Congratulations Faithfuls, you have eliminated player '{all_player_result}' "
                        f"who was a Traitor"
                    )
                else:
                    message = f"Faithfuls, you voted off player '{all_player_result}' who was a Faithful"

                players.remove(all_player_result)
                vote_off.append(get_player_by_name(all_player_result))
                votes = 0
                for p in players:
                    p.vote = None
                handle_message({"sender": auto_send_name, "message": message})
                socketio.emit("next-round")

    if player in vote_off:
        return redirect("/you-lost")

    player_voting_option = [p.player_name for p in players if p is not player] + [end_game_option_label]
    player_traitor_list = [p.player_name for p in traitors if player in traitors]
    player_messages = [m[1] for m in chat_messages if m[0] in player.joined_rooms]

    return render_template(
        "game.html",
        voting_options=player_voting_option,
        traitors=player_traitor_list,
        message=message,
        chat_messages=player_messages,
        auto_send_name=auto_send_name,
        end_game_option_label=end_game_option_label,
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
    global traitors, votes, game_started, players, chat_messages

    if not game_started:
        return redirect("/wait")

    # play again
    if request.method == "POST":
        votes = 0
        vote_off.clear()
        game_started = False
        players.clear()
        traitors.clear()
        chat_messages = [(default_chat_room, {"sender": auto_send_name, "message": "Welcome to The Traitors!"})]
        for player in players:
            player.vote = None
        return redirect("/")

    if any([t in players for t in traitors]):
        return render_template("game_over.html", message="The Traitors have won!")

    return render_template("game_over.html", message="The Faithful have won!")


@app.route("/you-lost", methods=["GET"])
def you_lost():
    if not game_started:
        return redirect("/wait")

    return render_template("you_lost.html")


@socketio.on("message")
def handle_message(data, to_players=None):
    """receive messages data from client, store server side, push to all clients"""
    if to_players:
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

    player = get_player_by_name(session.get("player_name"))

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
    player = get_player_by_name(session.get("player_name"))
    for room_key in player.joined_rooms:
        leave_room(room_key, player.sid)
    player.previous_sid = player.sid
    player.sid = None


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, allow_unsafe_werkzeug=True)
