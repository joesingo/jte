import os
import random
import json
import time
import pickle

from flask import Flask, render_template, request, redirect, abort, session

from matchmaking import Matchmaker, InvalidNameException, GameFullException


app = Flask(__name__)
app.secret_key = os.urandom(24)

MAX_GAME_ID = 100
GAME_FILES_DIRECTORY = "./games"

if not os.path.isdir(GAME_FILES_DIRECTORY):
    os.mkdir(GAME_FILES_DIRECTORY)

with open("europe-map.json") as map_file:
    europe_map = json.load(map_file)


def check_game_exists(game_id):
    """Check if a game with the specifed ID exists"""
    if str(game_id) not in os.listdir(GAME_FILES_DIRECTORY):
        abort(404)


@app.route("/")
def home_redirect():
    """Redirect home page to create game page"""
    return redirect("/create/")


@app.route("/create/")
def create_game():
    """Render the static page for a user to create a new game"""
    return render_template("create_game.html")


@app.route("/create/", methods=["POST"])
def create_game_post():
    """Handle a POST request from the create game page to actually create the
    game. Return a redirect to the join page for the newly created game"""

    if len(os.listdir(GAME_FILES_DIRECTORY)) >= MAX_GAME_ID:
        return "Too many games in progress", 503

    while True:
        game_id = random.randint(1, MAX_GAME_ID)

        if str(game_id) not in os.listdir(GAME_FILES_DIRECTORY):
            break

    try:
        players = int(request.form["no_of_players"])
    except (ValueError, KeyError):
        return "Must provide integer value 'no_of_players'", 400

    m = Matchmaker(players, europe_map)
    save_matchmaker(game_id, m)

    return redirect("/join/{}/".format(game_id))


@app.route("/join/<int:game_id>/")
def join_game(game_id):
    """Render the page for a user to join a game"""
    check_game_exists(game_id)
    return render_template("join_game.html")


@app.route("/join/<int:game_id>/", methods=["POST"])
def joing_game_post(game_id):
    """Handle a POST request from the join page to actually add the user to the
    game"""
    check_game_exists(game_id)
    if str(game_id) in session:
        return "Cannot join game multiple times", 400

    try:
        name = request.form["username"]
    except KeyError:
        return "Must provide 'username'", 400

    if not name:
        return "Username cannot be blank", 400

    name = name[0].upper() + name[1:].lower()

    m = get_matchmaker(game_id)

    try:
        m.add_player(name)
    except (InvalidNameException, GameFullException) as e:
        return str(e), 400

    save_matchmaker(game_id, m)
    session[game_id] = name

    return "", 200


@app.route("/join/<int:game_id>/status/")
def join_game_status(game_id):
    """Return the matchmaking status of the specified game as JSON"""
    check_game_exists(game_id)
    m = get_matchmaker(game_id)
    status = m.get_status()
    return json.dumps(status)


def get_username(game_id):
    """Get the username of the user for the specified game from the session
    object"""
    game_id = str(game_id)

    if game_id not in session:
        abort(403)

    return session[game_id]

def get_matchmaker(game_id):
    """Unpickle and return the Matchmaker object for the specifed game"""
    filename = os.path.join(GAME_FILES_DIRECTORY, str(game_id))
    with open(filename, "rb") as f:
        m = pickle.load(f)

    return m


def save_matchmaker(game_id, matchmaker):
    """Pickle the Matchmaker object provided to a file"""
    filename = os.path.join(GAME_FILES_DIRECTORY, str(game_id))
    with open(filename, "wb") as f:
        pickle.dump(matchmaker, f)


@app.route("/play/<int:game_id>/")
def play_game(game_id):
    """Render the page to actually play the game"""
    check_game_exists(game_id)
    m = get_matchmaker(game_id)

    if not m.get_status()["ready"]:
        abort(403)

    username = get_username(game_id)

    return render_template("game.html", username=username,
                           cities=json.dumps(m.game.game_map["cities"]),
                           airports=json.dumps(m.game.game_map["airports"]),
                           random_num=time.time())


@app.route("/play/<int:game_id>/status/<float:timestamp>/")
def get_game_status(game_id, timestamp):
    """Return the game status as JSON. If the latest status for the game is
    not newer than the timestamp provided, return a 204"""
    check_game_exists(game_id)
    m = get_matchmaker(game_id)

    if not m.get_status()["ready"]:
        abort(403)

    username = get_username(game_id)
    status = m.game.get_status(username)

    if status["timestamp"] > timestamp:
        return json.dumps(status)

    else:
        return "", 204


@app.route("/play/<int:game_id>/action/", methods=["POST"])
def perform_action(game_id):
    """Perform an action in the specified game"""
    check_game_exists(game_id)
    m = get_matchmaker(game_id)

    if not m.get_status()["ready"]:
        abort(403)

    username = get_username(game_id)

    try:
        action_id = int(request.form["action_id"])
    except (KeyError, ValueError):
        return "Must provide integer value 'action_id'", 400

    m.game.perform_action(action_id, username)
    save_matchmaker(game_id, m)
    return "Success", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
