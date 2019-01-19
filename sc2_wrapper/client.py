from sc2_wrapper.api_wrapper.player import Player
from sc2_wrapper.api_wrapper.game import (
    Replay,
    Classifier,
    PlayerVSIA,
    PlayerVSPlayer,
    IAVSIA,
)
import json
import sys

sys.path.append("..")

try:
    from local_settings import *
except ImportError:
    pass


async def load_replay(replay_name, step=5000):
    game = Replay(SERVER_ROUTE, SERVER_ADDRESS)
    await game.create()
    await game.load_replay(replay_name, id=2)
    sidea = game.observe_replay(step, 2)
    async for obs in sidea:
        yield obs
    game.host.status = "idle"
    game = Replay(SERVER_ROUTE, SERVER_ADDRESS)
    await game.create()
    await game.load_replay(replay_name, id=1)
    sideb = game.observe_replay(step, 1)
    game.host.status = "idle"
    async for obs in sideb:
        yield obs


async def classify(replay_name):
    game = Classifier(SERVER_ROUTE, SERVER_ADDRESS)
    await game.create()
    await game.load_replay(replay_name, id=2)
    meta = await game.observe_replay(24, 2)
    return json.dumps(meta)


async def play_vs_ia(player, player_args, starcrat_map, race, difficulty, step):
    await player.create(**player_args)
    player1 = player
    player2 = Player()
    await player2.create(race, "Computer", difficulty)
    game = PlayerVSIA(starcrat_map, player, player2)
    await game.create()
    await game.start_game()
    await game.simulate(step)
    await game.get_replay()


async def player_vs_player(player1, player2, starcrat_map, step):
    game = PlayerVSPlayer(starcrat_map, [player1, player2])
    await game.create()
    await game.start_game()
    await game.simulate(step)
    await game.get_replay()


async def ia_vs_ia(starcrat_map, race, difficulty, step):
    player1 = Player()
    await player1.create(race, "Computer", difficulty)
    player2 = Player()
    await player2.create(race, "Computer", difficulty)
    game = IAVSIA(starcrat_map, SERVER_ROUTE, SERVER_ADDRESS, [player1, player2])
    await game.create()
    await game.start_game()
    await game.simulate(step)
    await game.get_replay()
