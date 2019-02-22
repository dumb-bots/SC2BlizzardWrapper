import math
import itertools

import s2clientprotocol.common_pb2 as common
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.query_pb2 as api_query

from constants.ability_dependencies import ABILITY_DEPENDENCIES
from constants.ability_ids import AbilityId
from constants.unit_dependencies import UNIT_DEPENDENCIES
from constants.unit_type_ids import UnitTypeIds
from constants.upgrade_dependencies import UPGRADE_DEPENDENCIES
from functools import reduce
import math
from constants.upgrade_data import UPGRADE_DATA
from constants.unit_data import UNIT_DATA
QUADRANT_WIDTH = 33.5
QUADRANT_HEIGHT = 35.5
VESPENE_TO_MINERALS = 3.45
SUPPLY_TO_MINERALS = 12.5

HARVESTING_ORDERS = [
    # SCV
    AbilityId.HARVEST_GATHER_SCV.value,
    AbilityId.HARVEST_RETURN_SCV.value,
    AbilityId.SCVHARVEST_2.value,
    # Probes
    AbilityId.HARVEST_GATHER_PROBE.value,
    AbilityId.HARVEST_RETURN_PROBE.value,
    AbilityId.PROBEHARVEST_2.value,
    # Drones
    AbilityId.HARVEST_GATHER_DRONE.value,
    AbilityId.HARVEST_RETURN_DRONE.value,
    AbilityId.DRONEHARVEST_2.value,
    # Generic
    AbilityId.HARVEST_GATHER.value,
    AbilityId.HARVEST_RETURN.value,
]

FLYING_BUILDINGS = {
    UnitTypeIds.COMMANDCENTERFLYING.value,
    UnitTypeIds.FACTORYFLYING.value,
    UnitTypeIds.STARPORTFLYING.value,
    UnitTypeIds.BARRACKSFLYING.value,
    UnitTypeIds.ORBITALCOMMANDFLYING.value,
}

BUILDERS = {UnitTypeIds.SCV.value}

TOWN_HALLS = {
    UnitTypeIds.COMMANDCENTER.value,
    UnitTypeIds.ORBITALCOMMAND.value,
    UnitTypeIds.PLANETARYFORTRESS.value,
}

TECH_LAB_IDS = [
    unit_type.value for unit_type in UnitTypeIds if "TECHLAB" in unit_type.name
]
REACTORS_ID = [
    unit_type.value for unit_type in UnitTypeIds if "REACTOR" in unit_type.name
]
GEYSER_IDS = [
    unit_type.value for unit_type in UnitTypeIds if "GEYSER" in unit_type.name
]

MINERAL_FIELD_IDS = [
    unit_type.value for unit_type in UnitTypeIds if "MINERALFIELD" in unit_type.name
]

ADDON_BUILDINGS = [
    UnitTypeIds.BARRACKSTECHLAB.value, UnitTypeIds.BARRACKSREACTOR.value,
    UnitTypeIds.FACTORYTECHLAB.value, UnitTypeIds.FACTORYREACTOR.value,
    UnitTypeIds.STARPORTTECHLAB.value, UnitTypeIds.STARPORTREACTOR.value,
]


def get_building_unit(unit_id):
    building_unit_types = set()
    addon_types = set()

    dependency_list = UNIT_DEPENDENCIES.get(unit_id, [])

    # Check buildings in dependency list
    for dependencies in dependency_list:
        build_unit = dependencies[-1]
        if is_addon(build_unit):
            addon_types.add(build_unit)
        else:
            building_unit_types.add(build_unit)

    return building_unit_types, addon_types


def get_available_builders(unit_id, game_state):
    building_unit_types, addon_types = get_building_unit(unit_id)
    available_builders = game_state.player_units.filter(
        unit_type__in=building_unit_types, build_progress=1
    )
    if unit_id in ADDON_BUILDINGS:
        available_builders = available_builders.filter(add_on_tag=0)
    if addon_types:
        addon_tags = game_state.player_units.filter(
            unit_type__in=addon_types, build_progress=1
        ).values("tag", flat_list=True)
        addon_buildings = game_state.player_units.filter(add_on_tag__in=addon_tags)
        available_builders += addon_buildings

    return available_builders


def get_available_building_unit(unit_id, game_state):
    idle_builders = []
    available_builders = get_available_builders(unit_id, game_state)

    # Get idle builders
    for builder in available_builders:
        if not builder.orders:
            idle_builders.append(builder)
            return [builder]
        order_abilities = [order.ability_id for order in builder.orders]
        if set(order_abilities) & set(HARVESTING_ORDERS):
            idle_builders.append(builder)

    return idle_builders


