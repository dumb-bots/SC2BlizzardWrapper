import itertools
from functools import reduce

from api_wrapper.utils import get_closing_enemies
from constants.unit_type_ids import UnitTypeIds
from constants.upgrade_ids import UpgradeIds
from game_data.units import UnitManager
from players.actions import ActionsPlayer, Train, Harvest, Upgrade, Build, Attack, Expansion, DistributeHarvest


class Rule:
    def __init__(self, condition_parameters, actions, burner=False):
        self.condition_parameters = condition_parameters
        self.actions = actions
        self.burner = burner
        self._activated = False

    def _match(self, game_state, player):
        return False

    def match(self, game_state, player):
        if self.burner and self._activated:
            return False
        match = self._match(game_state, player)
        if match:
            self._activated = True
        return match

    def match_query_output(self, game_state):
        return None

    def next_actions(self, game_state, player):
        output = self.match_query_output(game_state)
        if output is None:
            return self.actions
        else:
            return list(map(lambda action: self._update_action_params(action, game_state), self.actions))

    def _update_action_params(self, action, game_state):
        return action


class ActionsRule(Rule):
    def _match(self, game_state, player):
        action_count = {}
        for action in player.actions_queue:
            action_name = action.__class__.__name__
            existing_value = action_count.get(action_name, 0)
            action_count[action_name] = existing_value + 1
        return action_count == self.condition_parameters


class UpgradesRule(Rule):
    def _match(self, game_state, player):
        return not (self.condition_parameters - set([u.upgrade_id for u in game_state.player_info.upgrades]))


class UnitsRule(Rule):
    def _match(self, game_state, player):
        filtered_units = self.match_query_output(game_state)
        return self.condition_parameters['evaluation'](filtered_units)

    def match_query_output(self, game_state):
        if self.condition_parameters['alignment'] == 'player':
            unit_set = game_state.player_units
        else:
            unit_set = game_state.enemy_units
        return unit_set.filter(**self.condition_parameters['query_params'])

    def _update_action_params(self, action, game_state):
        try:
            if action.target_unit:
                action.target_unit['ids'] = self.match_query_output(game_state)
        except AttributeError:
            pass
        return action


class Defend(UnitsRule):
    def _match(self, game_state, player):
        filtered_units = self.match_query_output(game_state)
        return filtered_units

    def match_query_output(self, game_state):
        return get_closing_enemies(game_state)


class TerminateIdleUnits(UnitsRule):
    def idle_units(self, game_state):
        return game_state.player_units.filter(
            mode=UnitManager.EXCLUDE_OR_MODE,
            movement_speed=0, unit_type=UnitTypeIds.SCV.value,
        ).filter(orders__attlength=0)

    def _match(self, game_state, player):
        no_enemy_th = not game_state.enemy_units.filter(
            unit_type__in=[
                UnitTypeIds.HATCHERY.value, UnitTypeIds.LAIR.value, UnitTypeIds.HIVE.value,
                UnitTypeIds.COMMANDCENTER.value, UnitTypeIds.ORBITALCOMMAND.value, UnitTypeIds.PLANETARYFORTRESS.value
            ],
        )
        return no_enemy_th and self.idle_units(game_state)

    def next_actions(self, game_state, player):
        enemy_targets = game_state.enemy_units.filter(movement_speed=0)
        if not enemy_targets:
            enemy_targets = game_state.enemy_units

        return [Attack(
            {"query": {"tag__in": self.idle_units(game_state).values('tag', flat_list=True)}},
            target_unit={
                "ids": enemy_targets.values('tag', flat_list=True),
                "alignment": "enemy",
                "action_pos": True,
            }
        )]


class Exterminate(TerminateIdleUnits):
    def _match(self, game_state, player):
        return game_state.game_loop > 30000


class DefendIdleUnits(TerminateIdleUnits):
    def match_query_output(self, game_state):
        return get_closing_enemies(game_state)

    def _match(self, game_state, player):
        return self.match_query_output(game_state) and self.idle_units(game_state)

    def next_actions(self, game_state, player):
        return [Attack(
            {"query": {"tag__in": self.idle_units(game_state).values('tag', flat_list=True)}},
            target_unit={
                "ids": self.match_query_output(game_state),
                "alignment": "enemy",
                "action_pos": True,
            }
        )]


