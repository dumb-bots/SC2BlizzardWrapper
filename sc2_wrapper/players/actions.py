import itertools
import traceback
from typing import Tuple, List, Dict, Union

from api_wrapper.utils import get_available_building_unit, find_placement, select_related_gas, \
    get_available_builders, \
    select_related_minerals, select_related_refineries, get_available_upgrade_buildings, get_upgrading_building, \
    return_current_unit_dependencies, return_current_ability_dependencies, return_upgrade_building_requirements, \
    return_missing_parent_upgrades, group_resources, ADDON_BUILDINGS, get_ongoing_build_orders
from constants.ability_ids import AbilityId
from constants.build_abilities import BUILD_ABILITY_UNIT
from constants.unit_data import UNIT_DATA
from constants.unit_type_ids import UnitTypeIds
from constants.upgrade_data import UPGRADE_DATA
from constants.upgrade_ids import UpgradeIds
from game_data.observations import DecodedObservation
from game_data.units import UnitManager, Unit
from game_data.utils import euclidean_distance
from players.build_order import Player


class UnitDestroyed(Exception):
    pass


class Action:
    MISSING_DEPENDENCIES = 'missing_dependencies'
    MISSING_RESOURCES = 'missing_resources'
    READY = 'ready'

    def __init__(self):
        self.fail_counter = 0
        self.ability_id = None
        self.target = None

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self.ability_id)

    async def perform_action(self, ws, game_state):
        return

    def return_units_required(self, game_state, existing_units):
        return {}

    def return_upgrades_required(self, existing_upgrades):
        return {}

    def return_resources_required(self, game_data):
        return 0, 0, 0

    def check_state(self, game_state, existing_units, existing_upgrades):
        minerals = game_state.player_info.minerals
        vespene = game_state.player_info.vespene
        food = game_state.player_info.food_cap - game_state.player_info.food_used

        units_required = self.return_units_required(game_state, existing_units)
        upgrades_required = self.return_upgrades_required(existing_upgrades)
        minerals_required, vespene_required, food_required = self.return_resources_required(game_state.game_data)

        minerals_missing = self.resource_missing(minerals, minerals_required)
        vespene_missing = self.resource_missing(vespene, vespene_required)
        food_missing = self.food_missing(food, food_required)

        return units_required, upgrades_required, minerals_missing, vespene_missing, food_missing

    def resource_missing(self, resource, resource_required):
        resource_missing = resource - resource_required
        resource_missing = - resource_missing if resource_missing < 0 else 0
        return resource_missing

    def food_missing(self, food, food_required):
        return self.resource_missing(food, food_required)

    def get_units_ready_for_action(self, game_state):
        return game_state.player_units.filter(build_progress=1).values('unit_type', flat_list=True)

    def get_action_state(self, game_state):
        existing_units = game_state.player_units.values('unit_type', flat_list=True)
        existing_units += self.units_in_build_queue(game_state)

        existing_upgrades = {u.upgrade_id for u in game_state.player_info.upgrades}

        units_required, upgrades_required, minerals_missing, vespene_missing, food_missing = \
            self.check_state(game_state, existing_units, existing_upgrades)

        ready_units = self.get_units_ready_for_action(game_state)
        missing_units = len(self.return_units_required(game_state, ready_units))
        aux = self.return_upgrades_required(existing_upgrades)
        if not aux:
            missing_upgrades = 0
        else:
            missing_upgrades = len(aux)

        # Determine action state
        if missing_units > 0 or missing_upgrades > 0:
            action_state = Action.MISSING_DEPENDENCIES
        elif minerals_missing or vespene_missing or food_missing:
            action_state = Action.MISSING_RESOURCES
        else:
            action_state = Action.READY
        return units_required, upgrades_required, minerals_missing, vespene_missing, food_missing, action_state

    def determine_action_state(self, game_state, units_queue, upgrades_queue):
        required_actions = []

        # Units query
        existing_units = set(game_state.player_units.values('unit_type', flat_list=True))
        all_units = existing_units.union(set(units_queue))

        units_required, upgrades_required, minerals_missing, vespene_missing, food_missing, action_state = \
            self.get_action_state(game_state)

        # Check additional missing units
        vespene_units = self.vespene_dependency(all_units, vespene_missing)
        food_units = self.food_dependency(units_queue, food_missing, game_state.player_info.food_cap)
        units_required.update(vespene_units)
        units_required.update(food_units)

        # Add dependencies
        self.add_build_dependencies(game_state, units_queue, upgrades_queue, units_required, required_actions)
        self.add_upgrade_dependencies(game_state, units_queue, upgrades_queue, upgrades_required, required_actions)
        return action_state, required_actions

    def add_upgrade_dependencies(self, game_state, units_queue, upgrades_queue, upgrades_required, required_actions):
        # Create actions for required units
        for upgrade in upgrades_required:
            if upgrade not in upgrades_queue and not self.upgrade_in_game_queue(game_state, upgrade):
                self.add_upgrade_actions(
                    upgrade,
                    game_state,
                    units_queue,
                    upgrades_queue,
                    required_actions,
                )

    def add_build_dependencies(self, game_state, units_queue, upgrades_queue, units_required, required_actions):
        # Create actions for required units
        for unit_id, amount in units_required.items():

            # Get number of units required
            reduced = self.number_of_units_under_construction(game_state, unit_id, units_queue)
            if amount <= reduced:
                continue
            else:
                amount -= reduced

            building_stuck = len(game_state.player_units.filter(name__in=["SCV", "CommandCenter"])) == 0
            if not building_stuck:
                self.add_build_actions(
                    unit_id,
                    amount,
                    game_state,
                    units_queue,
                    upgrades_queue,
                    required_actions,
                )

    def add_upgrade_actions(self, upgrade, game_state, units_queue, upgrades_queue, required_actions,):
        existing_units = set(game_state.player_units.values('unit_type', flat_list=True))
        all_units = existing_units.union(set(units_queue))

        # Add required buildings
        buildings_required = return_upgrade_building_requirements(upgrade, all_units)
        units_required = {unit_id: 1 for unit_id in buildings_required}
        self.add_build_dependencies(game_state, units_queue, upgrades_queue, units_required, required_actions)

        # Add action
        action = Upgrade(upgrade)
        _, _, _, _, food_missing, state = self.get_action_state(game_state)
        if state == Action.READY:
            m, v, _ = action.return_resources_required(game_state.game_data)
            game_state.player_info.minerals -= m
            game_state.player_info.vespene -= v

        # Add a build action for required unit
        required_actions.append((action, state))
        upgrades_queue.append(upgrade)

    def vespene_dependency(self, current_units, vespene_missing):
        missing_units = {}
        if vespene_missing:
            # TODO: Check faction
            refinery_id = UnitTypeIds.REFINERY.value
            if refinery_id not in current_units:
                missing_units[refinery_id] = 1
        return missing_units

    def food_dependency(self, units_in_queue, food_missing, food_cap):
        missing_units = {}
        if food_missing and food_cap < 200:
            # TODO: Check faction
            farm_id = UnitTypeIds.SUPPLYDEPOT.value
            if farm_id not in units_in_queue:
                missing_units[farm_id] = 1
        return missing_units

    def upgrade_in_game_queue(self, game_state, upgrade):
        for builder in get_available_upgrade_buildings(game_state, upgrade):
            for order in builder.orders:
                if order.ability_id == UPGRADE_DATA[upgrade]['ability_id']:
                    return True
        return False

    def number_of_units_under_construction(self, game_state, unit_id, unit_queue_set):
        # Decrease required units based on queue units
        queue_count = unit_queue_set.count(unit_id)
        # Decrease required units based on units under construction
        in_progress = 0
        build_ability_id = game_state.game_data.units[unit_id].ability_id or UNIT_DATA[unit_id]['ability_id']
        for builder in get_available_builders(unit_id, game_state):
            for order in builder.orders:
                if order.ability_id == build_ability_id:
                    in_progress += 1
        # Reduce units required
        reduced = queue_count + in_progress
        return reduced

    def add_build_actions(self, unit_id, amount, game_state, units_queue, upgrades_queue, required_actions):
        action_required = self.get_action(unit_id)

        # Add unit dependencies
        units_queue.append(unit_id)
        state, _required_units = action_required.determine_action_state(game_state, units_queue, upgrades_queue)
        required_actions += _required_units
        # Added requirements to queue
        for _ in range(amount):
            _, _, _, _, food_missing, state = self.get_action_state(game_state)
            if state == Action.READY:
                m, v, _ = action_required.return_resources_required(game_state.game_data)
                game_state.player_info.minerals -= m
                game_state.player_info.vespene -= v

            # Add a build action for required unit
            action = self.get_action(unit_id)
            required_actions.append((action, state))

    def get_action(self, unit_id):
        if UNIT_DATA.get(unit_id, {}).get('food_required', 0) > 0:
            action_required = Train(unit_id)
        elif unit_id == UnitTypeIds.COMMANDCENTER.value:
            action_required = Expansion()
        else:
            action_required = Build(unit_id)
        return action_required

    def units_in_build_queue(self, game_state):
        worker_orders = game_state.player_units.filter(name='SCV').values('orders', flat_list=True)
        plain_worker_orders = itertools.chain(*worker_orders)
        abilities_in_queue = [order.ability_id for order in plain_worker_orders]
        units_in_queue = [BUILD_ABILITY_UNIT[ability_id] for ability_id in abilities_in_queue
                          if BUILD_ABILITY_UNIT.get(ability_id)]
        return units_in_queue