def is_addon(unit_type):
    tech_labs = TECH_LAB_IDS
    reactors = REACTORS_ID
    addons = tech_labs + reactors
    if unit_type in addons:
        return True
    else:
        return False


async def find_placement(
    ws, ability_id, target_point, circles=6, circle_distance=3, min_distance=3
):
    for circle in range(1, circles + 1):
        distance = (circle * circle_distance) + min_distance
        options = [
            (target_point[0], target_point[1]),
            (target_point[0] + distance, target_point[1] + distance),
            (target_point[0] + distance, target_point[1]),
            (target_point[0] + distance, target_point[1] - distance),
            (target_point[0] - distance, target_point[1] + distance),
            (target_point[0] - distance, target_point[1]),
            (target_point[0] - distance, target_point[1] - distance),
            (target_point[0], target_point[1] + distance),
            (target_point[0], target_point[1] - distance),
        ]
        for point in options:
            can_place = await query_building_placement(ws, ability_id, point)
            if can_place:
                return point


async def query_building_placement(ws, ability_id, point):
    if not isinstance(point, common.Point2D):
        point = common.Point2D(x=point[0], y=point[1])
    api_request = api.Request(
        query=api_query.RequestQuery(
            placements=[
                api_query.RequestQueryBuildingPlacement(
                    ability_id=ability_id, target_pos=point
                )
            ]
        )
    )
    await ws.send(api_request.SerializeToString())
    result = await ws.recv()
    response = api.Response.FromString(result)
    return response.query.placements[0].result == 1


def get_upgrading_building(upgrade_id):
    dependency_list = UPGRADE_DEPENDENCIES.get(upgrade_id, {})

    # Check buildings in dependency list
    return dependency_list.get("buildings", [])[-1]


def get_available_upgrade_buildings(game_state, upgrade):
    unit_type = get_upgrading_building(upgrade)
    return game_state.player_units.filter(unit_type=unit_type, build_progress=1)


def select_related_minerals(game_state, town_hall):
    neutral = game_state.neutral_units.filter(
        unit_type__in=MINERAL_FIELD_IDS
    ).add_calculated_values(distance_to={"unit": town_hall})
    return neutral.filter(last_distance_to__lte=25).sort_by("last_distance_to")


def select_related_gas(game_state, town_hall):
    vespene_geyser_ids = GEYSER_IDS
    neutral = game_state.neutral_units.filter(
        unit_type__in=vespene_geyser_ids
    ).add_calculated_values(distance_to={"unit": town_hall})
    return neutral.filter(last_distance_to__lte=25).sort_by("last_distance_to")


def select_related_refineries(game_state, town_hall):
    refinery_ids = [
        UnitTypeIds.REFINERY.value,
        UnitTypeIds.ASSIMILATOR.value,
        UnitTypeIds.EXTRACTOR.value,
    ]
    refineries = game_state.player_units.filter(
        unit_type__in=refinery_ids
    ).add_calculated_values(distance_to={"unit": town_hall})
    return refineries.filter(last_distance_to__lte=25).sort_by("last_distance_to")


def return_current_unit_dependencies(unit_id, existing_units=(UnitTypeIds.SCV.value,)):
    # If unit already exists, no need to check for dependencies
    if unit_id in existing_units:
        return []

    # Safeguard to avoid recursion when no builders nor town halls exist
    if not (BUILDERS & set(existing_units)) and not (TOWN_HALLS & set(existing_units)):
        return []

    # Getting the shortest path, invalid dependency by default
    selected_dependencies = None
    try:
        for unit_dependencies in UNIT_DEPENDENCIES[unit_id]:
            dependencies = [
                dependency
                for dependency in unit_dependencies
                if dependency not in existing_units
            ]
            if set(dependencies) & FLYING_BUILDINGS:
                continue

            for unit_dependency in unit_dependencies:
                # Engineering bay recursion control
                if unit_id == UnitTypeIds.ENGINEERINGBAY.value and unit_dependency == UnitTypeIds.ORBITALCOMMAND.value:
                    if UnitTypeIds.ORBITALCOMMAND.value in existing_units:
                        return []
                    elif UnitTypeIds.ENGINEERINGBAY.value not in existing_units:
                        continue

                if unit_id == UnitTypeIds.ENGINEERINGBAY.value and unit_dependency == UnitTypeIds.PLANETARYFORTRESS.value:
                    if UnitTypeIds.PLANETARYFORTRESS.value in existing_units:
                        return []
                    elif UnitTypeIds.ENGINEERINGBAY.value not in existing_units:
                        continue

                additional_dependencies = return_current_unit_dependencies(
                    unit_dependency, existing_units
                )
                if not additional_dependencies:
                    continue

                dependencies = [
                    dependency
                    for dependency in additional_dependencies
                    if dependency not in existing_units
                ] + dependencies

            # If one path completed, return empty requirements
            if not dependencies and dependencies is not None:
                return []

            if selected_dependencies is None or (
                dependencies is not None
                and len(dependencies) < len(selected_dependencies)
            ):
                selected_dependencies = dependencies

    # If unit cannot be constructed (has no building dependencies) return None (invalid dependency)
    except KeyError:
        return None
    return selected_dependencies