class IdleWorkersHarvest(UnitsRule):
    def match_query_output(self, game_state):
        return game_state.player_units.filter(unit_type=UnitTypeIds.SCV.value, orders__attlength=0)

    def _match(self, game_state, player):
        return self.match_query_output(game_state)

    def next_actions(self, game_state, player):
        unit_group = {"query": {"tag__in": self.match_query_output(game_state).values('tag', flat_list=True)}}
        return [DistributeHarvest(unit_group)]


class OverWorkersHarvest(UnitsRule):
    HARVESTING_HUBS = [
        UnitTypeIds.REFINERY.value,
        UnitTypeIds.COMMANDCENTER.value,
        UnitTypeIds.PLANETARYFORTRESS.value,
        UnitTypeIds.ORBITALCOMMAND.value,
    ]

    def match_query_output(self, game_state):
        town_halls = game_state.player_units.filter(build_progress=1, unit_type__in=self.HARVESTING_HUBS)
        return UnitManager(list(filter(lambda th: th.assigned_harvesters > th.ideal_harvesters, town_halls)))

    def _match(self, game_state, player):
        return self.match_query_output(game_state)

    def _get_spare_workers(self, game_state):
        worker_tags = []
        workers = game_state.player_units.filter(unit_type=UnitTypeIds.SCV.value)
        for hub in self.match_query_output(game_state):
            workers_got = 0
            extra_workers = hub.assigned_harvesters - hub.ideal_harvesters
            for worker in workers:
                if workers_got >= extra_workers:
                    break

                for order in worker.orders:
                    if order.target_unit_tag == hub.tag:
                        worker_tags.append(worker.tag)
                        workers_got += 1
                        break
        return worker_tags

    def next_actions(self, game_state, player):
        spare_workers = self._get_spare_workers(game_state)
        if spare_workers:
            unit_group = {"query": {"tag__in": spare_workers}}
            return [DistributeHarvest(unit_group)]
        return []


class TooMuchWorkersExpansion(OverWorkersHarvest):
    def get_idle_workers(self, game_state):
        return game_state.player_units.filter(unit_type=UnitTypeIds.SCV.value, orders__attlength=0)

    def get_available_hubs(self, game_state):
        harvesting_hubs = game_state.player_units.filter(build_progress=1, unit_type__in=self.HARVESTING_HUBS)
        return UnitManager(list(filter(lambda hub: hub.assigned_harvesters < hub.ideal_harvesters, harvesting_hubs)))

    def get_workers_to_assign(self, game_state):
        return self._get_spare_workers(game_state) + self.get_idle_workers(game_state)

    def get_number_of_workers_to_assign(self, game_state):
        under_producing_workers = (self._get_spare_workers(game_state) + self.get_idle_workers(game_state))
        workers_to_assign = len(under_producing_workers)
        return workers_to_assign

    def get_available_spots(self, hub):
        harvest_diff = hub.ideal_harvesters - hub.assigned_harvesters
        return harvest_diff if harvest_diff > 0 else 0

    def get_number_of_working_spots(self, game_state):
        return reduce(
            lambda acc, hub: acc + self.get_available_spots(hub),
            self.get_available_hubs(game_state),
            0,
        )

    def _match(self, game_state, player):
        workers_to_assign = self.get_number_of_workers_to_assign(game_state)
        available_working_spots = self.get_number_of_working_spots(game_state)
        return workers_to_assign > available_working_spots

    def get_upcoming_spots(self, game_state, player):
        th_under_construction = game_state.player_units.filter(unit_type__in=[18, 132, 130], build_progress__lt=1)
        r_under_construction = game_state.player_units.filter(unit_type__in=[20], build_progress__lt=1)

        expansions_in_queue = list(filter(lambda a: isinstance(a, Expansion), player.actions_queue))
        refineries_in_queue = list(filter(lambda a: isinstance(a, Build) and a.unit_id == 20, player.actions_queue))

        orders = list(itertools.chain(*game_state.player_units.filter(unit_type=45).values('orders', flat_list=True)))
        th_orders = list(filter(lambda o: o.ability_id == 318, orders))
        ref_orders = list(filter(lambda o: o.ability_id == 320, orders))

        th_spots = (len(th_under_construction) + len(expansions_in_queue) + len(th_orders)) * 16
        ref_spots = (len(r_under_construction) + len(refineries_in_queue) + len(ref_orders)) * 3

        return th_spots + ref_spots

    def get_total_refineries(self, game_state, player):
        refineries = game_state.player_units.filter(unit_type=UnitTypeIds.REFINERY.value)
        refineries_in_queue = list(filter(lambda a: isinstance(a, Build) and a.unit_id == 20, player.actions_queue))
        return len(refineries) + len(refineries_in_queue)

    def get_total_ths(self, game_state, player):
        ths = game_state.player_units.filter(unit_type__in=[18, 132, 130])
        expansions_in_queue = list(filter(lambda a: isinstance(a, Expansion), player.actions_queue))
        return len(ths) + len(expansions_in_queue)

    def next_actions(self, game_state, player):
        workers_to_assign = self.get_workers_to_assign(game_state)
        available_spots = self.get_number_of_working_spots(game_state)
        upcoming_spots = self.get_upcoming_spots(game_state, player)
        workers_left_to_assign = len(workers_to_assign) - upcoming_spots + available_spots
        if workers_left_to_assign <= 0:
            return []

        missing_expansions = 0
        missing_refineries = self.get_total_ths(game_state, player) * 2 - self.get_total_refineries(game_state, player)
        missing_refineries = missing_refineries if missing_refineries > 0 else 0
        if missing_refineries * 3 < workers_left_to_assign:
            missing_expansions = 1

        return ([Build(UnitTypeIds.REFINERY.value)] * missing_refineries) + ([Expansion()] * missing_expansions)


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
                lambda action_list, rule: action_list + rule.next_actions(game_state, self),
                passing_rules,
                []
            )

    async def process_step(self, ws, game_state, raw=None, actions=None):
        passing_rules = [rule for rule in self.rules if rule.match(game_state, self)]
        self.apply_actions(game_state, passing_rules)
        await super(RulesPlayer, self).process_step(ws, game_state, raw, actions)


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


