from api_wrapper.player import Player
from api_wrapper.game import Game
import asyncio
player1 = Player("Terran", "Human", server_route='/home/marcelo/StarCraftII', server_address="127.0.0.1")
# player2 = Player("Zerg", "Human", server_route='/home/marcelo/StarCraftII', server_address="127.0.0.1")
player2 = Player("Terran", "Computer", difficulty="VeryHard")
game = Game(players=[player1, player2], map="../Maps/Ladder2018Season1/AbiogenesisLE.SC2Map", server_route='/home/marcelo/StarCraftII', server_address="127.0.0.1")
game.start_game()

loop = asyncio.get_event_loop()
loop.run_until_complete(game.start_game())
loop.run_until_complete(game.simulate())
loop.close()
game.get_replay()