def return_current_ability_dependencies(ability_id, existing_upgrades=set()):
    if ability_id in existing_upgrades:
        return []
    upgrade_required = ABILITY_DEPENDENCIES.get(ability_id, None)
    if upgrade_required and upgrade_required not in existing_upgrades:
        parent_upgrades = return_missing_parent_upgrades(
            upgrade_required, existing_upgrades
        )
        return parent_upgrades + [upgrade_required]
    else:
        return []


def return_missing_parent_upgrades(upgrade, existing_upgrades):
    upgrade_dependencies = UPGRADE_DEPENDENCIES.get(upgrade, {})
    parent = upgrade_dependencies.get("upgrade")
    if parent is None or parent in existing_upgrades:
        return []
    return return_missing_parent_upgrades(parent, existing_upgrades) + [parent]


def return_upgrade_building_requirements(
    upgrade, existing_units=(UnitTypeIds.SCV.value, UnitTypeIds.COMMANDCENTER.value)
):
    units_required = []
    upgrade_dependencies = UPGRADE_DEPENDENCIES.get(upgrade, {})
    unit_dependencies = upgrade_dependencies.get("buildings")
    new_existing_units = list(existing_units)
    for unit in unit_dependencies:
        units_required += return_current_unit_dependencies(unit, new_existing_units)
        units_required.append(unit)
        new_existing_units += units_required
    return units_required


def get_closing_enemies(game_state):
    from game_data.units import UnitManager

    town_halls = game_state.player_units.filter(unit_type__in=[
        UnitTypeIds.COMMANDCENTER.value,
        UnitTypeIds.ORBITALCOMMAND.value,
        UnitTypeIds.PLANETARYFORTRESS.value,
    ])
    min_distance = 30
    dangerous_units = UnitManager([])
    for th in town_halls:
        e_units = game_state.enemy_units \
            .add_calculated_values(distance_to={"unit": th}) \
            .filter(last_distance_to__lte=min_distance)
        dangerous_units += e_units
    return dangerous_units.values('tag', flat_list=True)


class ResourceCluster:
    DISTANCE_THRESHOLD = 16

    def __init__(self, initial_resource, game_state):
        self._geysers = []
        self._mineral_fields = []
        self.center = (initial_resource.pos.x, initial_resource.pos.y)
        self.height = game_state.terrain_height(self.center)
        self.add_unit(initial_resource)

    def __repr__(self):
        return '<Cluster {} {}: {}m {}g>'.format(
            self.center, self.height, len(self._mineral_fields), len(self._geysers)
        )

    @property
    def mineral_fields(self):
        from game_data.units import UnitManager
        return UnitManager(self._mineral_fields)

    @property
    def geysers(self):
        from game_data.units import UnitManager
        return UnitManager(self._geysers)

    def unit_in_cluster(self, resource_unit, game_state):
        unit_height = game_state.terrain_height((resource_unit.pos.x, resource_unit.pos.y))
        in_range = resource_unit.distance_to(pos=self.center) < ResourceCluster.DISTANCE_THRESHOLD
        in_height = unit_height == self.height
        return in_range and in_height

    def add_mineral_field(self, mineral_field):
        self._mineral_fields.append(mineral_field)

    def add_geyser(self, geyser):
        self._geysers.append(geyser)

    def add_unit(self, unit):
        if unit.unit_type in MINERAL_FIELD_IDS:
            self.add_mineral_field(unit)
        elif unit.unit_type in GEYSER_IDS:
            self.add_geyser(unit)

    def building_point(self):
        possible_points = self._get_possible_points()
        restricted_points = self._restrict_point_distance(possible_points)
        return min(
            restricted_points,
            key=lambda p: sum(self._distances_to_minerals(p)) + sum(self._distances_to_geysers(p))
        )

    def _get_possible_points(self):
        offset_square_side = 10
        low_limit = - offset_square_side
        top_limit = offset_square_side + 1
        offsets = list(itertools.product(list(range(low_limit, top_limit)), list(range(low_limit, top_limit))))
        points = map(lambda o: (
            self.geysers[0].pos.x + o[0],
            self.geysers[0].pos.y + o[1]
        ), offsets)
        return points

    def _restrict_point_distance(self, points):
        return filter(self._point_in_valid_area, points)

    def _point_in_valid_area(self, point):
        min_distance_to_minerals = 6
        min_distance_to_geysers = 7
        too_close_to_minerals = any(map(lambda d: d < min_distance_to_minerals, self._distances_to_minerals(point)))
        too_close_to_geysers = any(map(lambda d: d < min_distance_to_geysers, self._distances_to_geysers(point)))
        return not too_close_to_minerals and not too_close_to_geysers

    def _distances_to_minerals(self, point):
        return self.mineral_fields.add_calculated_values(
            distance_to={"pos": point}
        ).values('last_distance_to', flat_list=True)

    def _distances_to_geysers(self, point):
        return self.geysers.add_calculated_values(
            distance_to={"pos": point}
        ).values('last_distance_to', flat_list=True)


