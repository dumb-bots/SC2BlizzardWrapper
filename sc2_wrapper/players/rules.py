from functools import reduce

from sc2_wrapper.constants.unit_type_ids import UnitTypeIds
from sc2_wrapper.constants.upgrade_ids import UpgradeIds
from sc2_wrapper.game_data.units import UnitManager
from sc2_wrapper.players.actions import ActionsPlayer, Train, Harvest, Upgrade, Build, Attack


class Rule:
    def __init__(self, condition_parameters, actions, burner=False):
        self.condition_parameters = condition_parameters
        self.actions = actions
        self.burner = burner

    def match(self, game_state, player):
        pass

    def match_query_output(self, game_state):
        return None

    def next_actions(self, game_state):
        output = self.match_query_output(game_state)
        if output is None:
            return self.actions
        else:
            return list(map(lambda action: self._update_action_params(action, game_state), self.actions))

    def _update_action_params(self, action, game_state):
        return action


class ActionsRule(Rule):
    def match(self, game_state, player):
        action_count = {}
        for action in player.actions_queue:
            action_name = action.__class__.__name__
            existing_value = action_count.get(action_name, 0)
            action_count[action_name] = existing_value + 1
        return action_count == self.condition_parameters


class UpgradesRule(Rule):
    def match(self, game_state, player):
        return not (self.condition_parameters - set([u.upgrade_id for u in game_state.player_info.upgrades]))


class UnitsRule(Rule):
    def match(self, game_state, player):
        filtered_units = self.match_query_output(game_state)
        return self.condition_parameters['evaluation'](filtered_units)

    def match_query_output(self, game_state):
        if self.condition_parameters['alignment'] == 'player':
            unit_set = game_state.player_units
        else:
            unit_set = game_state.enemy_units
        return unit_set.filter(**self.condition_parameters['query_params'])

    def _update_action_params(self, action, game_state):
        action.target_unit['ids'] = self.match_query_output(game_state)
        return action


class Defend(UnitsRule):
    def match(self, game_state, player):
        filtered_units = self.match_query_output(game_state)
        return filtered_units

    def match_query_output(self, game_state):
        # TODO: Check race
        town_halls = game_state.player_units.filter(unit_type__in=[
            UnitTypeIds.COMMANDCENTER.value,
            UnitTypeIds.ORBITALCOMMAND.value,
            UnitTypeIds.PLANETARYFORTRESS.value,
        ])
        min_distance = 30
        dangerous_units = UnitManager([])
        for th in town_halls:
            e_units = game_state.enemy_units\
                .add_calculated_values(distance_to={"unit": th})\
                .filter(last_distance_to__lte=min_distance)
            dangerous_units += e_units
        return dangerous_units.values('tag', flat_list=True)


class RulesPlayer(ActionsPlayer):
    def __init__(self):
        super().__init__()
        self.queues = []
        self.rules = []

    async def create(self, race, obj_type, difficulty=None, server=None, server_route=None, server_address=None,
                     **kwargs):

        await super().create(race, obj_type, difficulty, server, server_route, server_address, **kwargs)
        self.queues = kwargs.get('queues', [])
        self.rules = kwargs.get('rules', [])

    def apply_actions(self, game_state, passing_rules):
        if passing_rules:
            self.actions_queue += reduce(
                lambda action_list, rule: action_list + rule.next_actions(game_state),
                passing_rules,
                []
            )

    async def process_step(self, ws, game_state, actions=None):
        passing_rules = [rule for rule in self.rules if rule.match(game_state, self)]
        self.apply_actions(game_state, passing_rules)
        await super(RulesPlayer, self).process_step(ws, game_state, actions)


DEMO_RULES_ACTIONS_1 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                       [Build(UnitTypeIds.BARRACKSREACTOR.value)] + \
                       [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)] + \
                       [Harvest({UnitTypeIds.SCV.value: 3}, Harvest.VESPENE)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value)]
DEMO_RULES_1 = [
    ActionsRule(
        {},
        [Attack({
            UnitTypeIds.MARINE.value: 20},
            target_unit={
                "types": [UnitTypeIds.HATCHERY.value, UnitTypeIds.LAIR],
                "alignment": "enemy",
                "action_pos": True,
            }
        )] +
        [Train(UnitTypeIds.MARINE.value, 1) for _ in range(25)]
    )
]


DEMO_RULES_ACTIONS_2 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(4)] + \
                       [Build(UnitTypeIds.BARRACKSREACTOR.value)] + \
                       [Train(UnitTypeIds.MARINE.value, 1) for _ in range(30)] + \
                       [Harvest({"composition": {UnitTypeIds.SCV.value: 3}}, Harvest.VESPENE)] + \
                       [Train(UnitTypeIds.MEDIVAC.value, 1) for _ in range(4)] + \
                       [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(4)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYARMORSLEVEL1.value)]
                       # [Upgrade(UpgradeIds.SHIELDWALL.value)] + \

DEMO_RULES_2 = [
    ActionsRule(
        {},
        [Train(UnitTypeIds.MARINE.value, 1) for _ in range(30)]
    ),
    Defend(
        {},
        [Attack(
            {"query": {"unit_type__in": [48, 33, 54]}},
            target_unit={
                "alignment": "enemy",
                "action_pos": True,
            }
        )]
    ),
    ActionsRule(
        {},
        [Attack(
            {"query": {"unit_type__in": [48, 33, 54]}},
            target_unit={
                "types": [UnitTypeIds.HATCHERY.value, UnitTypeIds.LAIR.value, UnitTypeIds.HIVE.value],
                "alignment": "enemy",
                "action_pos": True,
            }
        )]
    )
]
