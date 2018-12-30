from functools import reduce

from sc2_wrapper.constants.unit_type_ids import UnitTypeIds
from sc2_wrapper.constants.upgrade_ids import UpgradeIds
from sc2_wrapper.players.actions import ActionsPlayer, Train, Harvest, Upgrade, Build, Attack


class Rule:
    def __init__(self, condition_parameters, actions, burner=False):
        self.condition_parameters = condition_parameters
        self.actions = actions
        self.burner = burner

    def match(self, game_state, player):
        pass

    def next_actions(self):
        return self.actions


class ActionsRule(Rule):
    def match(self, game_state, player):
        action_count = {}
        for action in player.actions_queue:
            action_name = action.__class__.__name__
            existing_value = action_count.get(action_name, 0)
            action_count[action_name] = existing_value + 1
        return action_count == self.condition_parameters


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

    def apply_actions(self, passing_rules):
        self.actions_queue += reduce(lambda action_list, rule: action_list + rule.next_actions(), passing_rules, [])

    async def process_step(self, ws, game_state, actions=None):
        passing_rules = [rule for rule in self.rules if rule.match(game_state, self)]
        self.apply_actions(passing_rules)
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
                       [Upgrade(UpgradeIds.SHIELDWALL.value)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYARMORSLEVEL1.value)]

DEMO_RULES_2 = [
    ActionsRule(
        {},
        [Attack(
            {"query": {"unit_type__in": [48, 33, 54]}},
            target_unit={
                "types": [UnitTypeIds.HATCHERY.value, UnitTypeIds.LAIR, UnitTypeIds.HIVE],
                "alignment": "enemy",
                "action_pos": True,
            }
        )] +
        [Train(UnitTypeIds.MARINE.value, 1) for _ in range(30)]
    )
]
