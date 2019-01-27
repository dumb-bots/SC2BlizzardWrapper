import enum
from copy import deepcopy

from s2clientprotocol.data_pb2 import Attribute

from  constants import UNIT_DEPENDENCIES
from  constants.unit_type_ids import UnitTypeIds
from players.build_order import BuildOrderPlayer, PlayerOrder


class ObjectiveTypes(enum.Enum):
    BUILD = 1
    ATTACK = 2


class Objective:
    def __init__(self, objective_type, units, target=None):
        self.objective_type = objective_type
        self.units = units
        self.target = target


class ObjectivesPlayer(BuildOrderPlayer):
    async def create(self, race, obj_type, difficulty=None, server=None, server_route=None, server_address=None, **kwargs):
        await super().create(race, obj_type, difficulty, server, server_route, server_address, **kwargs)
        self.objectives = kwargs.get('objectives', [])

    def resolve_dependencies(self, unit_id, existing_units=(UnitTypeIds.SCV.value,)):
        if unit_id in existing_units:
            return []

        # Getting dependencies 0, basic dependencies
        unit_dependencies = UNIT_DEPENDENCIES[unit_id][0]
        dependencies = deepcopy(unit_dependencies)

        for unit_dependency in unit_dependencies:
            additional_dependencies = self.resolve_dependencies(unit_dependency)
            additional_dependencies.reverse()
            dependencies = [dependency for dependency in additional_dependencies if dependency not in existing_units] \
                           + dependencies
        return dependencies

    def order_unit_creation(self, unit, game_state):
        unit_dependencies = self.resolve_dependencies(unit['id'])
        for dependency in unit_dependencies:
            dep_data = game_state.game_data.units[dependency]
            ability_id = dep_data.ability_id
            if Attribute.Value("Structure") in dep_data.attributes:
                worker = "SCV"
                town_hall = "CommandCenter"
                order = PlayerOrder(
                    unit_filters={"name": worker}, unit_index=0, ability_id=ability_id,
                    target={"unit": {"filter_params": {"name": town_hall}, "index": 0}, "diff": (-6, 6)})
                self.orders.append(order)
            else:
                raise NotImplemented("Not implemented for non structure units")

        unit_data = game_state.game_data.units[unit['id']]
        ability_id = unit_data.ability_id
        order = PlayerOrder(unit_filters={"unit_id": UNIT_DEPENDENCIES[unit['id']][0][0]}, ability_id=ability_id,
                            target=None, repeat=20)
        self.orders.append(order)

    def process_build_objective(self, game_state, objective):
        for unit in objective.units:
            self.order_unit_creation(unit, game_state)


    def prepare_orders(self, game_state):
        for objective in self.objectives:
            if objective.objective_type == ObjectiveTypes.BUILD:
                self.process_build_objective(game_state, objective)
            else:
                print("Unknown objective type")

    async def process_step(self, ws, game_state):
        print(self.resolve_dependencies(UnitTypeIds.MARINE.value))
        if self.orders or self.current_order is not None:
            await self.process_next_order(ws, game_state)
        else:
            self.prepare_orders(game_state)

DEMO_OBJECTIVES_SET = [Objective(objective_type=ObjectiveTypes.BUILD,
                                 units=[{"id": UnitTypeIds.MARINE.value, "q": 20}],
                                 target=None)]
