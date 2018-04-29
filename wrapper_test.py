from api_wrapper.player import Player
from api_wrapper.game import Game
import asyncio
player1 = Player("Zerg", "Computer", difficulty="VeryEasy")
player2 = Player("Terran", "Computer", difficulty="VeryHard")
game = Game(players=[player1, player2], map="../Maps/AbiogenesisLE.SC2Map", server_route='/home/marcelo/Develop/Facultad/proyecto/StarCraftII', server_address="127.0.0.1")
game.start_game()

loop = asyncio.get_event_loop()
# Blocking call which returns when the hello_world() coroutine is done
loop.run_until_complete(game.simulate())
loop.close()
