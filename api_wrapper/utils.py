import s2clientprotocol.common_pb2 as common
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.query_pb2 as api_query

from constants.ability_dependencies import ABILITY_DEPENDENCIES
from constants.ability_ids import AbilityId
from constants.unit_dependencies import UNIT_DEPENDENCIES
from constants.unit_type_ids import UnitTypeIds
from constants.upgrade_dependencies import UPGRADE_DEPENDENCIES

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

BUILDERS = {
    UnitTypeIds.SCV.value,
}

TOWN_HALLS = {
    UnitTypeIds.COMMANDCENTER.value,
    UnitTypeIds.ORBITALCOMMAND.value,
    UnitTypeIds.PLANETARYFORTRESS.value,
}

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


def get_upgrading_building(upgrade_id):
    dependency_list = UPGRADE_DEPENDENCIES.get(upgrade_id, {})

    # Check buildings in dependency list
    return dependency_list.get('buildings', [])[-1]


def get_available_upgrade_buildings(game_state, upgrade):
    unit_type = get_upgrading_building(upgrade)
    return game_state.player_units.filter(unit_type=unit_type, build_progress=1)


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


def return_current_unit_dependencies(unit_id, existing_units=(UnitTypeIds.SCV.value,)):
    # If unit already exists, no need to check for dependencies
    if unit_id in existing_units:
        return []

    # Safeguard to avoid recursion when no builders nor town halls exist
    if not (BUILDERS & set(existing_units)) and not (TOWN_HALLS & set(existing_units)):
        return None

    # Getting the shortest path, invalid dependency by default
    selected_dependencies = None
    try:
        for unit_dependencies in UNIT_DEPENDENCIES[unit_id]:
            dependencies = [dependency for dependency in unit_dependencies if dependency not in existing_units]
            if set(dependencies) & FLYING_BUILDINGS:
                continue

            for unit_dependency in unit_dependencies:
                additional_dependencies = return_current_unit_dependencies(unit_dependency, existing_units)
                if not additional_dependencies:
                    continue

                dependencies = \
                    [dependency for dependency in additional_dependencies if dependency not in existing_units] + \
                    dependencies

            # If one path completed, return empty requirements
            if not dependencies and dependencies is not None:
                return []

            if selected_dependencies is None or \
                    (dependencies is not None and len(dependencies) < len(selected_dependencies)):
                selected_dependencies = dependencies

    # If unit cannot be constructed (has no building dependencies) return None (invalid dependency)
    except KeyError:
        return None
    return selected_dependencies


def return_current_ability_dependencies(ability_id, existing_upgrades=set()):
    if ability_id in existing_upgrades:
        return None
    upgrade_required = ABILITY_DEPENDENCIES.get(ability_id, None)
    if upgrade_required and upgrade_required not in existing_upgrades:
        parent_upgrades = return_missing_parent_upgrades(upgrade_required, existing_upgrades)
        return parent_upgrades + [upgrade_required]
    else:
        return []


def return_missing_parent_upgrades(upgrade, existing_upgrades):
    upgrade_dependencies = UPGRADE_DEPENDENCIES.get(upgrade, {})
    parent = upgrade_dependencies.get('upgrade')
    if parent is None or parent in existing_upgrades:
        return []
    return return_missing_parent_upgrades(parent, existing_upgrades) + [parent]


def return_upgrade_building_requirements(
        upgrade,
        existing_units=(UnitTypeIds.SCV.value, UnitTypeIds.COMMANDCENTER.value)
):
    units_required = []
    upgrade_dependencies = UPGRADE_DEPENDENCIES.get(upgrade, {})
    unit_dependencies = upgrade_dependencies.get('buildings')
    new_existing_units = list(existing_units)
    for unit in unit_dependencies:
        units_required += return_current_unit_dependencies(unit, new_existing_units)
        units_required.append(unit)
        new_existing_units += units_required
    return units_required