# Building Actions -------------------------------
class BuildingAction(Action):
    def __init__(self, unit_id):
        super().__init__()
        # Unit to build identifier
        self.unit_id = unit_id

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self.unit_id)

    def return_units_required(self, game_state, existing_units):
        # For building, only requires 1 unit available
        existing_units = self._check_addons(game_state, existing_units)
        try:
            unit_dependencies = return_current_unit_dependencies(self.unit_id, set(existing_units))
            if unit_dependencies:
                return {unit_type: 1 for unit_type in unit_dependencies}
            else:
                return {}
        except Exception as e:
            print(self.unit_id)
            print(existing_units)
            print(traceback.print_exc())
            return {}

    def return_resources_required(self, game_data):
        unit_data = game_data.units[self.unit_id]
        unit_data_patch = UNIT_DATA[self.unit_id]

        return unit_data.mineral_cost, \
               unit_data.vespene_cost, \
               unit_data.food_required or unit_data_patch.get('food_required', 0)

    def _check_addons(self, game_state, existing_units):
        if self.unit_id not in ADDON_BUILDINGS:
            return existing_units

        existing_units = self._check_addon_units(
            UnitTypeIds.BARRACKS.value,
            [UnitTypeIds.BARRACKSTECHLAB.value, UnitTypeIds.BARRACKSREACTOR.value],
            game_state, existing_units
        )
        existing_units = self._check_addon_units(
            UnitTypeIds.FACTORY.value,
            [UnitTypeIds.FACTORYTECHLAB.value, UnitTypeIds.FACTORYREACTOR.value],
            game_state, existing_units
        )
        existing_units = self._check_addon_units(
            UnitTypeIds.STARPORT.value,
            [UnitTypeIds.STARPORTTECHLAB.value, UnitTypeIds.STARPORTREACTOR.value],
            game_state, existing_units
        )
        return existing_units

    def _check_addon_units(self, unit, addon_units, game_state, existing_units):
        if self.unit_id in addon_units:
            unit_count = existing_units.count(unit)
            units_with_addons = len(game_state.player_units.filter(unit_type__in=addon_units))
            if units_with_addons >= unit_count:
                return [u for u in existing_units if u != unit]
        return existing_units


