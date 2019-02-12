from players.objectives import ObjectivesPlayer
from pymongo import MongoClient
import datetime
import json
import random
from api_wrapper.utils import obs_to_case

class CBRAlgorithm(ObjectivesPlayer):
    async def create(self, race, obj_type, difficulty=None, server=None, server_route=None, server_address=None,cases=None,**kwargs):
        self.cases = cases
        await super().create(race, obj_type,difficulty,server, server_route, server_address, **kwargs)

    async def process_step(self, ws, game_state, raw=None, actions=None):
        situation = obs_to_case(raw[0], raw[1])
        print(situation["loop"])
        probabilities_per_case = []
        actions = []
        if self.cases:
            for case in self.cases:
                case_evaluation = self.evaluate_case(situation, case) #I take the first case and evaluate it
                probabilities_per_case.append([case,case_evaluation])
            items = probabilities_per_case
            items = sorted(items, key=lambda x : x[1])
            items = items[-100:]

            total = sum(map(lambda x : x[1], items))
            items = map(lambda x : [x[0],x[1]/total], items)
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

            actions = selected_case["actions"]                #List of actions for the case
            if actions:
                list_of_actions = []
                for action in actions:
                    random_number_action = random.uniform(0, 1)
                    if random_number_action <= self.evaluate_action(action):
                        list_of_actions.append(action)
                actions = list_of_actions
        print(actions)
        

    #Returns the distance between two cases    
    def get_distance(self, situation, case):
        distance = 0
        distance += abs(situation["minerals"] - case["observation"]["minerals"])
        distance += abs(situation["vespene"] - case["observation"]["vespene"])
        distance += abs(situation["foodCap"] - case["observation"]["foodCap"])
        distance += abs(situation["foodUsed"] - case["observation"]["foodUsed"])
        distance += abs(situation["foodArmy"] - case["observation"]["foodArmy"])
        distance += abs(situation["foodWorkers"] - case["observation"]["foodWorkers"])
        distance += abs(situation["idleWorkerCount"] - case["observation"]["idleWorkerCount"])
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
        distance = self.get_distance(situation, case)
        #distance = 0
        case_eval = (count / (count + 10)) * (((2 * won) / count) - 1) * (1 / (1 + distance))
        return case_eval

    #Returns te action evaluation
    def evaluate_action(self, action):
        rate = action["wins"]/action["games"]
        return rate

    def units_distance(self, unit1, unit2):
        distance = 0
        if unit1["display"] != unit2["display"]:
            distance += 1
        if unit1["alliance"] != unit2["alliance"]:
            distance += 1
        distance += abs(unit1["health"] - unit2["health"]) 
        distance += abs(unit1["buildProgress"] - unit2["buildProgress"])
        distance += ((unit1["position"]["x"] - unit2["position"]["x"]) ** 2  + (unit1["position"]["y"] - unit2["position"]["y"]) ** 2) ** (1/2)
        return distance