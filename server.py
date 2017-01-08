import random
import json

from flask import Flask, render_template, request, redirect, abort, session

from matchmaking import Matchmaker, InvalidNameException, GameFullException


app = Flask(__name__)
app.secret_key = ("\x04\xbb5vU\xa1,\xc9\xa3\xa0\x1d\x86\xf7]=}\xe8\xa1\xba\x1b"
                  "\x18\x9c\x92n")

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
