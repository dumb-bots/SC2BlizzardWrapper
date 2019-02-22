import random
from api_wrapper.utils import obs_to_case, get_quadrant_position, get_quadrant_min_side, UnitInfluenceArea, own_minerals_distance
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
        if (game_state.game_loop > 40000):
            await self.leave_game()


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
            if not look_cases and situation["loop"] > 40000:
                keys = sorted(self.cases_by_loop.keys())[-10:]
                look_cases = self.cases_by_loop[keys[random.randint(0,9)]]
            if not look_cases:
                return actions
            unit_data = {u.unit_id: u for u in raw[2].units}
            start = time.time()
            for case in look_cases:
                case_evaluation = self.evaluate_case(situation, case, unit_data)  # I take the first case and evaluate it
                probabilities_per_case.append([case, case_evaluation])
            print("Distance calculation time: {}s".format(time.time() - start))
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
                        list_of_actions.append([action, self.evaluate_action(action) * action["games"] / float(selected_case["games"])])
                    maximum_fitness = max(map(lambda x: x[1], list_of_actions))
                    list_of_actions = list(map(lambda x: [x[0], x[1] / maximum_fitness], list_of_actions))
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
        distance += abs(situation["loop"] - case["observation"]["loop"])

        # New format
        if situation.get('food') is not None:
            if case['observation'].get('food') is not None:
                distance += abs(situation["food"] - case["observation"]["food"]) * 100
            else:
                distance += abs(
                    situation["food"] - (case["observation"]["foodCap"] - case["observation"]["foodUsed"])
                ) * 100
        elif situation.get('foodCap') is not None:
            distance += abs(situation["foodCap"] - case["observation"]["foodCap"]) * 100
            distance += abs(situation["foodUsed"] - case["observation"]["foodUsed"]) * 100
            distance += abs(situation["foodArmy"] - case["observation"]["foodArmy"])
            distance += abs(situation["foodWorkers"] - case["observation"]["foodWorkers"])
            distance += abs(situation["idleWorkerCount"] - case["observation"]["idleWorkerCount"]) * 100
            distance += abs(situation["armyCount"] - case["observation"]["armyCount"])
            distance += abs(situation["warpGateCount"] - case["observation"]["warpGateCount"])
        else:
            print(situation)

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
    def evaluate_case(self, situation, case, game_data=None):
        won = case["wins"]
        count = case["games"]
        lost = case["looses"]
        distance = own_minerals_distance(situation, case["observation"], game_data)
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
        target_unit, target_point = self._target_unit_from_action(action, target_point, game_state)

        # if action_id == 1 and not target_unit:
        if action_id == 1:
            return

        # Check Build Actions
        built_unit = BUILD_ABILITY_UNIT.get(action_id)
        if UNIT_DEPENDENCIES.get(built_unit):
            if UNIT_DATA.get(built_unit, {}).get('food_required', 0) > 0:
                return actions.Train(built_unit)
            elif built_unit == UnitTypeIds.COMMANDCENTER.value:
                return actions.Expansion(target_point)
            else:
                target_point = self.process_build_target_point(target_point, game_state)
                return actions.Build(built_unit, target_point)

        # Check upgrades
        upgrade_id = UPGRADE_ABILITY_MAPPING.get(action_id)
        if upgrade_id:
            return actions.Upgrade(upgrade_id)

        # Check Unit Actions
        if action_id in [AbilityId.ATTACK_ATTACK.value, AbilityId.ATTACK.value]:
            unit_group = self.redefine_attacking_unit_group(unit_group, game_state)
            target_point = self.redefine_attack_target_point(target_point, game_state)
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

    def _target_unit_from_action(self, action, target_point, game_state):
        target_unit = action.get('targetUnit')
        if target_unit:
            unit_info = self._get_unit_info(game_state, target_unit)
            if unit_info:
                return unit_info, target_point
            else:
                return None, (target_unit['position']['x'], target_unit['position']['y'])
        return None, target_point

    def _get_unit_info(self, game_state, target_unit):
        unit_type = target_unit['type']
        unit_position = target_unit['position']['x'], target_unit['position']['y']
        if target_unit['alliance'] == 'Self':
            alignment = "own"
            unit_group = game_state.player_units
        elif target_unit['alliance'] == 'Enemy':
            alignment = "enemy"
            unit_group = game_state.enemy_units
        elif target_unit['alliance'] == 'Neutral':
            alignment = "neutral"
            unit_group = game_state.neutral_units
        else:
            return None

        p_units = unit_group.filter(unit_type=unit_type).add_calculated_values(
            distance_to={'pos': unit_position})
        if p_units:
            unit = min(p_units, key=lambda u: u.last_distance_to) if p_units else None
            if unit.last_distance_to > 30:
                return None

            unit_id = unit.tag
            return {"ids": [unit_id], "alignment": alignment}
        else:
            return None

    @staticmethod
    def redefine_attack_target_point(target_point, game_state):
        if target_point is None:
            return target_point

        closest_enemy = min(
            game_state.enemy_units.add_calculated_values(distance_to={"pos": target_point}),
            key=lambda unit: unit.last_distance_to,
        )
        if closest_enemy.last_distance_to > get_quadrant_min_side(game_state):
            redefined_target_point = get_quadrant_position(closest_enemy, game_state)
            return redefined_target_point
        return target_point

    @staticmethod
    def redefine_attacking_unit_group(unit_group, game_state):
        if not unit_group.get('composition'):
            return unit_group

        new_composition = {}
        for k, v in unit_group['composition'].items():
            unit = CBRAlgorithm.get_attacking_unit(k, v, game_state)
            new_composition[unit] = v
        return {'composition': new_composition}

    @staticmethod
    def get_attacking_unit(unit_id, number, game_state):
        attacking_unit_id = unit_id
        # Let's not send SCVs to the war, they are better off working
        if unit_id == UnitTypeIds.SCV.value:
            attacking_unit_id = UnitTypeIds.MARINE.value
        # It ain't going anywhere without micro
        elif unit_id == UnitTypeIds.SIEGETANKSIEGED.value:
            attacking_unit_id = UnitTypeIds.SIEGETANK.value

        # Need build + ability to get one
        elif unit_id == UnitTypeIds.VIKINGASSAULT.value:
            if len(game_state.player_units.filter(unit_type=UnitTypeIds.VIKINGASSAULT.value)) < number:
                attacking_unit_id = UnitTypeIds.VIKINGFIGHTER.value
        # Need build + ability to get one
        elif unit_id == UnitTypeIds.HELLIONTANK.value:
            if len(game_state.player_units.filter(unit_type=UnitTypeIds.HELLIONTANK.value)) < number:
                attacking_unit_id = UnitTypeIds.HELLION.value
        # Need build + ability to get one
        elif unit_id == UnitTypeIds.LIBERATORAG.value:
            if len(game_state.player_units.filter(unit_type=UnitTypeIds.LIBERATORAG.value)) < number:
                attacking_unit_id = UnitTypeIds.LIBERATOR.value
        return attacking_unit_id

    @staticmethod
    def process_build_target_point(target_point, game_state):
        if target_point is None:
            return target_point

        town_halls = game_state.player_units.filter(unit_type__in=[
            UnitTypeIds.COMMANDCENTER.value,
            UnitTypeIds.PLANETARYFORTRESS.value,
            UnitTypeIds.ORBITALCOMMAND.value,
        ])
        town_hall_influence_areas = map(lambda th: UnitInfluenceArea(th, game_state), town_halls)
        if not any(map(
                lambda i_area: i_area.point_in_influence_area(target_point, game_state),
                town_hall_influence_areas
        )):
            target_point = None
        return target_point
