from api_wrapper.player import Player
from api_wrapper.game import Game
import asyncio

from players.build_order import BuildOrderPlayer, DEMO_ORDER_SET
from players.random import RandomPlayer
try:
    from local_settings import *
except ImportError:
    pass

async def load_replay(replay_name, step):
    game = Game()
    await game.create(server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
    game.load_replay(replay_name,id=2)
    await game.observe_replay(step)
    game.host.process.terminate()

    game = Game()
    await game.create(server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)  
    game.load_replay(replay_name,id=1)
    await game.observe_replay(step)
    game.host.process.terminate()


async def play_vs_ia(player, starcrat_map, race, difficulty, step):
    player1 = player
    player2 = Player(race, "Computer", difficulty)
    game = Game()
    await game.create(players=[player1, player2], map=starcrat_map, server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
    await game.start_game()
    await game.simulate(step)
    game.get_replay()

async def player_vs_player(player1, player2, starcrat_map, step):
    game = Game()
    await game.create(players=[player1, player2], map=starcrat_map, server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
    await game.start_game()
    await game.simulate(step)
    game.get_replay()

