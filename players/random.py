import random
from game_data.units import UnitManager
from api_wrapper.player import Player
from constants.ability_ids import AbilityId
class RandomPlayer(Player):
    async def process_step(self, ws, game_state, actions=None):
        significant = False
        counter = 0
        if game_state.game_loop > 1500:
            while not significant and counter < 10:
                index = random.randint(0, len(actions) - 1)
                action = actions[index]
                manager = UnitManager([action.unit])
                if action.unit.name != "SCV" or (action.ability_id > 30):
                    significant = True
                counter += 1
                
            if action.require_target:
                x = random.randint(-10,10)
                y = random.randint(-10,10)
                unit_x = action.unit.get_attribute("pos").x
                unit_y = action.unit.get_attribute("pos").y
                await  manager.give_order(ws, action.ability_id, target_point=(unit_x + x,unit_y + y))
            else:
                await manager.give_order(ws, action.ability_id)


        