from copy import deepcopy

from api_wrapper.utils import get_available_building_unit, find_placement, select_related_gas
from constants.unit_data import UNIT_DATA
from constants.unit_dependencies import UNIT_DEPENDENCIES
from constants.unit_type_ids import UnitTypeIds
from game_data.units import UnitManager
from players.build_order import Player


def return_current_unit_dependencies(unit_id, existing_units=(UnitTypeIds.SCV.value,)):
    if unit_id in existing_units:
        return []

    # Getting dependencies 0, basic dependencies
    unit_dependencies = UNIT_DEPENDENCIES[unit_id][0]
    dependencies = deepcopy(unit_dependencies)

    for unit_dependency in unit_dependencies:
        additional_dependencies = return_current_unit_dependencies(unit_dependency, existing_units)
        dependencies = [dependency for dependency in additional_dependencies if dependency not in existing_units] \
                       + dependencies
    return dependencies


class Action:
    MISSING_DEPENDENCIES = 'missing_dependencies'
    MISSING_RESOURCES = 'missing_resources'
    READY = 'ready'

    def __init__(self):
        self.ability_id = None
        self.target = None

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self.ability_id)

    async def perform_action(self, ws, game_state):
        return

    def return_units_required(self, existing_units):
        return []

    def return_resources_required(self, game_data):
        return 0, 0, 0

    def check_state(self, game_data, existing_units, minerals, vespene, food):
        units_required = self.return_units_required(existing_units)
        minerals_required, vespene_required, food_required = self.return_resources_required(game_data)

        minerals_missing = minerals - minerals_required
        minerals_missing = - minerals_missing if minerals_missing < 0 else 0
        vespene_missing = vespene - vespene_required
        vespene_missing = - vespene_missing if vespene_missing < 0 else 0
        food_missing = food - food_required
        food_missing = - food_missing if food_missing < 0 else 0

        return units_required, minerals_missing, vespene_missing, food_missing

    def get_action_state(self, game_state):
        return [], (0, 0, 0), 'ready'


# Building Actions -------------------------------
class BuildingAction(Action):
    def __init__(self, unit_id):
        super().__init__()
        # Unit to build identifier
        self.unit_id = unit_id

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self.unit_id)

    def return_units_required(self, existing_units):
        return return_current_unit_dependencies(self.unit_id, existing_units)

    def return_resources_required(self, game_data):
        unit_data = game_data.units[self.unit_id]
        return unit_data.mineral_cost, unit_data.vespene_cost, unit_data.food_required or 3

    def get_action_state(self, game_state, existing_units=None):
        if existing_units is None:
            existing_units = set(game_state.player_units.values('unit_type', flat_list=True))

        minerals = game_state.player_info.minerals
        vespene = game_state.player_info.vespene
        food = game_state.player_info.food_cap - game_state.player_info.food_used

        units_required, minerals_missing, vespene_missing, food_missing = \
            self.check_state(game_state.game_data, existing_units, minerals, vespene, food)

        dependencies_ready = game_state.player_units.filter(unit_type__in=units_required, build_progress=1).values(
            'unit_type', flat_list=True)
        missing_dependencies = len(set(units_required) - set(dependencies_ready))

        # Determine action state
        if missing_dependencies:
            action_state = Action.MISSING_DEPENDENCIES
        elif minerals_missing or vespene_missing or food_missing:
            action_state = Action.MISSING_RESOURCES
        else:
            action_state = Action.READY
        return units_required, minerals_missing, vespene_missing, food_missing, action_state


class Build(BuildingAction):
    def __init__(self, unit_id, placement=None):
        super().__init__(unit_id)
        # Use to define target point
        self.placement = placement

    async def perform_action(self, ws, game_state):
        try:
            available_builders = get_available_building_unit(self.unit_id, game_state)

            # Get ability_id
            ability_id = game_state.game_data.units[self.unit_id].ability_id or UNIT_DATA[self.unit_id]['ability_id']

            # Get target point (for now TH1)
            # TODO: Check faction
            # Find placement
            if self.placement:
                placement = self.placement
            else:
                placement = None
                th = game_state.player_units.filter(unit_type=UnitTypeIds.COMMANDCENTER.value)[0]
                if self.unit_id in [UnitTypeIds.REFINERY.value]:
                    geysers = select_related_gas(game_state, th)
                    for geyser in geysers:
                        target_point = geyser.pos.x, geyser.pos.y
                        placement = await find_placement(ws, ability_id, target_point)
                        if placement:
                            break
                else:
                    target_point = th.pos.x, th.pos.y
                    placement = await find_placement(ws, ability_id, target_point)

            # Select builder
            # TODO: Get closest builder
            builder = available_builders[0]

            # Send order
            result = await UnitManager([builder]).give_order(ws, ability_id, target_point=placement)
            # print(result)

            # Return result
            return result.action.result[0]
        except Exception:
            return False


