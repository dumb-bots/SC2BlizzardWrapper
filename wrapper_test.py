from api_wrapper.player import Player
from api_wrapper.game import Game
import asyncio

from players.build_order import BuildOrderPlayer, DEMO_ORDER_SET
from players.random import RandomPlayer

# player1 = RandomPlayer("Terran", "Human", server_route='/home/marcelo/Develop/Facultad/proyecto/StarCraftII', server_address="127.0.0.1",)
# player2 = Player("Terran", "Computer", difficulty="Medium")
# game = Game(players=[player1, player2], map="Ladder2018Season1/AbiogenesisLE.SC2Map", server_route='/home/marcelo/StarCraftII', server_address="127.0.0.1")
game = Game(server_route='/home/marcelo/Develop/Facultad/proyecto/StarCraftII', server_address='127.0.0.1')
game.load_replay("/home/marcelo/Develop/Facultad/proyecto/StarCraftII/Replays/ffffac3c77fe8697d6be7164068299499a517244bb741c92b5b10199130e9948.SC2Replay")
loop = asyncio.get_event_loop()
# loop.run_until_complete(game.start_game())
loop.run_until_complete(game.simulate(10))
game.get_replay()
loop.close()