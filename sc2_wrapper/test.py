from sc2_wrapper.client import *
from os import listdir
from os.path import isfile, join
import asyncio
from sc2_wrapper.players.actions import ActionsPlayer, DEMO_ACTIONS_9
from pympler import tracker
import sys

sys.path.append("..")

try:
    from local_settings import *
except ImportError:
    pass

tr = tracker.SummaryTracker()
onlyfiles = [f for f in listdir(REPLAY_ROUTE) if isfile(join(REPLAY_ROUTE, f))]
files = list(map(lambda x: REPLAY_ROUTE + x, onlyfiles))

# def f(x):
#     loop.run_until_complete(load_replay(x))


# THREADS = 1
loop = asyncio.get_event_loop()
# try:
#     print(f(files[0]))
# finally:
#     loop.close()
# tr.print_diff()
# while True:
#     player1 = RandomPlayer()
#     loop.run_until_complete(
#         player1.create(
#             "Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS
#         )
#     )
#     loop.run_until_complete(
#         play_vs_ia(
#             player1, "Ladder2017Season3/InterloperLE.SC2Map", "Zerg", "VeryHard", 100
#         )
#     )
# for i in range(100):
#     loop.run_until_complete(
#         ia_vs_ia("Ladder2017Season3/InterloperLE.SC2Map", "Terran", "VeryHard", 24)
#     )

player1 = ActionsPlayer()
player_args = {
    "race": "Terran",
    "obj_type": "Human",
    "server_route": SERVER_ROUTE,
    "server_address": SERVER_ADDRESS,
    "actions": DEMO_ACTIONS_9,
}
loop.run_until_complete(
    play_vs_ia(
        player1,
        player_args,
        "Ladder2017Season3/InterloperLE.SC2Map",
        "Zerg",
        "VeryEasy",
        100,
    )
)

# while True:
#     player1 = CBRPlayer()
#     player2 = CBRPlayer()
#     loop.run_until_complete(
#         player2.create(
#             "Terran",
#             "Human",
#             500,
#             "Terran",
#             DATABASE_NAME,
#             DATABASE_ROUTE,
#             DATABASE_PORT,
#             server_route=SERVER_ROUTE,
#             server_address=SERVER_ADDRESS,
#         )
#     )
#     loop.run_until_complete(
#         player1.create(
#             "Terran",
#             "Human",
#             500,
#             "Terran",
#             DATABASE_NAME,
#             DATABASE_ROUTE,
#             DATABASE_PORT,
#             server_route=SERVER_ROUTE,
#             server_address=SERVER_ADDRESS,
#         )
#     )
#     loop.run_until_complete(
#         player_vs_player(player1, player2, "Ladder2017Season3/InterloperLE.SC2Map", 24)
#     )
# loop.run_until_complete(player2.create(
#     "Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS))
# loop.run_until_complete(player_vs_player(
#     player1, player2, "Ladder2017Season3/InterloperLE.SC2Map", 24))
loop.close()
