import sys
import os

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(DIR + "/sc2_wrapper")
print(sys.path)

from api_wrapper.player import Player
from api_wrapper.game import (
    Replay,
    Classifier,
    PlayerVSIA,
    PlayerVSPlayer,
    IAVSIA,
)
import json
try:
    from local_settings import *
except ImportError:
    pass


async def load_replay(replay_name, step=24):
    game = Replay(SERVER_ROUTE, SERVER_ADDRESS)
    await game.create()
    retries = 10
    success = False
    for i in range(0, retries):
        try:
            success = await game.load_replay(replay_name, id=2)
            break
        except Exception as e:
            print(e)

    if success:
        sidea = game.observe_replay(step, 2)
        async for obs in sidea:
            yield obs
        game.host.status = "idle"
        game = Replay(SERVER_ROUTE, SERVER_ADDRESS)
        await game.create()
        for i in range(0, retries):
            try:
                success = await game.load_replay(replay_name, id=1)
                break
            except Exception as e:
                print(e)
        sideb = game.observe_replay(step, 1)
        game.host.status = "idle"
        async for obs in sideb:
            yield obs
    else:
        yield False


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
