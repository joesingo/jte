import sys
import json
import random
from enum import Enum

class InvalidMoveException(Exception):
    """The specifed move was not valid"""

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
        self.dice_points = None
        self.flown = False
        self.cities = [starting_city]

    def roll_dice(self):
        self.dice_points = random.randint(1, 6)


class Game(object):
    """An object to represent an actual game"""

    # The number of cards each player is dealt at the start of the game
    STARTING_CITIES = 3

    def __init__(self, game_map, player_names):
        """Create players and deal cards"""
        self.game_map = game_map
        self.players = []

        city_ids = list(range(len(self.game_map["cities"])))
        deck = CardDeck(city_ids)

        for name in player_names:
            cities = [deck.deal() for i in range(Game.STARTING_CITIES)]
            p = Player(name, cities, cities[0])
            self.players.append(p)

        self.player_queue = CircularQueue(self.players)
        self.current_player = None
        self.next_player()

    def next_player(self):
        """Advance the current_player counter"""
        if self.current_player is not None:
            print("End of {}'s turn".format(self.current_player.name))

        self.current_player = self.player_queue.next()
        self.current_turn = Turn(self.current_player.current_city)

    def roll_dice(self):
        self.current_turn.roll_dice()

        # Give the player another go if they rolled a 6
        if self.current_turn.dice_points == 6:
            self.player_queue.previous()

    def get_links(self, player_id):
        """Return a list of links that the player with the specified ID can
        travel along. Each link is a dictionary of the form:
        {"cities": [<city 1 ID>, <city2 ID>],
         "type": <link type>,
         "cost": <link cost if type is "air">}
        """
        player = self.players[player_id]
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
                if self.current_turn.flown and link["type"] == LinkTypes.AIR.value:
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

                # If reached here then the link must be okay
                available_links.append(link)

        # If the player cannot move anywhere then end the turn here
        if not available_links:
            pass
            # self.next_player()

        return available_links

    def travel_to(self, player_id, link, from_city, wait_at_port=False):
        """Make the specified player travel along the link provided"""

        # Check this move is valid
        current_player_index = self.players.index(self.current_player)
        if player_id != current_player_index:
            raise InvalidMoveException("It is not that player's turn")

        if link not in self.get_links(player_id):
            raise InvalidMoveException("That is not a valid move")

        if from_city not in link["cities"]:
            raise InvalidMoveException("The from city is not part of the link "
                                       "provided")

        # Work out the to_city
        if link["cities"][0] == from_city:
            to_city = link["cities"][1]
        else:
            to_city = link["cities"][0]

        player = self.players[player_id]
        player.current_city = to_city
        self.current_turn.cities.append(to_city)

        if to_city in player.cities:
            print("Got a city")
            player.cities_visited.append(to_city)

        self.win_check()

        if link["type"] == LinkTypes.AIR.value:
            self.current_turn.dice_points -= int(link["cost"])
            self.current_turn.flown = True

        elif link["type"] == LinkTypes.LAND.value:
            self.current_turn.dice_points -= 1

        elif link["type"] == LinkTypes.SEA.value:
            self.next_player()

        # End turn now if all dice points are used up or if choosing to wait at
        # a port
        if self.current_turn.dice_points == 0 or wait_at_port:
            self.next_player()


    def get_city_name(self, city_id):
        return self.game_map["cities"][city_id]["name"]

    def win_check(self):
        for player in self.players:
            if set(player.cities_visited) == set(player.cities):
                self.end_game(player)
            else:
                print("Cities remaining are:")
                print(set(player.cities) - set(player.cities_visited))

    def end_game(self, winner):
        print("{} has won!".format(winner.name))
        sys.exit(0)


def show_options(options, start_at=1):
    print("Your options are:")
    for i, option in enumerate(options):
        print("{}. {}".format(i + start_at, option))

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
        p = game.current_player
        print("It's {}'s turn".format(p.name))
        print("You are at {}".format(game.get_city_name(p.current_city)))

        dice_rolled = game.current_turn.dice_points is not None

        if dice_rolled:
            print("You have {} points remaining".format(game.current_turn.dice_points))

        current_player_idx = game.players.index(game.current_player)
        links = game.get_links(current_player_idx)
        link_descs = []
        for link in links:
            if link["cities"][0] == game.current_player.current_city:
                city = link["cities"][1]
            else:
                city = link["cities"][0]
            link_descs.append("{} via {}".format(game.get_city_name(city), link["type"]))

        options = link_descs
        start_at = 1

        if not dice_rolled:
            options.insert(0, "Roll dice")
            start_at = 0

        show_options(options, start_at)

        choice = int(input())

        if choice == 0:
            game.roll_dice()
            dice_rolled = True
            print("You rolled a {}".format(game.current_turn.dice_points))
            continue

        game.travel_to(current_player_idx, links[choice - 1], p.current_city)