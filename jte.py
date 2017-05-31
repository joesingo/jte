import sys
import json
import random
import time
import copy
from enum import Enum


class AuthenticationException(Exception):
    """There was a problem with authenticating the user"""


class InvalidMoveException(Exception):
    """The specifed move was not valid"""


class InvalidActionException(Exception):
    """The specifed action was not valid"""


class LinkTypes(Enum):
    """An enum to store the availble types of link between cities"""
    LAND = "land"
    SEA = "sea"
    AIR = "air"


class CircularQueue(object):
    """A queue that wraps around once the last item is reached"""

    def __init__(self, items):
        self.items = items
        self.current_index = 0

    def next(self):
        """Return the item at the current position in the queue and advance the
        pointer to the next position"""
        item = self.items[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.items)
        return item

    def previous(self):
        """Return the item at the current position in the queue and advance the
        pointer to the previous position"""
        item = self.items[self.current_index]
        self.current_index = (self.current_index - 1) % len(self.items)
        return item


class CardDeck(object):
    """An object to represent a deck of cards"""

    def __init__(self, cards):
        self.cards = cards
        random.shuffle(self.cards)

    def deal(self):
        """Deal a card and remove it from the deck"""
        return self.cards.pop()


class MessageLog(object):
    """An object to represent the message log for a game"""

    MAX_MESSAGES = 10

    def __init__(self):
        self.messages = [None] * MessageLog.MAX_MESSAGES
        self.ptr = 0  # Index of the position to insert the next message into

    def add(self, message_str):
        """Add a string to the log"""
        self.messages[self.ptr] = {
            "message": message_str,
            "timestamp": time.time()
        }
        self.ptr = (self.ptr + 1) % MessageLog.MAX_MESSAGES
        time.sleep(0.05)

    def get_list(self):
        """Return a list of the messages in the log in order (oldest first)"""
        l = self.messages[self.ptr:] + self.messages[:self.ptr]
        return [i for i in l if i is not None]


class Player(object):
    """A player in the game"""

    def __init__(self, name, starting_cities, home_city):
        self.name = name
        self.cities = starting_cities
        self.home_city = home_city
        self.cities_visited = []
        self.current_city = self.home_city


class Turn(object):
    """An object to represet a single turn taken by a player"""

    def __init__(self, starting_city):
        self.dice_roll = None  # The score rolled on the dice
        self.dice_points = None  # The number of dice points remaining
        self.flown = False
        self.cities = [starting_city]

    def roll_dice(self):
        self.dice_roll = random.randint(1, 6)
        self.dice_points = self.dice_roll


