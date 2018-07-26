from client import *
loop = asyncio.get_event_loop()

# loop.run_until_complete(load_replay(REPLAY_ROUTE + "ffffac3c77fe8697d6be7164068299499a517244bb741c92b5b10199130e9948.SC2Replay", 100))

player1 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
loop.run_until_complete(play_vs_ia(player1, "Ladder2018Season1/AbiogenesisLE.SC2Map", "Zerg", "VeryHard", 100))


# player1 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# player2 = RandomPlayer("Terran", "Human", server_route=SERVER_ROUTE, server_address=SERVER_ADDRESS)
# loop.run_until_complete(player_vs_player(player1, player2, "Ladder2018Season1/AbiogenesisLE.SC2Map", 100))

loop.close()