from players.objectives import ObjectivesPlayer
from pymongo import MongoClient
import datetime

class CBRPlayer(ObjectivesPlayer):
    def __init__(self, race, obj_type, process_time, oponent_race, db_name, db_host, db_port, difficulty=None, server=None, server_route=None, server_address=None, weights=None, **kwargs):
        if not weights:
            self.weights = [120] + [1 for x in range(0,19)] + [-1]
        else:
            self.weights = weights
        self.LOOP_RANGE = 0
        self.MINERALS = 1
        self.VESPENE = 2
        self.GAME_LOOP = 3
        self.FOOD_CAP = 4
        self.FOOD_USED = 5
        self.FOOD_ARMY = 6
        self.FOOD_WORKERS = 7
        self.IDLE_WORKERS = 8
        self.VISIBILITY = 9
        self.CREEP = 10
        self.ARMY = 11
        self.GATES = 12
        self.UNITS = 13
        self.ENEMY_UNITS = 14
        self.UPGRADES = 15
        self.VISIBLE_ENEMY = 16
        self.SNAPSHOT_ENEMY = 17
        self.GAMES = 18
        self.WINS = 19
        self.DISTANCE = 20
        self.client = MongoClient(db_host, db_port)
        self.db = self.client["11"]
        self.collection = self.db.cases
        self.process_time = process_time
        super().__init__(race, obj_type, difficulty, server, server_route, server_address, **kwargs)
    
    async def process_step(self, ws, game_state, actions=None):
        start_time = datetime.datetime.now()
        situation = game_state.to_case({"map" : "Interloper LE"})
        start = 0 if situation["game_loop"] - self.weights[self.LOOP_RANGE] < 0 else situation["game_loop"] - self.weights[self.LOOP_RANGE]
        end = situation["game_loop"] + self.weights[self.LOOP_RANGE]
        cases = list(self.collection.find({"map":situation["map"], "game_loop" : {"$lt" : end, "$gt" : start}}))
        
        best_case = cases[0]
        best_fitness = self.get_fittness(situation, cases[0])
        i = 1
        while (((datetime.datetime.now() - start_time).total_seconds() * 1000) < self.process_time) and i < len(cases):
            case_fitness = self.get_fittness(situation, cases[i])
            if case_fitness > best_fitness:
                best_case = cases[i]
                best_fitness = case_fitness
                i += 1
        
        print(best_case, best_fitness)

                

            

        
        # print(self.resolve_dependencies(UnitTypeIds.MARINE.value))
        # if self.orders or self.current_order is not None:
        #     await self.process_next_order(ws, game_state)
        # else:
        #     self.prepare_orders(game_state)
    
    def get_distance(self, situation, case):
        distance = 0
        distance += self.weights[self.MINERALS] * abs(situation["minerals"] - case["minerals"])
        distance += self.weights[self.VESPENE] * abs(situation["vespene"] - case["vespene"])
        distance += self.weights[self.GAME_LOOP] * abs(situation["game_loop"] - case["game_loop"])
        distance += self.weights[self.FOOD_CAP] * abs(situation["food_cap"] - case["food_cap"])
        distance += self.weights[self.FOOD_ARMY] * abs(situation["food_army"] - case["food_army"])
        distance += self.weights[self.FOOD_WORKERS] * abs(situation["food_workers"] - case["food_workers"])
        distance += self.weights[self.IDLE_WORKERS] * abs(situation["idle_worker_count"] - case["idle_worker_count"])
        distance += self.weights[self.VISIBILITY]  * abs(situation["visibility_percentage"] - case["visibility_percentage"])
        distance += self.weights[self.CREEP]  * abs(situation["creep_percentage"] - case["creep_percentage"])
        distance += self.weights[self.ARMY]  * abs(situation["army_count"] - case["army_count"])
        distance += self.weights[self.GATES]  * abs(situation["warp_gate_count"] - case["warp_gate_count"])


        for unit in situation["units"]:
            common_unit_ammount = 0
            for caunit in case["units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.UNITS] * abs(unit["amount"] - common_unit_ammount)
        

        for unit in case["units"]:
            common_unit_ammount = 0
            for caunit in situation["units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.UNITS] * abs(unit["amount"] - common_unit_ammount)
        
        for unit in situation["enemy_units"]:
            common_unit_ammount = 0
            for caunit in case["enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.ENEMY_UNITS] * abs(unit["amount"] - common_unit_ammount)
        

        for unit in case["enemy_units"]:
            common_unit_ammount = 0
            for caunit in situation["enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.ENEMY_UNITS] * abs(unit["amount"] - common_unit_ammount)
        
        for unit in situation["visible_enemy_units"]:
            common_unit_ammount = 0
            for caunit in case["visible_enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.VISIBLE_ENEMY] * abs(unit["amount"] - common_unit_ammount)
        

        for unit in case["visible_enemy_units"]:
            common_unit_ammount = 0
            for caunit in situation["visible_enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.VISIBLE_ENEMY] * abs(unit["amount"] - common_unit_ammount)
        
        for unit in situation["known_invisible_enemy_units"]:
            common_unit_ammount = 0
            for caunit in case["known_invisible_enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.VISIBLE_ENEMY] * abs(unit["amount"] - common_unit_ammount)
        

        for unit in case["known_invisible_enemy_units"]:
            common_unit_ammount = 0
            for caunit in situation["known_invisible_enemy_units"]:
                if unit["unit_type_ id"] == caunit["unit_type_ id"]:
                    common_unit_ammount = caunit["amount"]
            distance += self.weights[self.SNAPSHOT_ENEMY] * abs(unit["amount"] - common_unit_ammount)

        
        for upgrade in situation["upgrades"]:
            if upgrade not in case["upgrades"]:
                distance += self.weights[self.UPGRADES]
        for upgrade in case["upgrades"]:
            if upgrade not in situation["upgrades"]:
                distance += self.weights[self.UPGRADES]
        return distance
    
    def get_fittness(self, situation, case):
        distance = self.get_distance(situation, case)
        confidence = case["played_in_games"]
        results = case["wins"]
        return (self.weights[self.DISTANCE] * distance + self.weights[self.GAMES] * confidence + self.weights[self.WINS] * results)
        