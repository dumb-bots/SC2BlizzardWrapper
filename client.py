from api_wrapper.player import Player
from api_wrapper.game import Game
import asyncio
from concurrent.futures import ProcessPoolExecutor
from players.build_order import BuildOrderPlayer, DEMO_ORDER_SET
from players.random import RandomPlayer
try:
    from local_settings import *
except ImportError:
    pass



async def load_replay(replay_name, step=24, matchup=""):
    if DATABASE_NAME == "mongo":
        from pymongo import MongoClient
        client = MongoClient(DATABASE_ROUTE, DATABASE_PORT)
    else:
        client = None
    game = Game()
    await game.create(server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS, matchup=matchup)
    game.load_replay(replay_name,id=2)
    await game.observe_replay(step, client, 2)
    game.host.process.terminate()

    game = Game()
    await game.create(server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS, matchup=matchup)  
    game.load_replay(replay_name,id=1)
    await game.observe_replay(step, client, 1)
    game.host.process.terminate()

    if client:
        client.close()


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

async def ia_vs_ia(starcrat_map, race, difficulty, step):
    player1 = Player(race, "Computer", difficulty)
    player2 = Player(race, "Computer", difficulty)
    game = Game()
    await game.create(players=[player1, player2], map=starcrat_map, server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
    await game.start_game()
    await game.simulate(step)
    game.get_replay()