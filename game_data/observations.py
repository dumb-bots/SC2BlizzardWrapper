import s2clientprotocol.raw_pb2 as api_data

from game_data.units import UnitManager, Unit


class DecodedObservation:
    def __init__(self, observation, game_data, actions = []):
        # Set player data
        self.player_info = PlayerCommon(observation.player_common, observation.raw_data.player, game_data)

        # Set game units
        self.player_units = UnitManager([Unit(unit, game_data) for unit in observation.raw_data.units
                                         if unit.alliance == api_data.Alliance.Value("Self")])
        self.allied_units = UnitManager([Unit(unit, game_data) for unit in observation.raw_data.units
                                         if unit.alliance == api_data.Alliance.Value("Ally")])
        self.enemy_units = UnitManager([Unit(unit, game_data) for unit in observation.raw_data.units
                                        if unit.alliance == api_data.Alliance.Value("Enemy")])
        self.neutral_units = UnitManager([Unit(unit, game_data) for unit in observation.raw_data.units
                                          if unit.alliance == api_data.Alliance.Value("Neutral")])
        self.all_units = UnitManager([Unit(unit, game_data) for unit in observation.raw_data.units])

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
                ability = ""
                identifier = ac.unit_command.ability_id
                if identifier == 1:
                    continue
                for ability in game_data.abilities:
                    if ability.ability_id == identifier:
                        ability = ability.friendly_name
                        break
                # TODO Change unit target to spatial target
                for tag in list(ac.unit_command.unit_tags):

                    targetx, targety = (ac.unit_command.target_world_space_pos.x, ac.unit_command.target_world_space_pos.y)
                    if self.player_units.filter(tag=tag):
                        unitType = self.player_units.filter(tag=tag)[0].proto_unit_data
                        self.parsed_actions.append((identifier, targetx, targety, unitType.unit_id, unitType.name, ability))
                    else:
                        self.parsed_actions.append((identifier, targetx, targety, None, None, ability))


    def to_dict(self):
        return {
            "player_common": self.player_info.to_dict(),
            "player_units": [unit.to_dict() for unit in self.player_units],
            "allied_units": [unit.to_dict() for unit in self.allied_units],
            "enemy_units": [unit.to_dict() for unit in self.enemy_units],
            "neutral_units": [unit.to_dict() for unit in self.neutral_units],
            "game_loop": self.game_loop
        }


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