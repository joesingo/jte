from jte import Game


class InvalidNameException(Exception):
    """There is a problem with the username provided by the user"""


class GameFullException(Exception):
    """A user tried to join a game that is already fully allocated"""


class Matchmaker(object):
    """An object to facilitate creating a Game object for a game between
    multiple players who join the game at different times"""

    def __init__(self, no_of_players, game_map):
        self.no_of_players = no_of_players
        self.game_map = game_map
        self.game = None

        # A list of usernames of the user that have joined so far
        self.player_names = []

    def add_player(self, name):
        if self.game is not None:
            raise GameFullException("That game is full")

        if not name:
            raise InvalidNameException("Name cannot be empty")

        if name in self.player_names:
            raise InvalidNameException("There is already a player with that "
                                       "name")

        self.player_names.append(name)

        if len(self.player_names) == self.no_of_players:
            self.game = Game(self.game_map, self.player_names)

    def get_status(self):
        """Return a dictionary containing all status information necessary for a
        client to know"""
        return {
            "ready": (self.game is not None),
            "player_names": self.player_names,
            "max_players": self.no_of_players
        }
