from client import *
from os import listdir
from os.path import isfile, join
from multiprocessing import Pool

onlyfiles = [f for f in listdir(REPLAY_ROUTE) if isfile(join(REPLAY_ROUTE, f))]
files = list(map(lambda x : REPLAY_ROUTE + x, onlyfiles))

def f(x):
    loop.run_until_complete(load_replay(x))

loop = asyncio.get_event_loop()
try:
    p = Pool(5)
    print(p.map(f, files))
finally:
    loop.close()

# player1 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# loop.run_until_complete(play_vs_ia(player1, "Ladder2018Season1/AbiogenesisLE.SC2Map", "Zerg", "VeryHard", 100))


# player1 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# player2 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# loop.run_until_complete(player_vs_player(player1, player2, "Ladder2018Season1/AbiogenesisLE.SC2Map", 100))