class Build(BuildingAction):
    def __init__(self, unit_id, placement=None):
        super().__init__(unit_id)
        # Use to define target point
        self.placement = placement

    def food_missing(self, food, food_required):
        return 0

    def determine_action_state(self, game_state, units_queue, upgrades_queue):
        building_stuck = len(game_state.player_units.filter(unit_type__in=[45, 18, 130, 132])) == 0
        if building_stuck:
            return Action.MISSING_DEPENDENCIES, []
        else:
            return super(Build, self).determine_action_state(game_state, units_queue, upgrades_queue)

    async def perform_action(self, ws, game_state):
        try:
            available_builders = get_available_building_unit(self.unit_id, game_state)
            if not available_builders:
                return False

            target_unit = None

            # Get ability_id
            ability_id = game_state.game_data.units[self.unit_id].ability_id or UNIT_DATA[self.unit_id]['ability_id']

            # Get target point (for now TH1)
            # TODO: Check faction
            # Find placement
            placement, target_unit = await self.find_building_placement(ability_id, game_state, target_unit, ws)

            # Select builder
            # TODO: Get closest builder
            builder = available_builders[0]

            # Send order
            if target_unit is None:
                result = await UnitManager([builder]).give_order(ws, ability_id, target_point=placement)
            else:
                result = await UnitManager([builder]).give_order(ws, ability_id, target_unit=target_unit)

            # Return result
            return result.action.result[0]
        except Exception:
            print(traceback.print_exc())
            return False

    async def find_building_placement(self, ability_id, game_state, target_unit, ws):
        placement = self.placement
        if not placement:
            th = self.get_th(game_state)
            placement = th.pos.x, th.pos.y

        if self.unit_id in [UnitTypeIds.REFINERY.value]:
            th = self.get_th(game_state)
            geysers = select_related_gas(game_state, th)
            for geyser in geysers:
                target_point = geyser.pos.x, geyser.pos.y
                placement = await find_placement(ws, ability_id, target_point)
                if placement:
                    target_unit = geyser
                    break
        else:
            placement = await find_placement(ws, ability_id, placement)
        return placement, target_unit

    def get_th(self, game_state):
        return game_state.player_units.filter(unit_type__in=[
            UnitTypeIds.COMMANDCENTER.value,
            UnitTypeIds.PLANETARYFORTRESS.value,
            UnitTypeIds.ORBITALCOMMAND.value
        ])[0]


