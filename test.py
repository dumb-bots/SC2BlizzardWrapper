from client import *
from os import listdir
from os.path import isfile, join
from multiprocessing import Pool
from subprocess import call
from players.cbr_player import CBRPlayer
try:
    from local_settings import *
except ImportError:
    pass


onlyfiles = [f for f in listdir(REPLAY_ROUTE) if isfile(join(REPLAY_ROUTE, f))]
files = list(map(lambda x : REPLAY_ROUTE + x, onlyfiles))

def f(x):
    loop.run_until_complete(load_replay(x,matchup="11"))

THREADS = 6
loop = asyncio.get_event_loop()
# try:
#     for i in range(1,int(len(files) / THREADS)):
#         p = Pool(THREADS)
#         start = THREADS * (i-1)
#         end = THREADS * i   
#         p.map(f, files[start:end])
#         print(call(["sudo", "killall", "-9", "/home/marcelo/git/StarCraftII/Versions/Base55958/SC2_x64"]))
# finally:
#     loop.close()

# player1 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# loop.run_until_complete(play_vs_ia(player1, "Ladder2017Season3/InterloperLE.SC2Map", "Zerg", "VeryHard", 100))
# for i in range(100):
#     loop.run_until_complete(ia_vs_ia("Ladder2017Season3/InterloperLE.SC2Map", "Terran", "VeryHard", 24))

player1 = CBRPlayer("Terran", "Human", 500, "Terran", DATABASE_NAME, DATABASE_ROUTE, DATABASE_PORT, server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
player2 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
loop.run_until_complete(player_vs_player(player1, player2, "Ladder2017Season3/InterloperLE.SC2Map", 24))
loop.close()