def group_resources(game_state):
    resources = game_state.neutral_units.filter(unit_type__in=MINERAL_FIELD_IDS + GEYSER_IDS)
    clusters = []
    for resource in resources:
        in_cluster = False
        for cluster in clusters:
            if cluster.unit_in_cluster(resource, game_state):
                cluster.add_unit(resource)
                in_cluster = True
                break
        if not in_cluster:
            clusters.append(ResourceCluster(resource, game_state))
    return clusters

def situation_case_to_cluster_x(game_info, x,nx):
    MAP_X = game_info["terrainHeight"]["size"]["x"]
    PLAYABLE_X1 = game_info["playableArea"]["p0"]["x"]
    PLAYABLE_X2 = game_info["playableArea"]["p1"]["x"]
    X_RESOLUTION = abs(PLAYABLE_X2 - PLAYABLE_X1) / float(nx)
    new_x = math.floor((x - PLAYABLE_X1) / X_RESOLUTION)
    cx = PLAYABLE_X1 + (new_x * X_RESOLUTION) + (X_RESOLUTION / float(2))
    return cx

def situation_case_to_cluster_y(game_info, y,ny):
    MAP_Y = game_info["terrainHeight"]["size"]["y"]
    PLAYABLE_Y1 = game_info["playableArea"]["p0"]["y"]
    PLAYABLE_Y2 = game_info["playableArea"]["p1"]["y"]
    Y_RESOLUTION = abs(PLAYABLE_Y2 - PLAYABLE_Y1) / float(ny)
    new_y = math.floor((y - PLAYABLE_Y1) / Y_RESOLUTION)
    cy = PLAYABLE_Y1 + (new_y * Y_RESOLUTION) + (Y_RESOLUTION / float(2))
    return cy

def obs_to_case(obs, game_info):
    resumed_units = []
    units = obs.get("observation", {}).get("observation",{}).get("rawData", {}).get("units", [])
    for unit in units:
        if unit["alliance"] != "Neutral":
            resumed_units.append(
                {
                    "type": unit.get("unitType",0),
                    "alliance": unit["alliance"],
                    "position": {
                        "x": situation_case_to_cluster_x(game_info, unit["pos"]["x"], 4),
                        "y": situation_case_to_cluster_y(game_info, unit["pos"]["y"], 5),
                    },
                }
            )
    resumed_units = sorted(resumed_units, key= lambda k : (k["type"], k["position"]["x"], k["position"]["y"], k["alliance"]))
    observation = obs["observation"]["observation"]["playerCommon"]
    observation.pop("foodArmy")
    observation.pop("foodWorkers")
    observation.pop("warpGateCount")
    observation.pop("armyCount")
    observation.pop("idleWorkerCount")
    observation["minerals"] = round(observation["minerals"] / float(100))
    observation["vespene"] = round(observation["vespene"] / float(100))
    observation["food"] = observation["foodCap"] - observation["foodUsed"]
    observation.pop("foodCap")
    observation.pop("foodUsed")
    observation["loop"] = round(obs["observation"]["observation"]["gameLoop"] / float(240)) * 240
    observation["upgrades"] = obs["observation"]["observation"]["rawData"]["player"].get("upgradeIds",[])
    observation["upgrades"] = sorted(observation["upgrades"])
    observation["units"] = resumed_units
    observation["startingPoints"] = game_info["startLocations"]
    return observation

