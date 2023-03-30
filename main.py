import random

from flask import Flask, redirect, render_template, request, session
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "some_secret"
app.static_folder = "static"
socketio = SocketIO(app, async_mode="threading")

players = []
vote_off = []
traitors = []
votes = {}
game_started = False
admin = "Offlon"
enable_multi_browser_logon = False
min_no_players = 3
end_game_option_label = "End game"
auto_send_name = "info"
traitor_result = None

# global
traitor_result = None

chat_messages = [{"sender": auto_send_name, "message": "Welcome to The Traitors!"}]


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
    """Wait page until game starts"""
    global admin
    if not session.get("player_name") or session["player_name"] not in players:
        return redirect("/")
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

    player = session["player_name"]

    if request.method == "GET":
        if player in traitors:
            message = "Traitor, all you need to do to win is work with your fellow Traitors to survive the eliminations"
        else:
            message = "Faithful, you need to work with your fellow Faithfuls to vote off the Traitors to win"

    if request.method == "POST":
        # player = session["player_name"]
        if player in votes:
            message = "You have already voted"
        elif player == traitor_result:
            players.remove(player)
            vote_off.append(player)
            message = f"{player} has been eliminated by the Traitors!"
            handle_message({"sender": auto_send_name, "message": message})
            socketio.emit("next-round")
            return redirect("/you-lost")
        else:
            vote = request.form["vote"]
            votes[player] = vote
            message = f"You voted for {vote}"
            if len(votes) == len(players):
                all_player_votes = list(votes.values())
                all_player_result = round_result(all_player_votes)

                traitor_votes = [vote for player, vote in votes.items() if player in traitors]
                traitor_result = round_result(traitor_votes)

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
                vote_off.append(all_player_result)
                votes.clear()
                handle_message({"sender": auto_send_name, "message": message})
                socketio.emit("next-round")

    if player in vote_off:
        return redirect("/you-lost")

    player_voting_option = players.copy() + [end_game_option_label]
    player_voting_option.remove(player)
    player_traitor_list = traitors if player in traitors else []

    return render_template(
        "game.html",
        voting_options=player_voting_option,
        traitors=player_traitor_list,
        message=message,
        votes=votes,
        chat_messages=chat_messages,
        auto_send_name=auto_send_name,
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
    global traitors, votes, game_started, players

    if not game_started:
        return redirect("/wait")

    if request.method == "POST":
        votes.clear()
        vote_off.clear()
        game_started = False
        players.clear()
        traitors.clear()
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
def handle_message(data):
    """receive messages data from client, store server side, push to all clients"""
    chat_messages.append(data)
    socketio.emit("message", data)


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, allow_unsafe_werkzeug=True)