class Game(object):
    """An object to represent an actual game"""

    # The number of cards each player is dealt at the start of the game
    STARTING_CITIES = 9

    # Constants to represent the actions players are allowed to perform
    ROLL_DICE_ACTION = "roll_dice"
    TRAVEL_ACTION = "travel"
    WAIT_AT_PORT_ACTION = "wait_at_port"

    def __init__(self, game_map, player_names):
        """Create players and deal cards"""
        self.in_progress = True
        self.game_map = game_map

        # Build a list of sea ports
        self.sea_ports = []
        for link in self.game_map["links"]:
            if link["type"] == LinkTypes.SEA.value:
                self.sea_ports.append(link["cities"][0])
                self.sea_ports.append(link["cities"][1])
        self.sea_ports = set(self.sea_ports)

        self.players = []

        city_ids = list(range(len(self.game_map["cities"])))
        deck = CardDeck(city_ids)

        for name in player_names:
            cities = [deck.deal() for i in range(Game.STARTING_CITIES)]
            p = Player(name, cities, cities[0])
            self.players.append(p)

        self.player_queue = CircularQueue(self.players)
        self.current_player = None
        self.winner = None
        self.available_actions = None
        self.status = None
        self.message_log = MessageLog()
        self.next_player()
        self.update_status()

    def next_player(self):
        """Advance the current_player counter"""
        if self.current_player is not None:
            msg = "End of {}'s turn".format(self.current_player.name)
            self.message_log.add(msg)

        self.current_player = self.player_queue.next()
        self.current_turn = Turn(self.current_player.current_city)

        self.available_actions = self.get_available_actions()

        msg = "It's {}'s turn".format(self.current_player.name)
        self.message_log.add(msg)

    def get_available_actions(self):
        """Calculate and return the actions the current player is able to
        perform. Each action is a dictionary of the form:
            {"id": <integer ID>,
             "type": <one of the constants at the top of this class>
             ""}
        """
        if not self.in_progress:
            return []

        actions = []

        if self.current_turn.dice_points is None:
            actions.append({"type": Game.ROLL_DICE_ACTION})

        for link in self.get_links():
            actions.append({
                "type": Game.TRAVEL_ACTION, "link": link
            })

        # Allow waiting at port if player is at a sea port with dice points
        # remaining
        at_port = self.current_player.current_city in self.sea_ports
        if at_port and self.current_turn.dice_points is not None:
            actions.append({"type": Game.WAIT_AT_PORT_ACTION})

        # Add IDs to each action
        for i, action in enumerate(actions):
            action["id"] = i

        return actions

    def perform_action(self, action_id, username):
        """Perform an action as the player with the username provided"""

        if username != self.current_player.name:
            msg = "It is not {}'s turn".format(player.name)
            raise AuthenticationException(msg)

        action = None
        for i in self.available_actions:
            if i["id"] == action_id:
                action = i
                break

        if action is None:
            raise InvalidActionException("No action with that ID was found")

        if action["type"] == Game.ROLL_DICE_ACTION:
            self.roll_dice()

        elif action["type"] == Game.TRAVEL_ACTION:
            self.travel_to(action["link"])

        elif action["type"] == Game.WAIT_AT_PORT_ACTION:
            self.next_player()

        # Recalculate available actions
        self.available_actions = self.get_available_actions()

        # If no actions are available then end turn now and recalculate
        if not self.available_actions:
            self.message_log.add("{} got stuck!".format(self.current_player.name))
            self.next_player()
            self.available_actions = self.get_available_actions()

        self.update_status()

    def roll_dice(self):
        self.current_turn.roll_dice()

        # Give the player another go if they rolled a 6
        if self.current_turn.dice_points == 6:
            self.player_queue.previous()

        msg = "{} rolled a {}".format(self.current_player.name,
                                      self.current_turn.dice_points)
        self.message_log.add(msg)

    def get_links(self):
        """Return a list of links that the current player can travel along.
        Each link is a dictionary of the form:
            {"to_city": <destination city ID>,
            "type": <link type>,
            "cost": <link cost if type is "air">}
        """
        player = self.current_player
        available_links = []

        for link in self.game_map["links"]:
            if player.current_city in link["cities"]:

                # Skip if dice has not been rolled and this is not a sea link
                if (self.current_turn.dice_points is None and
                        link["type"] != LinkTypes.SEA.value):
                    continue

                # Skip if dice has been rolled and this is a sea link
                if (self.current_turn.dice_points is not None and
                        link["type"] == LinkTypes.SEA.value):
                    continue

                # Skip if already flown this turn and this is an air link
                if (link["type"] == LinkTypes.AIR.value and
                        self.current_turn.flown):
                    continue

                # Skip if not enough dice points are remaining
                if ("cost" in link and
                        link["cost"] > self.current_turn.dice_points):
                    continue

                # Work out the 'to' city - the city in the link that is not the
                # player's current city
                if link["cities"][0] == player.current_city:
                    to_city = link["cities"][1]
                else:
                    to_city = link["cities"][0]

                # Skip if the to city has already been visited this turn
                if to_city in self.current_turn.cities:
                    continue

                link["to_city"] = to_city

                # If reached here then the link must be okay
                available_links.append(link)

        return available_links

    def travel_to(self, link):
        """Move the current player along the link provided"""

        # Check this move is valid
        if link not in self.get_links():
            raise InvalidMoveException("That is not a valid move")

        current_city_str = self.get_city_name(self.current_player.current_city)
        to_city_str = self.get_city_name(link["to_city"])
        msg = "{}: {} -> {}".format(self.current_player.name, current_city_str,
                                    to_city_str)
        self.message_log.add(msg)

        self.current_player.current_city = link["to_city"]
        self.current_turn.cities.append(link["to_city"])

        end_turn = False

        if link["to_city"] in self.current_player.cities:
            p = self.current_player

            # Work out whether the player has visited all cities except their
            # home city
            visited_all = (list(set(p.cities) - set(p.cities_visited))
                           == [p.home_city])

            already_visited = link["to_city"] in self.current_player.cities_visited

            if not already_visited and (link["to_city"] != p.home_city or visited_all):

                msg = "{} got a city".format(self.current_player.name)
                self.message_log.add(msg)

                self.current_player.cities_visited.append(link["to_city"])

                # End turn when reaching a city - strictly this is not part of
                # the rules of the game but it's how me and Ivan play it...
                end_turn = True

        self.win_check()

        if self.in_progress:
            if link["type"] == LinkTypes.AIR.value:
                self.current_turn.dice_points -= int(link["cost"])
                self.current_turn.flown = True

            elif link["type"] == LinkTypes.LAND.value:
                self.current_turn.dice_points -= 1

            elif link["type"] == LinkTypes.SEA.value:
                self.next_player()

            # End turn now if all dice points are used up
            if self.current_turn.dice_points == 0:
                self.next_player()

        if end_turn:
            self.next_player()

    def get_city_name(self, city_id):
        return self.game_map["cities"][city_id]["name"]

    def win_check(self):
        for player in self.players:
            if set(player.cities_visited) == set(player.cities):
                self.end_game(player)

    def end_game(self, winner):
        self.in_progress = False
        self.message_log.add("{} has won!".format(winner.name))
        self.winner = winner.name

    def get_status(self, username):
        """Return the status as set in update_status(). username is the name of the user
        retreiving the status"""

        # Copy the status so some things can be removed
        status = copy.deepcopy(self.status)

        # Put this player's cards in top level in the status dict
        for p in status["players"]:
            if p["name"] == username:
                status["cards"] = p["cards"]

            del p["cards"]

        # Only show actions if it is that player's turn
        if username != self.current_player.name:
            del status["actions"]

        return status


    def update_status(self):
        """Set the current status to a  dictionary containing all information a
        client will need to provide and interface for the game.
        """
        self.status = {
            "in_progress": self.in_progress,
            "winner": None if self.in_progress else self.winner,
            "current_player": self.current_player.name,
            "dice_roll": self.current_turn.dice_roll,
            "dice_points": self.current_turn.dice_points,
            "players": [],
            "message_log": self.message_log.get_list(),
            "actions": self.available_actions
        }

        for p in self.players:
            progress_str = "{}/{}".format(len(p.cities_visited), len(p.cities))
            player_status = {
                "name": p.name,
                "progress": progress_str,
                "current_city": p.current_city,
                "cards": []
            }

            for city in p.cities:
                player_status["cards"].append({
                    "id": city,
                    "visited": (city in p.cities_visited)
                })

            self.status["players"].append(player_status)

        self.status["timestamp"] = time.time()