class Expansion(Build):
    def __init__(self, point=None):
        # TODO: Check race
        unit_id = UnitTypeIds.COMMANDCENTER.value
        super().__init__(unit_id, point)

    def determine_action_state(self, game_state, units_queue, upgrades_queue):
        return super(Expansion, self).determine_action_state(game_state, units_queue, upgrades_queue)

    async def find_building_placement(self, ability_id, game_state, target_unit, ws):
        point = self._get_point(game_state)
        existing_ths_positions = self._get_existing_ths_positions(game_state)
        clusters = filter(
            lambda c: not any(map(lambda thpos: c.point_in_cluster(thpos, game_state), existing_ths_positions)),
            group_resources(game_state)
        )
        closest_cluster = min(clusters, key=lambda cluster: euclidean_distance(point, cluster.center))
        return closest_cluster.building_point(), target_unit

    def _get_existing_ths_positions(self, game_state):
        # For terran v terran
        unit_filter = {"unit_type__in": [
            UnitTypeIds.COMMANDCENTER.value,
            UnitTypeIds.ORBITALCOMMAND.value,
            UnitTypeIds.PLANETARYFORTRESS.value
        ]}
        player_positions = game_state.player_units.filter(**unit_filter).values('pos', flat_list=True)
        enemy_positions = game_state.enemy_units.filter(**unit_filter).values('pos', flat_list=True)
        built_ths = [(pos.x, pos.y) for pos in player_positions + enemy_positions]
        th_built_orders = get_ongoing_build_orders(UnitTypeIds.COMMANDCENTER.value, game_state)
        orders_positions = [(o.target_world_space_pos.x, o.target_world_space_pos.y) for o in th_built_orders]
        return built_ths + orders_positions

    def _get_point(self, game_state):
        point = self.placement
        if point is None:
            units = game_state.player_units.filter(unit_type__in=[
                UnitTypeIds.COMMANDCENTER.value,
                UnitTypeIds.ORBITALCOMMAND.value,
                UnitTypeIds.PLANETARYFORTRESS.value
            ])
            if not units:
                units = game_state.player_units.filter(movement_speed=0)
            unit_mean_x = sum([unit.pos.x for unit in units]) / float(len(units))
            unit_mean_y = sum([unit.pos.y for unit in units]) / float(len(units))
            point = (unit_mean_x, unit_mean_y)
        return point


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
    def __init__(self, ability_id, unit_group, target_point=None, target_unit=None):
        """ Generic UnitAction Action

        :param ability_id:      <int>           Ability Id
        :param unit_group:      <dict{int:int}  Unit group composition, id: amount | Ex: {MARINE: 10}
        :param target_point:    <(float, float) Coordinates in map
        :param target_unit:     <dict>          Targeted unit information
            target_unit: {
             type:                                  <int>   Unit type id,
             alignment:                             <str>   Enemy/Own/Neutral
             index: (Optional, default 0)           <int>   Index according to distance,
             action_pos: (Optional, default False)  <bool>  Determines if target unit or position of unit
                                                                (for example an attacking unit with a targeted position
                                                                will attack enemies in its path)
            }
        """

        super().__init__()
        self.ability_id = ability_id
        self.unit_group = unit_group
        self.target_point = target_point
        self.target_unit = target_unit

    def food_missing(self, food, food_required):
        return 0

    def get_target_data(self, game_state):
        target = {}
        if self.target_unit:
            targeted_unit = self.filter_target_unit(game_state)

            if self.target_unit.get("action_pos"):
                target['target_point'] = (targeted_unit.pos.x, targeted_unit.pos.y)
            else:
                target['target_unit'] = targeted_unit

        elif self.target_point:
            target['target_point'] = (self.target_point[0], self.target_point[1])

        return target

    def filter_target_unit(self, game_state):
        # Get targeted unit data
        unit_ids = self.target_unit.get("ids")
        unit_types = self.target_unit.get("types")
        index = self.target_unit.get("index", 0)
        alignment = self.target_unit.get("alignment")

        # Select set
        if alignment == "enemy":
            selected_set = game_state.enemy_units
        elif alignment == "own":
            selected_set = game_state.player_units
        else:
            selected_set = game_state.neutral_units

        # TODO: Add distance to starting point
        if unit_ids:
            filtered_units = selected_set.filter(tag__in=unit_ids)
            if not filtered_units:
                raise UnitDestroyed()
        else:
            filtered_units = selected_set.filter(unit_type__in=unit_types)
        return filtered_units[index]

    def get_action_units(self, game_state, target):
        distance_args = None
        if target.get('target_unit'):
            distance_args = {"unit": target.get('target_unit')}
        elif target.get('target_point'):
            distance_args = {"pos": target.get('target_point')}

        # Get units performing the action
        base_manager = UnitManager([])

        composition = self.unit_group.get('composition')
        query_params = self.unit_group.get('query')

        if query_params:
            base_manager = game_state.player_units.filter(**query_params)
            if distance_args:
                base_manager = base_manager.add_calculated_values(distance_to=distance_args)

        elif composition:
            base_manager = self.prepare_unit_composition(composition, distance_args, game_state)

        return base_manager

    def prepare_unit_composition(self, composition, distance_args, game_state):
        base_manager = UnitManager([])
        for unit_type, amount in composition.items():
            units = game_state.player_units.filter(unit_type=unit_type)
            if distance_args:
                units = units.add_calculated_values(distance_to=distance_args)
            base_manager += units[:amount]
        return base_manager

    def return_units_required(self, game_state, existing_units):
        composition = self.unit_group.get('composition')
        query_params = self.unit_group.get('query')

        if query_params:
            return {}
        elif composition:
            required_units = {}
            for unit_type, amount in composition.items():
                existing = len(game_state.player_units.filter(unit_type=unit_type, build_progress=1))
                missing = amount - existing
                if missing > 0:
                    required_units[unit_type] = missing
            return required_units
        else:
            return {}

    def return_upgrades_required(self, existing_upgrades):
        return return_current_ability_dependencies(self.ability_id, existing_upgrades)

    async def perform_action(self, ws, game_state):
        try:
            target = self.get_target_data(game_state)
            troops = self.get_action_units(game_state, target)

            if troops:
                # Send order
                result = await troops.give_order(ws, self.ability_id, **target)
                return result.action.result[0]
            else:
                # No units to perform action, return failure
                return False
        except UnitDestroyed:
            return 1
        except Exception as e:
            return False