DEMO_RULES_ACTIONS_2 = [Train(UnitTypeIds.SCV.value, 1) for _ in range(30)] + \
                       [Build(UnitTypeIds.BARRACKSREACTOR.value) for _ in range(2)] + \
                       [Build(UnitTypeIds.REFINERY.value)] + \
                       [Train(UnitTypeIds.MARINE.value, 1) for _ in range(30)] + \
                       [Train(UnitTypeIds.MARAUDER.value, 1) for _ in range(7)] + \
                       [Harvest({"composition": {UnitTypeIds.SCV.value: 3}}, Harvest.VESPENE)] + \
                       [Train(UnitTypeIds.MEDIVAC.value, 1) for _ in range(4)] + \
                       [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(4)] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value)] + \
                       [Expansion()] + \
                       [Upgrade(UpgradeIds.TERRANINFANTRYARMORSLEVEL1.value)] + \
                       [Upgrade(UpgradeIds.SHIELDWALL.value)] + \
                       [Upgrade(UpgradeIds.PUNISHERGRENADES.value)]

DEMO_RULES_2 = [
    ActionsRule(
        {},
        [Train(UnitTypeIds.MARINE.value, 1) for _ in range(6)] +
        [Train(UnitTypeIds.MARAUDER.value, 1) for _ in range(2)] +
        [Train(UnitTypeIds.SIEGETANK.value, 1) for _ in range(1)]
    ),
    DefendIdleUnits(None, None),
    TerminateIdleUnits(None, None),
    IdleWorkersHarvest(None, None),
    OverWorkersHarvest(None, None),
    TooMuchWorkersExpansion(None, None),
    UnitsRule(
        {
            "alignment": "player",
            "query_params": {"unit_type": UnitTypeIds.REFINERY.value, "build_progress": 1},
            "evaluation": lambda units: len(units) > 1,
        },
        [Harvest({"composition": {UnitTypeIds.SCV.value: 6}}, Harvest.VESPENE)],
        burner=True,
    ),
    UnitsRule(
        {
            "alignment": "player",
            "query_params": {"unit_type": UnitTypeIds.COMMANDCENTER.value, "build_progress": 1},
            "evaluation": lambda units: len(units) > 1,
        },
        [Train(UnitTypeIds.SCV.value, 1) for _ in range(10)],
        burner=True,
    ),
    ActionsRule(
        {},
        [Attack(
            {"query": {"unit_type__in": [48, 33, 54, 51]}},
            target_unit={
                "types": [UnitTypeIds.HATCHERY.value, UnitTypeIds.LAIR.value, UnitTypeIds.HIVE.value],
                "alignment": "enemy",
                "action_pos": True,
            }
        )]
    )
]


IDLE_RULES = [
    DefendIdleUnits(None, None),
    TerminateIdleUnits(None, None),
    IdleWorkersHarvest(None, None),
    OverWorkersHarvest(None, None),
    TooMuchWorkersExpansion(None, None),
]