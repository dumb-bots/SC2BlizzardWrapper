import asyncio

from constants.ability_ids import AbilityId
from constants.unit_type_ids import UnitTypeIds
from game_data.observations import decode_observation
from game_data.action import Action
from game_data.units import UnitManager
from .server import Server
import portpicker
import websockets
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
import s2clientprotocol.query_pb2 as query
from websocket import create_connection

class Player():
    def __init__(self, race, type, difficulty=None, server=None, server_route=None, server_address=None, **kwargs):
        self.race = race
        self.type = type
        self.difficulty = difficulty
        self.server = server
        self.isComputer = type == "Computer"
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        self.decision_function = lambda x,y:None
        # if server:
        #     self.websocket = websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port))
        if (not self.server) and (self.type != 'Computer'):
            port = portpicker.pick_unused_port()
            self.server =  Server(server_route, server_address, str(port))
            loop = asyncio.get_event_loop()
            future = asyncio.Future()
            asyncio.ensure_future(self.server.start_server(future))
            loop.run_until_complete(future)
            # self.websocket = websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port))

    async def join_game(self, port_config):
        request_payload = api.Request()
        request_payload.join_game.race =  dict(common.Race.items())[self.race]
        request_payload.join_game.server_ports.base_port = port_config["base_port"]
        request_payload.join_game.server_ports.game_port = port_config["game_port"]
        request_payload.join_game.shared_port = port_config["shared_port"]
        for config in port_config["players_ports"]:
            ports = request_payload.join_game.client_ports.add()
            ports.base_port= config["base_port"]
            ports.game_port= config["game_port"]
        request_payload.join_game.options.raw = True
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)) as websocket:
            await websocket.send(request_payload.SerializeToString())
            response = await websocket.recv()
            response = api.Response.FromString(response)
            return response

    def send_order(self, order):
        pass

    async def query_alvailable_actions(self, ws, game_state):
        units = game_state.player_units
        available_actions = []
        for unit in units:
            lookup = api.Request(query=query.RequestQuery())
            request_available = lookup.query.abilities.add()
            request_available.unit_tag = unit.tag
            await ws.send(lookup.SerializeToString())
            data = await ws.recv()
            data = api.Response.FromString(data)
            abilities = data.query.abilities
            for ability in abilities:
                for ab in ability.abilities:
                    if hasattr(ab, "requires_point"):
                        action = Action(unit=unit, ability_id=ab.ability_id, require_target = True)
                    else:
                        action = Action(unit=unit, ability_id=ab.ability_id)
                    available_actions.append(action)
        return available_actions
    async def process_step(self, ws, game_state, actions=None):
        pass

    async def play(self, ws, observation):
        request_data = api.Request(data=api.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True))
        await ws.send(request_data.SerializeToString())
        result = await ws.recv()
        data_response = api.Response.FromString(result)
        game_data = data_response.data
        # If game is still on
        if game_data.units:
            obj = decode_observation(observation.observation.observation, game_data)
            actions = await self.query_alvailable_actions(ws, obj)
            await self.process_step(ws, obj, actions)
            # function = self.decision_function
            # alvailable_actions = self.query_alvailable_actions()
            # to_do_action = function(observation, alvailable_actions)
            # while(to_do_action and alvailable_actions):
            #    self.send_order(self, to_do_action)
            #    to_do_action = self.query_alvailable_actions()


    async def advance_time(self, step=100):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)) as ws:
            request_payload = api.Request()
            request_payload.observation.disable_fog = True
            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            observation = api.Response.FromString(result)
            if(not self.isComputer):
                await self.play(ws, observation)

            request_payload = api.Request()
            request_payload.step.count = step
            await ws.send(request_payload.SerializeToString())
            result = await ws.recv();
            response = api.Response.FromString(result)
            return observation

    # Player support tools
    def select_idle_workers(self, game_state, number=None):
        # TODO: Select according to race
        worker_id = "SCV"

        idle_workers = game_state.player_units.filter(name=worker_id, orders=[])

        # Returning workers
        harvest_return_abilities = [ability.value for ability in AbilityId if ability.name.startswith("HARVEST_RETURN")]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(name=worker_id, orders__ability_id=ability_id)

        # Gathering workers
        harvest_return_abilities = [ability.value for ability in AbilityId if ability.name.startswith("HARVEST_GATHER")]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(name=worker_id, orders__ability_id=ability_id)

        # Return manager with idle workers
        if number is not None:
            return UnitManager(idle_workers[:number])
        else:
            return UnitManager(idle_workers)

    def select_related_minerals(self, game_state, town_hall):
        mineral_field_ids = [unit_type.value for unit_type in UnitTypeIds if "MINERALFIELD" in unit_type.name]
        neutral = game_state.neutral_units.add_calculated_values(distance_to={"unit": town_hall})
        return neutral.filter(unit_type__in=mineral_field_ids, last_distance_to__lte=10)

    def select_related_gas(self, game_state, town_hall):
        vespene_geyser_ids = [unit_type.value for unit_type in UnitTypeIds if "VESPENEGEYSER" in unit_type.name]
        neutral = game_state.neutral_units.add_calculated_values(distance_to={"unit": town_hall})
        return neutral.filter(unit_type__in=vespene_geyser_ids, last_distance_to__lte=10)