class Move(UnitAction):
    def __init__(self, unit_group, target_point=None, target_unit=None):
        super().__init__(AbilityId.MOVE.value, unit_group, target_point, target_unit)


class Attack(UnitAction):
    def __init__(self, unit_group, target_point=None, target_unit=None):
        if target_unit is not None and not target_unit.get('action_pos'):
            super().__init__(AbilityId.ATTACK_ATTACK.value, unit_group, target_point, target_unit)
        else:
            super().__init__(AbilityId.ATTACK.value, unit_group, target_point, target_unit)


class Harvest(UnitAction):
    MINERAL = "mineral"
    VESPENE = "vespene"

    def __init__(self, workers, harvest_type, town_hall_idx=0):
        super().__init__(AbilityId.HARVEST_GATHER_SCV.value, workers)
        self.harvest_type = harvest_type
        self.town_hall_idx = town_hall_idx
        self.town_hall = None
        self.ideal_workers = None
        self.assigned_workers = None

    def get_units_ready_for_action(self, game_state):
        # Return created IDLE workers
        return game_state.player_units.filter(
            build_progress=1
        ).add_calculated_values(
            unit_availability={},
        ).filter(
            last_unit_availability__in=[0]
        )

    def get_target_data(self, game_state):
        # TODO: Check faction
        try:
            self.town_hall = game_state.player_units.filter(unit_type__in=[
                UnitTypeIds.COMMANDCENTER.value,
                UnitTypeIds.ORBITALCOMMAND.value,
                UnitTypeIds.PLANETARYFORTRESS.value
            ])[self.town_hall_idx]
        except KeyError:
            self.town_hall = None
            return {'target_unit': None}

        related_resource = None
        if self.harvest_type == self.MINERAL:
            try:
                related_resource = select_related_minerals(game_state, self.town_hall)[0]
            except KeyError:
                pass
            self.assigned_workers = self.town_hall.assigned_harvesters
            self.ideal_workers = self.town_hall.ideal_harvesters
        elif self.harvest_type == self.VESPENE:
            related_resource = None
            related_refineries = select_related_refineries(game_state, self.town_hall)

            # Select the refinery with less workers
            for refinery in related_refineries:
                if related_resource is None or related_resource.assigned_harvesters > refinery.assigned_harvesters:
                    related_resource = refinery

            if related_resource:
                self.assigned_workers = related_resource.assigned_harvesters
                self.ideal_workers = related_resource.ideal_harvesters
        return {'target_unit': related_resource}

    def get_action_units(self, game_state, target):
        target_unit = target.get('target_unit')
        missing_workers = self.ideal_workers - self.assigned_workers

        # If target unit is None or no workers required, return empty list of workers
        if target_unit is None or missing_workers <= 0:
            return []

        workers = UnitManager([])

        composition = self.unit_group.get('composition')
        query_params = self.unit_group.get('query')

        if query_params:
            type_workers = game_state.player_units.filter(**query_params).add_calculated_values(
                distance_to={"unit": target_unit},
                unit_availability={},
            ).sort_by('last_unit_availability', 'last_distance_to')

            assignable_workers = missing_workers
            workers += type_workers[:assignable_workers]
            missing_workers -= assignable_workers

        elif composition:
            for worker_type, worker_amount in composition.items():
                type_workers = game_state.player_units.filter(
                    unit_type=worker_type
                ).add_calculated_values(
                    distance_to={"unit": target_unit},
                    unit_availability={},
                ).sort_by('last_unit_availability', 'last_distance_to')

                assignable_workers = min(missing_workers, worker_amount)
                workers += type_workers[:assignable_workers]
                missing_workers -= assignable_workers

        return workers


