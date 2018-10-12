import s2clientprotocol.common_pb2 as common
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.query_pb2 as api_query

from constants.ability_ids import AbilityId
from constants.unit_dependencies import UNIT_DEPENDENCIES
from constants.unit_type_ids import UnitTypeIds

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

TECH_LAB_IDS = [unit_type.value for unit_type in UnitTypeIds if "TECHLAB" in unit_type.name]
REACTORS_ID = [unit_type.value for unit_type in UnitTypeIds if "REACTOR" in unit_type.name]
GEYSER_IDS = [unit_type.value for unit_type in UnitTypeIds if "GEYSER" in unit_type.name]


def get_building_unit(unit_id):
    building_unit_types = set()
    addon_types = set()

    dependency_list = UNIT_DEPENDENCIES[unit_id]

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
    available_builders = game_state.player_units.filter(unit_type__in=building_unit_types, build_progress=1)
    if addon_types:
        addon_tags = game_state.player_units.filter(
            unit_type__in=addon_types, build_progress=1).values('tag', flat_list=True)
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


async def find_placement(ws, ability_id, target_point, circles=6, circle_distance=3, min_distance=3):
    for circle in range(1, circles + 1):
        distance = (circle * circle_distance) + min_distance
        options = [(target_point[0], target_point[1]),
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
    api_request = api.Request(query=api_query.RequestQuery(placements=[api_query.RequestQueryBuildingPlacement(
        ability_id=ability_id, target_pos=point)]))
    await ws.send(api_request.SerializeToString())
    result = await ws.recv()
    response = api.Response.FromString(result)
    return response.query.placements[0].result == 1


def select_related_minerals(game_state, town_hall):
    mineral_field_ids = [
        unit_type.value for unit_type in UnitTypeIds if "MINERALFIELD" in unit_type.name]
    neutral = game_state.neutral_units.filter(
        unit_type__in=mineral_field_ids
    ).add_calculated_values(
        distance_to={"unit": town_hall}
    )
    return neutral.filter(last_distance_to__lte=25).sort_by('last_distance_to')


def select_related_gas(game_state, town_hall):
    vespene_geyser_ids = GEYSER_IDS
    neutral = game_state.neutral_units.filter(
        unit_type__in=vespene_geyser_ids
    ).add_calculated_values(
        distance_to={"unit": town_hall}
    )
    return neutral.filter(last_distance_to__lte=25).sort_by('last_distance_to')


def select_related_refineries(game_state, town_hall):
    refinery_ids = [UnitTypeIds.REFINERY.value, UnitTypeIds.ASSIMILATOR.value, UnitTypeIds.EXTRACTOR.value]
    refineries = game_state.player_units.filter(
        unit_type__in=refinery_ids
    ).add_calculated_values(
        distance_to={"unit": town_hall}
    )
    return refineries.filter(last_distance_to__lte=25).sort_by('last_distance_to')
