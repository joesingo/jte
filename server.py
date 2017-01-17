import os
import random
import json

from flask import Flask, render_template, request, redirect, abort, session

from matchmaking import Matchmaker, InvalidNameException, GameFullException


app = Flask(__name__)
app.secret_key = os.urandom(24)

MAX_GAME_ID = 100
matchmakers = {}

with open("map.json") as map_file:
    soton_map = json.load(map_file)


def check_game_exists(game_id):
    """Check if a game with the specifed ID exists"""
    if game_id not in matchmakers:
        abort(404)


@app.route("/create/")
def create_game():
    """Render the static page for a user to create a new game"""
    return render_template("create_game.html")


@app.route("/create/", methods=["POST"])
def create_game_post():
    """Handle a POST request from the create game page to actually create the
    game. Return a redirect to the join page for the newly created game"""
    while True:
        game_id = random.randint(1, MAX_GAME_ID)

        if game_id not in matchmakers:
            break

    try:
        players = int(request.form["no_of_players"])
    except ValueError, KeyError:
        abort(400)

    matchmakers[game_id] = Matchmaker(players, soton_map)
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

    try:
        name = request.form["username"]
    except KeyError:
        abort(400)

    name = name[0].upper() + name[1:].lower()

    try:
        matchmakers[game_id].add_player(name)

    except (InvalidNameException, GameFullException) as e:
        return e.message, 400

    session[game_id] = name

    return "", 200


@app.route("/join/<int:game_id>/status/")
def join_game_status(game_id):
    """Return the matchmaking status of the specified game as JSON"""
    check_game_exists(game_id)
    status = matchmakers[game_id].get_status()
    return json.dumps(status)


def get_username(game_id):
    """Get the username of the user for the specified game from the session
    object"""
    game_id = str(game_id)

    if game_id not in session:
        abort(403)

    return session[game_id]


def get_game(game_id):
    """Return the Game object for the specifed game"""
    check_game_exists(game_id)

    status = matchmakers[game_id].get_status()
    if not status["ready"]:
        abort(403)

    return matchmakers[game_id].game


@app.route("/play/<int:game_id>/")
def play_game(game_id):
    """Render the page to actually play the game"""
    game = get_game(game_id)
    username = get_username(game_id)

    return render_template("game.html", username=username,
                           cities=json.dumps(game.game_map["cities"]))


@app.route("/play/<int:game_id>/status/<float:timestamp>/")
def get_game_status(game_id, timestamp):
    """Return the game status as JSON. If the latest status for the game is
    not newer than the timestamp provided, return a 204"""
    game = get_game(game_id)
    username = get_username(game_id)
    status = game.get_status(username)

    if status["timestamp"] > timestamp:
        return json.dumps(status)

    else:
        return "", 204


@app.route("/play/<int:game_id>/action/", methods=["POST"])
def perform_action(game_id):
    """Perform an action in the specified game"""
    game = get_game(game_id)
    username = get_username(game_id)

    try:
        action_id = int(request.form["action_id"])
    except KeyError, ValueError:
        abort(400)

    game.perform_action(action_id, username)
    return "Success", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
