from client import *
from os import listdir
from os.path import isfile, join
import asyncio
from players.actions import ActionsPlayer, DEMO_ACTIONS_9
from pympler import tracker
import sys
import json
from players.cbr_algorithm import CBRAlgorithm
from pymongo import MongoClient
import requests

from players.rules import IDLE_RULES

sys.path.append("..")

try:
    from local_settings import *
except ImportError:
    pass

tr = tracker.SummaryTracker()
onlyfiles = [f for f in listdir(REPLAY_ROUTE) if isfile(join(REPLAY_ROUTE, f))]
files = list(map(lambda x: REPLAY_ROUTE + x, onlyfiles))


async def f(x):
    client = MongoClient(compressors="zlib", zlibCompressionLevel=9)
    db = client.test_database
    collection = db.test
    async for i in load_replay(x,24):
        collection.insert_one(i)


# THREADS = 1
loop = asyncio.get_event_loop()
# try:
#     loop.run_until_complete(f(files[0]))
# finally:
#     loop.close()
# tr.print_diff()

# observations = []
# i = 0
# while i < 80:
#     print(i)
#     r = requests.get("http://dumbbots.ddns.net/sample/")
#     print(r)
#     if r.status_code == 200:
#         observations += r.json()
#         i += 1
#     else:
#         print("Error, retrying")
#
# a = open('test_obs.txt', 'w')
# a.write(json.dumps(observations))
# a.close()

a = open('test_obs.txt', 'r')
observations = json.loads(a.read())
a.close()


# while True:

player1 = CBRAlgorithm()
loop.run_until_complete(
    player1.create(
        "Terran", "Human",
        server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS,
        cases=observations, rules=IDLE_RULES,
    )
)
loop.run_until_complete(
    play_vs_ia(player1, {}, "Ladder2017Season3/InterloperLE.SC2Map", "Terran", "VeryEasy", 24)
)

# for i in range(100):
#     loop.run_until_complete(
#         ia_vs_ia("Ladder2017Season3/InterloperLE.SC2Map", "Terran", "VeryHard", 24)
#     )

# player1 = ActionsPlayer()
# player_args = {
#     "race": "Terran",
#     "obj_type": "Human",
#     "server_route": SERVER_ROUTE,
#     "server_address": SERVER_ADDRESS,
#     "actions": DEMO_ACTIONS_9,
# }
# loop.run_until_complete(
#     play_vs_ia(
#         player1,
#         player_args,
#         "Ladder2017Season3/InterloperLE.SC2Map",
#         "Zerg",
#         "VeryEasy",
#         100,
#     )
# )

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
# loop.close()
