from flask import Flask, render_template, request, redirect, session
import random
# import hashlib


app = Flask(__name__)
app.secret_key = 'some_secret'
app.static_folder = 'static'

players = []
traitors = []
votes = {}
game_started = False
admin = 'Offlon'
enable_multi_browser_logon = False

chat_messages = ['Feel free to type message']


# @app.before_request
# def before_request():
#     if enable_multi_browser_logon:
#         session_key = 'session_' + hashlib.sha256(request.remote_addr.encode('utf-8')).hexdigest()
#         app.config['SESSION_COOKIE_NAME'] = session_key


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['player_name'] = request.form['player_name']
        players.append(session['player_name'])
        return redirect('/wait')
    elif session.get('player_name') and session['player_name'] in players:
        return redirect('/wait')
    else:
        session.clear()
        return render_template('index.html', player_count=len(players))


@app.route('/join_game', methods=['GET', 'POST'])
def join_game():
    if request.method == 'POST':
        session['player_name'] = request.form['player_name']
        players.append(session['player_name'])
        return redirect('/wait')
    return render_template('join_game.html')


@app.route('/wait', methods=['GET', 'POST'])
def wait():
    global admin
    if session['player_name'] == admin:
        can_start_game = True
    else:
        can_start_game = False
    return render_template('wait.html', players=players, admin=admin, can_start_game=can_start_game)


@app.route('/start_game', methods=['POST'])
def start_game():
    global game_started, admin
    game_started = True
    admin = session['player_name']
    traitor_count = len(players) // 3
    traitors.extend(random.sample(players, traitor_count))
    for player in players:
        if player in traitors:
            votes[player] = []
        else:
            votes[player] = None
    return redirect('/game')


@app.route('/game', methods=['GET', 'POST'])
def game():
    global traitors, game_started, votes
    if not game_started:
        return redirect('/wait')
    if request.method == 'POST':
        vote = request.form['vote']
        voter = session['player_name']
        if vote in votes[voter]:
            return render_template('game.html', players=session['players'], traitors=traitors,
                                   message='You have already voted for this player.', votes=votes,
                                   chat_messages=chat_messages)
        votes[voter] = vote
        return redirect('/results')
    return render_template('game.html', players=players, traitors=traitors, votes=votes, chat_messages=chat_messages)


# @app.route('/game_over')
# def game_over():
#     global players, traitors, votes, game_started, admin
#     players = []
#     traitors = []
#     votes = {}
#     game_started = False
#     admin = None
#     session.clear()
#     return redirect('/')


# @app.teardown_appcontext
# def clear_game_cookies(exception=None):
#     if 'player_name' in session:
#         session.pop('player_name')
#     if 'game_started' in session:
#         session.pop('game_started')
#     if 'traitors' in session:
#         session.pop('traitors')
#     if 'votes' in session:
#         session.pop('votes')


@app.route('/results', methods=['GET'])
def results():
    global traitors, votes, game_started
    if not game_started:
        return redirect('/wait')
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
            return render_template('game_over.html', message='The Faithfuls have won!')
        else:
            return redirect('/game')
    return render_template('result.html', vote_count=vote_count, players=players)


@app.route('/chat', methods=['POST'])
def chat():
    sender = session['player_name']
    message = request.form['message']
    chat_messages.append({'sender': sender, 'message': message})
    return 'OK'


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