class DistributeHarvest(UnitAction):
    def __init__(self, unit_group):
        super().__init__(AbilityId.HARVEST_GATHER_SCV.value, unit_group)

    async def perform_action(self, ws, game_state):
        try:
            workers = game_state.player_units.filter(**self.unit_group.get('query'))
            resources_missing_workers = self.get_resources_missing_workers(game_state)
            worker_distribution = self.distribute_workers_throughout_resources(workers, resources_missing_workers)

            # Send orders
            for resource, worker_group in worker_distribution.items():
                await worker_group.give_order(ws, self.ability_id, target_unit=resource)

            # Don't mind missing a resource distribution
            return 1
        except:
            print(traceback.print_exc())

    def get_resources_missing_workers(
            self, game_state: DecodedObservation,
    ) -> List[Tuple[Unit, int]]:
        mineral_harvesting_hubs = game_state.player_units.filter(unit_type__in=[
            UnitTypeIds.COMMANDCENTER.value,
            UnitTypeIds.PLANETARYFORTRESS.value,
            UnitTypeIds.ORBITALCOMMAND.value,
        ])
        vespene_harvesting_hubs = game_state.player_units.filter(unit_type__in=[UnitTypeIds.REFINERY.value])
        minerals = self._prepare_hub_info(game_state, mineral_harvesting_hubs)
        vespene = self._prepare_hub_info(game_state, vespene_harvesting_hubs)
        if game_state.player_info.minerals < game_state.player_info.vespene:
            return minerals + vespene
        else:
            return vespene + minerals

    def _prepare_hub_info(self, game_state: DecodedObservation, harvesting_hubs: UnitManager) -> List[Tuple[Unit, int]]:
        hubs_and_missing_workers = [(hub, hub.ideal_harvesters - hub.assigned_harvesters) for hub in harvesting_hubs]
        hubs_missing_workers = filter(lambda t: t[1] > 0, hubs_and_missing_workers)
        resources_missing_workers = [(self._get_target_resource(hub, game_state), m) for hub, m in hubs_missing_workers]
        resources_missing_workers = filter(lambda t: t[0] is not None, resources_missing_workers)
        return sorted(resources_missing_workers, key=lambda t: t[1], reverse=True)

    def _get_target_resource(self, hub: Unit, game_state: DecodedObservation) -> Union[Unit, None]:
        if hub.unit_type == UnitTypeIds.REFINERY.value:
            return hub
        related_resources = select_related_minerals(game_state, hub)
        if related_resources:
            return related_resources[0]

    def distribute_workers_throughout_resources(
            self,
            workers: UnitManager,
            resources_missing_workers: List[Tuple[Unit, int]],
    ) -> Dict[Unit, UnitManager]:
        worker_distribution = {}
        taken_workers = []
        for resource, missing_workers in resources_missing_workers:
            # Filter workers to take
            workers = workers.filter(
                mode=UnitManager.EXCLUDE_AND_MODE, tag__in=taken_workers
            ).add_calculated_values(distance_to={'unit': resource}).sort_by('last_distance_to')

            # Take workers
            workers_to_resource = workers[:missing_workers]
            worker_distribution[resource] = workers_to_resource
            taken_workers = workers_to_resource.values('tag', flat_list=True)
        return worker_distribution


