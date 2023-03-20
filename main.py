import random

from flask import Flask, redirect, render_template, request, session
from flask_socketio import SocketIO


app = Flask(__name__)
app.secret_key = "some_secret"
app.static_folder = "static"
socketio = SocketIO(app, async_mode="threading")


players = []
traitors = []
votes = {}
game_started = False
admin = "Offlon"
enable_multi_browser_logon = False
min_no_players = 3
end_game_option_label = "End game"
traitor_result = None

chat_messages = [{"sender": "Admin", "message": "Welcome to The Traitors!"}]


@app.route("/", methods=["GET", "POST"])
def index():
    if session.get("player_name"):
        if session["player_name"] not in players:
            players.append(session["player_name"])
        return redirect("/wait")

    if request.method == "POST":
        requested_player_name = request.form["player_name"]
        if requested_player_name in players:
            message = f"Requested player name '{requested_player_name}' is taken. Please choose another name."
            return render_template("index.html", player_count=len(players), message=message)
        session["player_name"] = request.form["player_name"]
        players.append(session["player_name"])
        return redirect("/wait")

    return render_template("index.html", player_count=len(players), message='Logon to play')


@app.route("/join_game", methods=["GET", "POST"])
def join_game():
    if request.method == "POST":
        session["player_name"] = request.form["player_name"]
        players.append(session["player_name"])
        return redirect("/wait")
    return render_template("join_game.html")


@app.route("/wait", methods=["GET", "POST"])
def wait():
    global admin
    if session["player_name"] == admin:
        can_start_game = True
    else:
        can_start_game = False
    return render_template("wait.html", players=players, admin=admin, can_start_game=can_start_game)


@app.route("/start_game", methods=["POST"])
def start_game():
    global game_started, admin
    game_started = True
    admin = session["player_name"]
    traitor_count = len(players) // 3
    traitors.extend(random.sample(players, traitor_count))
    return redirect("/game")


@app.route("/game", methods=["GET", "POST"])
def game():
    global traitors, game_started, votes
    message = ""
    if not game_started:
        return redirect("/wait")
    if request.method == "POST":
        voter = session["player_name"]
        if voter in votes:
            message = "You have already voted"
        else:
            vote = request.form["vote"]
            votes[voter] = vote
            message = f"You voted for {vote}"
    if len(votes) == len(players):
        return redirect("/round_result")

    return render_template("game.html", voting_options=players + [end_game_option_label], traitors=traitors,
                           message=message, votes=votes, chat_messages=chat_messages)


@app.route("/results", methods=["GET"])
def results():
    global traitors, votes, game_started
    if not game_started:
        return redirect("/wait")
    vote_count = {}
    for voter, vote in votes.items():
        if voter in traitors:
            continue
        if vote_count.get(vote):
            vote_count[vote] += 1
        else:
            vote_count[vote] = 1
    if len(vote_count) == 1:
        winner = list(vote_count.keys())[0]
        traitors = [t for t in traitors if t != winner]
        votes = {p: [] if p in traitors else None for p in players}
        if len(traitors) == 0:
            game_started = False
            return render_template("game_over.html", message="The Faithfuls have won!")
        else:
            return redirect("/game")
    return render_template("result.html", vote_count=vote_count, players=players)


@socketio.on("message")
def handle_message(data):
    sender = data["sender"]
    message = data["message"]
    chat_messages.append({"sender": sender, "message": message})
    socketio.emit("message", {"sender": sender, "message": message}, to=None)


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000)