if __name__ == "__main__":

    with open("map.json") as map_file:
        soton_map = json.load(map_file)

    players = ["John", "Yoko"]
    game = Game(soton_map, players)

    for i, name in enumerate(players):
        city_names = [game.get_city_name(c) for c in game.players[i].cities]
        print("{} has cards:\n{}".format(name, ", ".join(city_names)))

    print("")

    while True:
        username = game.current_player.name
        s = game.get_status(username)

        for i, p in enumerate(s["players"]):
            if p["name"] == s["current_player"]:
                break

        city_id = s["players"][i]["current_city"]
        city = game.get_city_name(city_id)
        message = "{}'s turn: {}".format(s["current_player"], city)

        if s["dice_points"]:
            message += ": {}/{}".format(s["dice_points"], s["dice_roll"])

        print(message)
        print("Available actions are:")

        for action in game.available_actions:
            if action["type"] == Game.ROLL_DICE_ACTION:
                desc = "Roll dice"

            elif action["type"] == Game.TRAVEL_ACTION:
                city = game.get_city_name(action["link"]["to_city"])
                desc = "Travel to {} by {}".format(city,
                                                   action["link"]["type"])

            elif action["type"] == Game.WAIT_AT_PORT_ACTION:
                desc = "Wait at port"

            print("{}. {}".format(action["id"], desc))

        choice = int(input())
        game.perform_action(choice, username)
