import s2clientprotocol.raw_pb2 as api_data
from PIL import Image
from sc2_wrapper.game_data.units import UnitManager, Unit


class DecodedObservation:
    def __init__(self, observation, game_data, actions=[]):
        # Set player data
        self.player_info = PlayerCommon(
            observation.player_common, observation.raw_data.player, game_data
        )

        # Set game units
        self.all_units = UnitManager(
            [Unit(unit, game_data) for unit in observation.raw_data.units]
        )
        self.player_units = UnitManager(
            [
                Unit(unit, game_data)
                for unit in observation.raw_data.units
                if unit.alliance == api_data.Alliance.Value("Self")
            ]
        )
        self.allied_units = UnitManager(
            [
                Unit(unit, game_data)
                for unit in observation.raw_data.units
                if unit.alliance == api_data.Alliance.Value("Ally")
            ]
        )
        self.enemy_units = UnitManager(
            [
                Unit(unit, game_data)
                for unit in observation.raw_data.units
                if unit.alliance == api_data.Alliance.Value("Enemy")
            ]
        )
        self.neutral_units = UnitManager(
            [
                Unit(unit, game_data)
                for unit in observation.raw_data.units
                if unit.alliance == api_data.Alliance.Value("Neutral")
            ]
        )
        self.all_units = UnitManager(
            [Unit(unit, game_data) for unit in observation.raw_data.units]
        )
        self.enemy_currently_seeing_units = self.enemy_units.filter(display=1)
        self.enemy_snapshot = self.enemy_units.filter(display=2)

        # Effects and events data
        self.game_event = observation.raw_data.event
        self.game_effects = observation.raw_data.effects

        # Observation's game loop
        self.game_loop = observation.game_loop
        self.game_data = game_data
        self.actions = actions
        self.parsed_actions = []
        for action in self.actions:
            ac = action.action_raw
            if not ac.unit_command:
                continue
            else:
                identifier = ac.unit_command.ability_id
                types_grouped = {}
                if ac.unit_command.target_unit_tag:
                    tag = ac.unit_command.target_unit_tag
                    unit = self.all_units.filter(tag=tag)
                    if unit:
                        position = unit[0].get_attribute("pos")
                        if unit[0].proto_unit_data:
                            target_unit_type = unit[0].proto_unit_data.unit_id
                            target_unit_name = unit[0].proto_unit_data.name
                        targetx = position.x
                        targety = position.y
                    else:
                        continue
                else:
                    targetx, targety = (
                        ac.unit_command.target_world_space_pos.x,
                        ac.unit_command.target_world_space_pos.y,
                    )
                    target_unit_type = None
                    target_unit_name = None
                for tag in list(ac.unit_command.unit_tags):
                    if self.player_units.filter(tag=tag):
                        unitType = self.player_units.filter(tag=tag)[0].proto_unit_data
                        if unitType:
                            order = types_grouped.get(unitType.unit_id, 0)
                            order += 1
                            types_grouped[unitType.unit_id] = order

                if types_grouped.items():
                    for key in types_grouped.keys():
                        item = {
                            "unit_type_id": key,
                            "amount": types_grouped[key],
                            "action_id": identifier,
                            "x": targetx,
                            "y": targety,
                            "target_type": target_unit_type,
                        }
                        self.parsed_actions.append(item)
        self.visibility_data = observation.raw_data.map_state.visibility
        self.discovery_percentage = sum(
            filter(lambda x: x >= 1, self.visibility_data.data)
        ) / len(self.visibility_data.data)
        self.creep_data = observation.raw_data.map_state.creep
        self.creep_percentage = sum(
            filter(lambda x: x >= 1, self.creep_data.data)
        ) / len(self.creep_data.data)

    def get_visibility_map(self):
        image_data = map(lambda x: 100 * x, self.visibility_data.data)
        image = Image.frombytes(
            "L",
            (self.visibility_data.size.x, self.visibility_data.size.y),
            bytes(image_data),
            "raw",
        )
        return image

    def get_creep_map(self):
        image_data = map(lambda x: 100 * x, self.creep_data.data)
        image = Image.frombytes(
            "L",
            (self.creep_data.size.x, self.creep_data.size.y),
            bytes(image_data),
            "raw",
        )
        return image

    def to_case(self, replay_info):
        json_dict = {
            "minerals": self.player_info.minerals,
            "vespene": self.player_info.vespene,
            "game_loop": self.game_loop,
            "food_cap": self.player_info.food_cap,
            "food_used": self.player_info.food_used,
            "food_army": self.player_info.food_army,
            "food_workers": self.player_info.food_workers,
            "idle_worker_count": self.player_info.idle_worker_count,
            "visibility_percentage": round(self.discovery_percentage, 2),
            "creep_percentage": round(self.creep_percentage, 2),
            "army_count": self.player_info.army_count,
            "warp_gate_count": self.player_info.warp_gate_count,
            "units": self.count_units(self.player_units),
            "enemy_units": self.count_units(self.enemy_units),
            "upgrades": list(map(lambda x: x.upgrade_id, self.player_info.upgrades)),
            "visible_enemy_units": self.count_units(self.enemy_currently_seeing_units),
            "known_invisible_enemy_units": self.count_units(self.enemy_snapshot),
            "map": replay_info["map"],
            "actions": self.parsed_actions,
        }
        return json_dict

    def count_units(self, units):
        type_amount = {}
        for unit in units:
            val = type_amount.get(unit.proto_unit.unit_type, 0)
            val += 1
            type_amount[unit.proto_unit.unit_type] = val
        result = []
        for key in type_amount.keys():
            item = {"unit_type_ id": key, "amount": type_amount[key]}
            result.append(item)
        return result


def decode_observation(observation, game_data):
    return DecodedObservation(observation, game_data)


class PlayerCommon:
    def __init__(self, proto_player_common, proto_raw_player, game_data):
        self.player_id = proto_player_common.player_id
        self.minerals = proto_player_common.minerals
        self.vespene = proto_player_common.vespene
        self.food_cap = proto_player_common.food_cap
        self.food_used = proto_player_common.food_used
        self.food_army = proto_player_common.food_army
        self.food_workers = proto_player_common.food_workers
        self.idle_worker_count = proto_player_common.idle_worker_count
        self.army_count = proto_player_common.army_count
        self.warp_gate_count = proto_player_common.warp_gate_count

        # Raw data
        self.power_sources = proto_raw_player.power_sources
        self.camera = proto_raw_player.camera
        self.upgrades = []
        for upgraded in proto_raw_player.upgrade_ids:
            for upgrade in game_data.upgrades:
                if upgrade.upgrade_id == upgraded:
                    self.upgrades.append(upgrade)

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "minerals": self.minerals,
            "vespene": self.vespene,
            "food_cap": self.food_cap,
            "food_used": self.food_used,
            "food_army": self.food_army,
            "food_workers": self.food_workers,
            "idle_worker_count": self.idle_worker_count,
            "army_count": self.army_count,
            "warp_gate_count": self.warp_gate_count,
        }


class UnitsProfile:
    def __init__(self, decoded_observation):
        player_unit_count = {}
        for unit in decoded_observation.player_units:
            player_unit_count[unit.name] = player_unit_count.get(unit.name, 0) + 1
        self.player_unit_count = player_unit_count

        enemy_unit_count = {}
        for unit in decoded_observation.enemy_units:
            enemy_unit_count[unit.name] = enemy_unit_count.get(unit.name, 0) + 1
        self.enemy_unit_count = enemy_unit_count

    def to_dict(self):
        return {
            "player_unit_count": self.player_unit_count,
            "enemy_unit_count": self.enemy_unit_count,
        }
