import random
from api_wrapper.utils import obs_to_case
from constants.ability_ids import AbilityId
from constants.build_abilities import BUILD_ABILITY_UNIT
from constants.unit_data import UNIT_DATA
from constants.unit_dependencies import UNIT_DEPENDENCIES
from constants.unit_type_ids import UnitTypeIds
from constants.upgrade_abilities import UPGRADE_ABILITY_MAPPING
from players import actions
from players.rules import RulesPlayer
import time

class CBRAlgorithm(RulesPlayer):
    async def create(
            self, race, obj_type,
            difficulty=None, server=None, server_route=None, server_address=None, cases=None,
            **kwargs
    ):
        self.cases = cases
        self.cases_by_loop = {}
        await super().create(race, obj_type,difficulty,server, server_route, server_address, **kwargs)

    async def perform_ready_actions(self, ws, new_actions, game_state):
        new_actions = await super(CBRAlgorithm, self).perform_ready_actions(ws, new_actions, game_state)
        return new_actions[-30:]

    async def process_step(self, ws, game_state, raw=None, actions=None):
        start = time.time()
        cbr_actions = await self.determine_actions(raw)
        # cbr_actions = list(filter(lambda x: x["id"] != 1, cbr_actions))
        translated_actions = self.raw_actions_to_player_actions(cbr_actions[:10], game_state)
        self.actions_queue += translated_actions
        await super(CBRAlgorithm, self).process_step(ws, game_state, raw, actions)
        end = time.time()
        print(end-start)

    async def determine_actions(self, raw):
        situation = obs_to_case(raw[0], raw[1])
        print(situation["loop"])
        probabilities_per_case = []
        actions = []
        if situation["loop"] == 0:
            self.cases = filter(lambda x: x["observation"]["startingPoints"] == situation["startingPoints"], self.cases)
            for case in self.cases:
                value = self.cases_by_loop.get(round(case["observation"]["loop"] / float(200)), [])
                value.append(case)
                self.cases_by_loop[round(case["observation"]["loop"] / float(200))] = value
        if self.cases_by_loop:
            look_cases = self.cases_by_loop.get(round(situation["loop"] / float(200)), [])
            if not look_cases:
                keys = sorted(look_cases.keys())[-10:]
                look_cases = look_cases[keys[random.randint(0,9)]]

            for case in look_cases:
                case_evaluation = self.evaluate_case(situation, case)  # I take the first case and evaluate it
                probabilities_per_case.append([case, case_evaluation])
            items = probabilities_per_case
            items = sorted(items, key=lambda x: x[1])
            items = items[-100:]

            total = sum(map(lambda x: x[1], items))
            items = map(lambda x: [x[0], x[1] / total], items)
            items = list(items)
            # print(items)
            for items_index in range(0, len(items) - 1):
                items[items_index + 1][1] += items[items_index][1]

            random_number = random.uniform(0, 1)

            selected_case = None
            for item in items:
                if random_number <= item[1]:
                    selected_case = item[0]
                    break
            if selected_case:
                actions = selected_case["actions"]  # List of actions for the case
                print("Actions " + str(actions))
                if actions:
                    list_of_actions = []
                    selected_actions = []
                    for action in actions:
                        list_of_actions.append([action, self.evaluate_action(action)])
                    maximum_fitness = max(map(lambda x: x[1], list_of_actions))
                    list_of_actions = list(map(lambda x: [x[0], x[1] / maximum_fitness * x[0]["games"] / selected_case["games"]], list_of_actions))
                    print(list_of_actions)
                    for action in list_of_actions:
                        rnd = random.uniform(0,1)
                        if rnd <= action[1]:
                            selected_actions.append(action[0])
                    actions = selected_actions
        return actions

    #Returns the distance between two cases    
    def get_distance(self, situation, case):
        distance = 0
        distance += abs(situation["minerals"] - case["observation"]["minerals"]) * 100
        distance += abs(situation["vespene"] - case["observation"]["vespene"]) * 100
        distance += abs(situation["foodCap"] - case["observation"]["foodCap"]) * 100
        distance += abs(situation["foodUsed"] - case["observation"]["foodUsed"]) * 100
        distance += abs(situation["foodArmy"] - case["observation"]["foodArmy"])
        distance += abs(situation["foodWorkers"] - case["observation"]["foodWorkers"])
        distance += abs(situation["idleWorkerCount"] - case["observation"]["idleWorkerCount"]) * 100
        distance += abs(situation["armyCount"] - case["observation"]["armyCount"])
        distance += abs(situation["warpGateCount"] - case["observation"]["warpGateCount"])
        distance += abs(situation["loop"] - case["observation"]["loop"])

        set_upgrades_union = set(situation["upgrades"] + case["observation"]["upgrades"])
        set_upgrades_intersection = set(situation["upgrades"]) & set(case["observation"]["upgrades"])
        distance += (len(set_upgrades_union) - len(set_upgrades_intersection))/(len(set_upgrades_union) + 1) * 300

        list_units_situation = situation["units"]
        list_units_case = case["observation"]["units"]
        distance += abs(len(list_units_situation) - len(list_units_case))

        units_by_type_situation = {}
        units_by_type_case = {}
        for unit_situation in list_units_situation:
            value = units_by_type_situation.get(unit_situation["type"], [])
            value.append(unit_situation)
            units_by_type_situation[unit_situation["type"]] = value
        for unit_case in list_units_case:
            value = units_by_type_case.get(unit_case["type"], [])
            value.append(unit_case)
            units_by_type_case[unit_case["type"]] = value

        for unit_situation in list_units_situation:
            comparing_units = units_by_type_case.get(unit_situation["type"], [])
            if comparing_units:
                units_distance = min(comparing_units, key = lambda x : self.units_distance(x, unit_situation))
                distance += self.units_distance(units_distance, unit_situation)

        for unit_case in list_units_case:
            comparing_units = units_by_type_situation.get(unit_case["type"],[])
            if comparing_units:
                units_distance = min(comparing_units, key = lambda x : self.units_distance(x, unit_case))
                distance += self.units_distance(units_distance, unit_case)

        return distance
    
    #Returns the case evaluation
    def evaluate_case(self, situation, case):
        won = case["wins"]
        count = case["games"]
        lost = case["looses"]
        distance = self.get_distance(situation, case)
        #distance = 0
        case_eval = (count / (count + 10)) * ((count) / (count + lost)) * (1 / (1 + distance))
        # case_eval = 1 / (1 + distance)
        return case_eval

    #Returns te action evaluation
    def evaluate_action(self, action):
        count = action["games"]
        won = action["wins"]
        lost = action["looses"]
        eval_action = (count / (count + 10)) * ((count) / (count + lost))
        return eval_action

    def units_distance(self, unit1, unit2):
        distance = 0
        if unit1["alliance"] != unit2["alliance"]:
            distance += 1
        distance += ((unit1["position"]["x"] - unit2["position"]["x"]) ** 2  + (unit1["position"]["y"] - unit2["position"]["y"]) ** 2) ** (1/2)
        return distance

    def raw_actions_to_player_actions(self, actions, game_state):
        return [action for action in map(lambda a: self.raw_action_to_player_action(a, game_state), actions) if action]

    def raw_action_to_player_action(self, action, game_state):
        action_id = action.get('id')
        if not isinstance(action_id, int):
            return

        unit_group = self._unit_group_from_action(action)
        target_point = self._target_point_from_action(action)
        target_unit = self._target_unit_from_action(action, game_state)

        if action_id == 1 and not target_unit:
            return

        # Check Build Actions
        built_unit = BUILD_ABILITY_UNIT.get(action_id)
        if UNIT_DEPENDENCIES.get(built_unit):
            if UNIT_DATA.get(built_unit, {}).get('food_required', 0) > 0:
                return actions.Train(built_unit)
            elif built_unit == UnitTypeIds.COMMANDCENTER.value:
                return actions.Expansion(target_point)
            else:
                if (built_unit in [48, 49]):
                    print("WHAT THE FUCK ARE YOU DOING?")
                    print(UNIT_DATA.get(built_unit, {}).get('food_required', 0))
                return actions.Build(built_unit, target_point)

        # Check upgrades
        upgrade_id = UPGRADE_ABILITY_MAPPING.get(action_id)
        if upgrade_id:
            return actions.Upgrade(upgrade_id)

        # Check Unit Actions
        if action_id in [AbilityId.ATTACK_ATTACK.value, AbilityId.ATTACK.value]:
            return actions.Attack(unit_group, target_point, target_unit)
        else:
            return actions.UnitAction(action_id, unit_group, target_point, target_unit)

    def _unit_group_from_action(self, action):
        unit_type_histogram = {}
        unit_types = [u['type'] for u in action['units']]
        for unit_type in unit_types:
            unit_type_histogram[unit_type] = unit_type_histogram.get(unit_type, 0) + 1
        return {"composition": unit_type_histogram}

    def _target_point_from_action(self, action):
        target_point = action.get('targetPoint')
        if target_point:
            return target_point.get("x", 0), target_point.get("y", 0)
        return None

    def _target_unit_from_action(self, action, game_state):
        target_unit = action.get('targetUnit')
        if target_unit:
            return self._get_unit_info(game_state, target_unit)
        return None

    def _get_unit_info(self, game_state, target_unit):
        unit_type = target_unit['type']
        unit_position = target_unit['position']['x'], target_unit['position']['y']
        p_units = game_state.player_units.filter(unit_type=unit_type).add_calculated_values(
            distance_to={'pos': unit_position})
        closest_p_unit = min(p_units, key=lambda u: u.last_distance_to) if p_units else None
        e_units = game_state.player_units.filter(unit_type=unit_type).add_calculated_values(
            distance_to={'pos': unit_position})
        closest_e_unit = min(e_units, key=lambda u: u.last_distance_to) if e_units else None
        n_units = game_state.player_units.filter(unit_type=unit_type).add_calculated_values(
            distance_to={'pos': unit_position})
        closest_n_unit = min(n_units, key=lambda u: u.last_distance_to) if n_units else None
        closest_list = [u for u in [closest_p_unit, closest_e_unit, closest_n_unit] if u is not None]

        if closest_list:
            unit_id = min(closest_list, key=lambda u: u.last_distance_to).tag
            if unit_id in p_units.values('tag', flat_list=True):
                alignment = "own"
            elif unit_id in e_units.values('tag', flat_list=True):
                alignment = "enemy"
            else:
                alignment = "neutral"
            return {"ids": [unit_id], "alignment": alignment}
        return None
