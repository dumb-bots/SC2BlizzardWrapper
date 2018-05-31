from s2clientprotocol.raw_pb2 import Alliance

from api_wrapper.player import Player
from api_wrapper.utils import find_placement
from constants.ability_ids import AbilityId
from game_data.units import UnitManager

# TODO: Define all build abilities
BUILD_ABILITIES = [319, 321]

class PlayerOrder:
    def __init__(self, unit_filters, ability_id, target, repeat=1, unit_index=None):
        self.unit_filters = unit_filters
        self.ability_id = ability_id
        self.target = target
        self.repeat = repeat
        self.unit_index = unit_index

    async def process_order(self, ws, game_state):
        if self.unit_index:
            index = self.unit_index
            units = UnitManager(game_state.player_units.filter(**self.unit_filters)[index : index + 1])
        else:
            units = game_state.player_units.filter(**self.unit_filters)

        target_unit = None
        target_point = None
        if self.target:
            if self.target.get("unit"):
                # Select unit manager given the target's alliance
                if self.target['unit'].get("alliance"):
                    if self.target['unit']["alliance"] == Alliance.Value("Enemy"):
                        unit_manager = game_state.enemy_units
                    else:
                        unit_manager = game_state.player_units
                else:
                    unit_manager = game_state.player_units

                unit = unit_manager.filter(
                    **self.target['unit']['filter_params'])[self.target['unit']['index']]
                if self.target.get("diff"):
                    diff = self.target["diff"]
                    target_point = (unit.get_attribute("pos").x + diff[0], unit.get_attribute("pos").y + diff[1])
                elif self.target['unit'].get("pos"):
                    target_point = (unit.get_attribute("pos").x, unit.get_attribute("pos").y)
                else:
                    target_unit = unit
            elif self.target.get("point"):
                target_point = self.target['point']
        if self.ability_id in BUILD_ABILITIES:
            target_point = await find_placement(ws, self.ability_id, target_point)
        await units.give_order(ws, ability_id=self.ability_id, target_point=target_point, target_unit=target_unit)


class BuildOrderPlayer(Player):
    def __init__(self, race, type, difficulty=None, server=None, server_route=None, server_address=None, **kwargs):
        super().__init__(race, type, difficulty, server, server_route, server_address, **kwargs)
        self.orders = kwargs.get('orders', [])
        self.current_order = 0
        self.order_repetition = 0

    async def process_step(self, ws, game_state, actions=None):
        if self.current_order < len(self.orders):
            order = self.orders[self.current_order]
            await order.process_order(ws, game_state)
            self.order_repetition += 1
            if self.order_repetition >= order.repeat:
                self.order_repetition = 0
                self.current_order += 1
        else:
            print("Ran out of steps!")


DEMO_ORDER_SET = (PlayerOrder(unit_filters={"name": "CommandCenter"}, ability_id=AbilityId.TRAIN_SCV.value,
                              target=None, repeat=2),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=0, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "CommandCenter"}, "index": 0}, "diff": (4, 4)}),
                  PlayerOrder(unit_filters={"name": "CommandCenter"}, ability_id=AbilityId.TRAIN_SCV.value,
                              target=None, repeat=2),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=0, ability_id=AbilityId.BUILD_BARRACKS.value,
                              target={"unit": {"filter_params": {"name": "CommandCenter"}, "index": 0}, "diff": (-6, 6)}),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=1, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "CommandCenter"}, "index": 0}, "diff": (4, -4)}),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=0, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "CommandCenter"}, "index": 0}, "diff": (-4, -4)}),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=1, ability_id=AbilityId.BUILD_BARRACKS.value,
                              target={"unit": {"filter_params": {"name": "Barracks"}, "index": 0}, "diff": (5, 0)}),
                  PlayerOrder(unit_filters={"name": "SCV"},unit_index=0, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "Barracks"}, "index": 0}, "diff": (-4, 0)}),
PlayerOrder(unit_filters={"name": "SCV"},unit_index=3, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "Barracks"}, "index": 0}, "diff": (-4, 0)}),
PlayerOrder(unit_filters={"name": "SCV"},unit_index=1, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "Barracks"}, "index": 0}, "diff": (-4, 0)}),
PlayerOrder(unit_filters={"name": "SCV"},unit_index=2, ability_id=AbilityId.BUILD_SUPPLYDEPOT.value,
                              target={"unit": {"filter_params": {"name": "Barracks"}, "index": 0}, "diff": (-4, 0)}),
                  PlayerOrder(unit_filters={"name": "Barracks"}, ability_id=AbilityId.TRAIN_MARINE.value,
                              target=None, repeat=40),
                  PlayerOrder(unit_filters={"name": "Marine"}, ability_id=AbilityId.ATTACK.value,
                              target={"unit": {"filter_params": {"name": "OrbitalCommand"}, "index": 0,
                                               "alliance": Alliance.Value("Enemy"), "pos": True}}),

                  )
