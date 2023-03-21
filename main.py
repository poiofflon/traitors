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

# global
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

    return render_template("index.html", player_count=len(players), message="Logon to play")


@app.route("/wait", methods=["GET", "POST"])
def wait():
    """ Wait page until game starts """
    global admin
    message = None
    if session["player_name"] == admin:
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


def max_votes(vote_list):
    vote_set = set(vote_list)
    max_count = max([vote_list.count(v) for v in vote_set])
    return [v for v in vote_set if vote_list.count(v) == max_count]


@app.route("/round_result", methods=["GET"])
def round_result():
    global traitor_result, votes

    all_player_votes = list(votes.values())
    traitor_votes = [vote for voter, vote in votes.items() if voter in traitors]

    # resolve tied results
    all_player_result = max_votes(all_player_votes)

    # end the game when a majority of players vote to end
    if end_game_option_label in all_player_result:
        return redirect("/results")

    # resolve tied result
    all_player_result = random.sample(max_votes(all_player_votes), 1)[0]
    players.remove(all_player_result)
    player_result_is_traitor = all_player_result in traitors

    if all_player_result == session["player_name"]:
        return redirect("/you_lost")

    # push update to notify player that they are out the game
    # push notification to chat to confirm outcome of public vote

    traitor_result = random.sample(max_votes(traitor_votes), 1)

    if player_result_is_traitor:
        message = f"Congratulations Faithfuls, you have eliminated player '{all_player_result}' who was a Traitor"
    else:
        message = f"Faithfuls, you voted off player '{all_player_result}' who was a Faithful"

    votes.clear()

    return render_template(
        "game.html", voting_options=players + [end_game_option_label], traitors=traitors, message=message, votes=votes
    )


@app.route("/results", methods=["GET", "POST"])
def results():
    global traitors, votes, game_started, players
    if not game_started:
        return redirect("/wait")

    if request.method == "POST":
        votes.clear()
        game_started = False
        players.clear()
        traitors.clear()
        return redirect("/")

    if any([t in players for t in traitors]):
        return render_template("game_over.html", message="The Traitors have won!")

    return render_template("game_over.html", message="The Faithful have won!")


@app.route("/you_lost", methods=["GET"])
def you_lost():
    return "You lost, sorry :-("


@socketio.on("message")
def handle_message(data):
    """ receive messages data from client, store server side, push to all clients """
    chat_messages.append(data)
    socketio.emit("message", data)


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, allow_unsafe_werkzeug=True)