class Upgrade(UnitAction):
    def __init__(self, upgrade_id):
        upgrade_data = UPGRADE_DATA[upgrade_id]
        upgrade_unit = get_upgrading_building(upgrade_id)
        super().__init__(upgrade_data['ability_id'], {"composition": {upgrade_unit: 1}})
        self.upgrade_id = upgrade_id

    def return_upgrades_required(self, existing_upgrades):
        return return_missing_parent_upgrades(self.upgrade_id, existing_upgrades)

    def return_resources_required(self, game_data):
        mineral_cost = UPGRADE_DATA[self.upgrade_id]['mineral_cost']
        vespene_cost = UPGRADE_DATA[self.upgrade_id]['vespene_cost']
        return mineral_cost, vespene_cost, 0


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
            return []

        # Current state summary
        actions_and_dependencies = []

        # Iterate over current actions
        for action in self.actions_queue:

            # Get action state
            action_state, required_actions = action.determine_action_state(
                game_state,
                [action.unit_id for action, _ in actions_and_dependencies if isinstance(action, BuildingAction)],
                [action.upgrade_id for action, _ in actions_and_dependencies if isinstance(action, Upgrade)],
            )

            # If action ready reduce resources to proceed with action
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
                if success != 1:
                    if action.fail_counter < 5:
                        action.fail_counter += 1
                        remaining_actions.append(action)
                    else:
                        print("{} failed several times in-game discarded".format(action))
                else:
                    print("{} executed".format(action))
            else:
                remaining_actions.append(action)
        return remaining_actions

    async def process_step(self, ws, game_state, raw=None, actions=None):
        new_actions = self.get_required_actions(game_state)
        self.actions_queue = await self.perform_ready_actions(ws, new_actions, game_state)
        print(new_actions)
        print("{} actions in queue".format(len(new_actions)))
        print("Supplies Log -------------------------")
        print("Food {}/{}".format(game_state.player_info.food_used, game_state.player_info.food_cap))
        print("Minerals {} - Harvesting: {}".format(game_state.player_info.minerals, ", ".join(mineral_stats(game_state))))
        print("Vespene {} - Harvesting: {}".format(game_state.player_info.vespene, ", ".join(vespene_stats(game_state))))
        print("Workers (idle/total) {}/{}".format(*idle_workers(game_state)))
        print("Worker tasks:")
        tasks = worker_tasks(game_state)
        for order, count in tasks.items():
            print("\tAbility {}: {}".format(order, count))
        print("--------------------------------------")