def obs_to_case_replay(obs, replay_info, game_info, units_by_tag):
    actions = obs.get("observation",{}).get("actions", [])
    obs = obs_to_case(obs, game_info)
    resumed_actions = []
    p_id = int(obs["playerId"]) - 1
    result = replay_info["results"][p_id]
    for action in actions:
        action = action.get("actionRaw",None)
        if action:
            resumed_action = {}
            if "unitCommand" in action.keys():
                action = action["unitCommand"]
                resumed_action = {
                    "id": action["abilityId"],
                    "units": list(reduce(lambda x, y: x + [units_by_tag[y]] if units_by_tag.get(y, None) else x,action.get("unitTags", []),[]))
                }
                resumed_action["units"] = sorted(resumed_action["units"], key= lambda k : (k["type"], k["position"]["x"], k["position"]["y"], k["alliance"]))
                if "targetWorldSpacePos" in action.keys():
                    if action["abilityId"] == 1:
                        continue
                    resumed_action["targetPoint"] = {
                        "x" : situation_case_to_cluster_x(game_info, action["targetWorldSpacePos"]["x"], 4),
                        "y" : situation_case_to_cluster_y(game_info, action["targetWorldSpacePos"]["y"], 5),
                    }
                elif "targetUnitTag" in action.keys():
                    targetUnit = units_by_tag.get(action["targetUnitTag"],None)
                    if targetUnit:
                        resumed_action["targetUnit"] = targetUnit
            elif "toggleAutocast" in action.keys():
                resumed_action = {
                    "id": action.get("abilityId", None),
                    "units": list(reduce(lambda x, y: x + [units_by_tag[y]] if units_by_tag.get(y, None) else x,action.get("unitTags", []),[]))
                }
                resumed_action["units"] = sorted(resumed_action["units"], key= lambda k : (k["type"], k["position"]["x"], k["position"]["y"], k["alliance"]))
            if resumed_action:
                resumed_action["games"] = 1
                resumed_action["wins"] = 1 if result  == 1 else 0
                resumed_action["looses"] = 0 if result  == 1 else 1
                resumed_actions.append(resumed_action)
    if not actions:
        resumed_actions = [{
            "id": "idle",
            "games": 1,
            "wins": 1 if result  == 1 else 0,
            "looses": 0 if result  == 1 else 1
        }]
    return {
        "observation": obs,
        "actions": resumed_actions,
        "games": 1,
        "wins": 1 if result  == 1 else 0,
        "looses": 0 if result  == 1 else 1
    }


def units_by_tag(obs, game_info):
    by_tag = {}
    units =  obs.get("observation", {}).get("observation",{}).get("rawData", {}).get("units", [])
    for unit in units:
        if unit.get("tag",None):
            by_tag[unit["tag"]] = {
                "type": unit.get("unitType",None),
                "alliance": unit["alliance"],
                "position":
                {
                    "x": situation_case_to_cluster_x(game_info, unit["pos"]["x"], 4),
                    "y": situation_case_to_cluster_y(game_info, unit["pos"]["y"], 5),
                }
            }
    return by_tag


def get_quadrant_center(x, y):
    return (
        x * QUADRANT_WIDTH + QUADRANT_WIDTH / 2.,
        y * QUADRANT_HEIGHT + QUADRANT_HEIGHT / 2.,
    )


def get_unit_quadrant(unit):
    return math.floor(unit.pos.x / QUADRANT_WIDTH), math.floor(unit.pos.y / QUADRANT_HEIGHT)

def get_situation_minerals(situation, game_data):
    minerals = situation["minerals"] * 100
    minerals += situation["vespene"] * VESPENE_TO_MINERALS * 100
    minerals += situation["food"] * SUPPLY_TO_MINERALS
    for upgrade in situation["upgrades"]:
        minerals += UPGRADE_DATA[upgrade]["mineral_cost"]
        minerals += UPGRADE_DATA[upgrade]["vespene_cost"] * VESPENE_TO_MINERALS
    for unit in situation["units"]:
        for unit_data in game_data.units:
            if unit["alliance"] == "Self" and unit["type"] == unit_data.unit_id:
                minerals += unit_data.mineral_cost
                minerals += unit_data.vespene_cost * VESPENE_TO_MINERALS
                minerals += unit_data.food_required * SUPPLY_TO_MINERALS    
    return minerals

def own_minerals_distance(case, situation, game_data):
    return abs(get_situation_minerals(case, game_data), get_situation_minerals(situation, game_data))
