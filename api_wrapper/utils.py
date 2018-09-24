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


def get_available_building_unit(unit_id, game_state):
    idle_builders = []

    dependency_list = UNIT_DEPENDENCIES[unit_id]
    building_unit_types = set()
    for dependencies in dependency_list:
        building_unit_types.add(dependencies[-1])
    available_builders = game_state.player_units.filter(unit_type__in=building_unit_types, build_progress=1)
    for builder in available_builders:
        if not builder.orders:
            idle_builders.append(builder)
            return [builder]
        order_abilities = [order.ability_id for order in builder.orders]
        if set(order_abilities) & set(HARVESTING_ORDERS):
            idle_builders.append(builder)

    return idle_builders


async def find_placement(ws, ability_id, target_point, circles=6, circle_distance=4):
    for circle in range(1, circles + 1):
        distance = circle * circle_distance
        options = [(target_point[0], target_point[1]),
                   (target_point[0] + distance, target_point[1] + distance),
                   (target_point[0] + distance, target_point[1]),
                   (target_point[0] + distance, target_point[1] - distance),
                   (target_point[0] - distance, target_point[1] + distance),
                   (target_point[0] - distance, target_point[1]),
                   (target_point[0] - distance, target_point[1] - distance),
                   (target_point[0], target_point[1] + distance),
                   (target_point[0], target_point[1] - distance),]
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
    neutral = game_state.neutral_units.add_calculated_values(
        distance_to={"unit": town_hall})
    return neutral.filter(unit_type__in=mineral_field_ids, last_distance_to__lte=30)


def select_related_gas(game_state, town_hall):
    vespene_geyser_ids = [
        unit_type.value for unit_type in UnitTypeIds if "VESPENEGEYSER" in unit_type.name]
    neutral = game_state.neutral_units.add_calculated_values(
        distance_to={"unit": town_hall})
    return neutral.filter(unit_type__in=vespene_geyser_ids, last_distance_to__lte=30)