def mineral_stats(game_state):
    return ["TH {} - {}/{}".format(th.tag, th.assigned_harvesters, th.ideal_harvesters)
            for th in game_state.player_units.filter(unit_type__in=[18, 130, 132]).sort_by('tag')]


def vespene_stats(game_state):
    return ["Refinery {} - {}/{}".format(refinery.tag, refinery.assigned_harvesters, refinery.ideal_harvesters)
            for refinery in game_state.player_units.filter(unit_type=20).sort_by('tag')]


def idle_workers(game_state):
    workers = game_state.player_units.filter(unit_type=45)
    return len(workers.filter(orders__attlength=0)), len(workers)


def worker_tasks(game_state):
    orders = game_state.player_units.filter(unit_type=45).values('orders', flat_list=True)
    orders = [o.ability_id for o in itertools.chain(*orders)]
    orders_h = {}
    for o in orders:
        orders_h[o] = orders_h.get(o, 0) + 1
    return orders_h

DEMO_ACTIONS = [Train(UnitTypeIds.MARAUDER.value, 10)]
DEMO_ACTIONS_2 = [Train(UnitTypeIds.MARINE.value, 1) for _ in range(3)]
DEMO_ACTIONS_3 = [Train(UnitTypeIds.MARAUDER.value, 1)] + [Train(UnitTypeIds.MARINE.value, 1) for _ in range(200)]
DEMO_ACTIONS_4 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                 [Build(UnitTypeIds.BARRACKS.value) for _ in range(2)] + \
                 [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)] + \
                 [Train(UnitTypeIds.MARAUDER.value, 1) for _ in range(5)] + \
                 [Train(UnitTypeIds.HELLION.value, 1) for _ in range(2)] + \
                 [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(2)]
DEMO_ACTIONS_5 = [Train(UnitTypeIds.BATTLECRUISER.value, 1)]
DEMO_ACTIONS_6 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                 [Build(UnitTypeIds.BARRACKS.value) for _ in range(2)] + \
                 [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)] + \
                 [Train(UnitTypeIds.MARAUDER.value, 1) for _ in range(5)] + \
                 [Train(UnitTypeIds.HELLION.value, 1) for _ in range(2)] + \
                 [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(2)] + \
                 [Train(UnitTypeIds.BATTLECRUISER.value, 2)]
DEMO_ACTIONS_7 = [Attack({"composition": {UnitTypeIds.MARINE.value: 10}},
                         target_unit={"types": [UnitTypeIds.HATCHERY.value],
                                      "alignment": "enemy",
                                      "action_pos": True
                                      })
                  ]
DEMO_ACTIONS_8 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                 [Build(UnitTypeIds.BARRACKS.value) for _ in range(2)] + \
                 [Build(UnitTypeIds.REFINERY.value) for _ in range(2)] + \
                 [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)] + \
                 [Harvest({UnitTypeIds.SCV.value: 3}, Harvest.VESPENE)] + \
                 [Train(UnitTypeIds.MARAUDER.value, 1) for _ in range(5)] + \
                 [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(2)] + \
                 [Attack({"composition": {UnitTypeIds.BATTLECRUISER.value: 1}},
                         target_unit={"types": [UnitTypeIds.HATCHERY.value],
                                      "alignment": "enemy",
                                      "action_pos": True
                                      })
                  ]
DEMO_ACTIONS_9 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                 [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)] + \
                 [Harvest({"composition": {UnitTypeIds.SCV.value: 3}}, Harvest.VESPENE)] + \
                 [Upgrade(UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value)] + \
                 [UnitAction(
                     ability_id=AbilityId.EFFECT_STIM_MARINE.value,
                     unit_group={"composition": {UnitTypeIds.MARINE.value: 5}}
                 )]