class Train(BuildingAction):
    def __init__(self, unit_id, amount=1, rally_point=None):
        super().__init__(unit_id)
        # Amount of units to train
        self.amount = amount
        # Rally point
        self.rally_point = rally_point

    async def perform_action(self, ws, game_state):
        try:
            available_builders = get_available_building_unit(self.unit_id, game_state)
            ability_id = game_state.game_data.units[self.unit_id].ability_id or UNIT_DATA[self.unit_id]['ability_id']

            # Select builder
            builder = available_builders[0]
            # Send order
            result = await UnitManager([builder]).give_order(ws, ability_id)
            # Return result
            return result.action.result[0]
        except Exception:
            return False

    def return_resources_required(self, game_data):
        mineral_cost, vespene_cost, food_required = super(Train, self).return_resources_required(game_data)
        return mineral_cost * self.amount, vespene_cost * self.amount, food_required * self.amount


# Unit Actions -------------------------------
class UnitAction(Action):
    def __init__(self):
        super().__init__()
        # Unit group composition
        #   {type: MARINE, amount: 10}
        self.unit_group = []


class Move(UnitAction):
    def __init__(self):
        super().__init__()


class Attack(UnitAction):
    def __init__(self):
        super().__init__()


class Use(UnitAction):
    def __init__(self):
        super().__init__()
        # Skill used identifier
        self.skill = None


class ActionsPlayer(Player):
    def __init__(self):
        self.actions_queue = []
        self.pending_actions = []

    async def create(self, race, obj_type, difficulty=None, server=None, server_route=None, server_address=None,
                     **kwargs):

        await super().create(race, obj_type, difficulty, server, server_route, server_address, **kwargs)
        self.actions_queue = kwargs.get('actions', [])

    def get_required_actions(self, game_state):
        # Check remaining orders
        if len(self.actions_queue) < 1:
            print("Ran out of actions")
            return

        # Current state summary
        existing_units = set(game_state.player_units.values('unit_type', flat_list=True))
        actions = deepcopy(self.actions_queue)
        actions.reverse()
        actions_and_dependencies = []
        ready_actions = []

        for action in actions:
            unit_queue_set = [action.unit_id for action, state in actions_and_dependencies]

            # Check if action available
            required_actions = []

            units_required, minerals_missing, vespene_missing, food_missing, action_state = \
                action.get_action_state(game_state, existing_units)

            # Check units for construction and add to queue if not added already
            # Check vespene production
            if vespene_missing:
                # TODO: Check faction
                refinery_id = UnitTypeIds.REFINERY.value
                current_units = existing_units.union(unit_queue_set)
                if refinery_id not in current_units:
                    units_required.append(refinery_id)

            # Check if food is missing, "You must construct additional Pylons"
            if food_missing:
                # TODO: Check faction
                farm_id = UnitTypeIds.SUPPLYDEPOT.value
                if farm_id not in unit_queue_set:
                    units_required.append(farm_id)

            # Create actions for required units
            for unit_id in units_required:
                # TODO: Check if build or train
                action_required = Build(unit_id)
                _, m, v, f, state = action_required.get_action_state(game_state, existing_units)

                # Check if refinery should be added
                # TODO: Check faction
                refinery_id = UnitTypeIds.REFINERY.value
                if v and refinery_id not in units_required:
                    units_required.append(refinery_id)

                if state == Action.READY:
                    m, v, _ = action_required.return_resources_required(game_state.game_data)
                    game_state.player_info.minerals -= m
                    game_state.player_info.vespene -= v

                required_actions.append((action_required, state))

            if action_state == Action.READY:
                m, v, _ = action.return_resources_required(game_state.game_data)
                game_state.player_info.minerals -= m
                game_state.player_info.vespene -= v

            # Append tuple with action information
            actions_and_dependencies += required_actions + [(action, action_state)]

        return actions_and_dependencies

    async def perform_ready_actions(self, ws, new_actions, game_state):
        remaining_actions = []
        for action, state in new_actions:
            # Attempt to perform actions ready
            if state == Action.READY:
                success = await action.perform_action(ws, game_state)
                if not success:
                    remaining_actions.append(action)
            else:
                remaining_actions.append(action)
        return remaining_actions

    async def process_step(self, ws, game_state, actions=None):
        new_actions = self.get_required_actions(game_state)
        self.actions_queue = await self.perform_ready_actions(ws, new_actions, game_state)
        # print(new_actions)


DEMO_ACTIONS = [Train(UnitTypeIds.MARAUDER.value, 10)]
DEMO_ACTIONS_2 = [Train(UnitTypeIds.MARINE.value, 1) for _ in range(3)]
