import asyncio
import traceback
from collections import namedtuple

from sc2_wrapper.constants.ability_ids import AbilityId
from sc2_wrapper.game_data import decode_observation
from sc2_wrapper.game_data.action import Action
from sc2_wrapper.game_data import UnitManager
from .server import Server
import portpicker
import websockets
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
import s2clientprotocol.query_pb2 as query


class Player():
    async def create(self, race, type, difficulty=None, server=None, server_route=None, server_address=None, **kwargs):
        self.race = race
        self.type = type
        self.difficulty = difficulty
        self.server = server
        self.isComputer = type == "Computer"
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        self.decision_function = lambda x, y: None
        # if server:
        #     self.websocket = websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port))
        if (not self.server) and (self.type != 'Computer'):
            port = portpicker.pick_unused_port()
            self.server = await Server.get_server(server_route, server_address, str(port))
            # self.websocket = websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port))

    async def join_game(self, port_config):
        request_payload = api.Request()
        request_payload.join_game.race = dict(common.Race.items())[self.race]
        request_payload.join_game.server_ports.base_port = port_config["base_port"]
        request_payload.join_game.server_ports.game_port = port_config["game_port"]
        request_payload.join_game.shared_port = port_config["shared_port"]
        for config in port_config["players_ports"]:
            ports = request_payload.join_game.client_ports.add()
            ports.base_port = config["base_port"]
            ports.game_port = config["game_port"]
        request_payload.join_game.options.raw = True
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)) as websocket:
            await websocket.send(request_payload.SerializeToString())
            response = await websocket.recv()
            response = api.Response.FromString(response)
            return response

    async def leave_game(self):
        request_payload = api.Request(leave_game=api.RequestLeaveGame())
        self.server.status = "idle"
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
                        action = Action(
                            unit=unit, ability_id=ab.ability_id, require_target=True)
                    else:
                        action = Action(unit=unit, ability_id=ab.ability_id)
                    available_actions.append(action)
        return available_actions

    async def process_step(self, ws, game_state, actions=None):
        pass

    async def play(self, ws, observation):
        success = True
        request_data = api.Request(data=api.RequestData(
            ability_id=True, unit_type_id=True, upgrade_id=True))
        await asyncio.wait_for(ws.send(request_data.SerializeToString()), 5)
        try:
            result = await asyncio.wait_for(ws.recv(), 5)
            data_response = api.Response.FromString(result)
            game_data = data_response.data
            # If game is still on
            if game_data.units:
                obj = decode_observation(
                    observation.observation.observation, game_data)
                await self.process_step(ws, obj)
                # function = self.decision_function
                # alvailable_actions = self.query_alvailable_actions()
                # to_do_action = function(observation, alvailable_actions)
                # while(to_do_action and alvailable_actions):
                #    self.send_order(self, to_do_action)
                #    to_do_action = self.query_alvailable_actions()
        except asyncio.TimeoutError:
            return False
        return True

    async def advance_time(self, step=100):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)) as ws:
            request_payload = api.Request()
            request_payload.observation.disable_fog = True
            DefaultObs = namedtuple('Observation', "status")
            observation = DefaultObs(3)

            try:
                await asyncio.wait_for(ws.send(request_payload.SerializeToString()), 5)
                result = await asyncio.wait_for(ws.recv(), 5)
                observation = api.Response.FromString(result)
                successfull = True
                if(not self.isComputer):
                    await self.play(ws, observation)
                request_payload = api.Request()
                request_payload.step.count = step
                await asyncio.wait_for(ws.send(request_payload.SerializeToString()), 5)
                result = await asyncio.wait_for(ws.recv(), 5)
                response = api.Response.FromString(result)
            except:
                print(traceback.print_exc())
                print("Error during advance time, ignoring observation")
            return observation

    # Player support tools
    def select_idle_workers(self, game_state, number=None):
        # TODO: Select according to race
        worker_id = "SCV"

        idle_workers = game_state.player_units.filter(
            name=worker_id, orders=[])

        # Returning workers
        harvest_return_abilities = [
            ability.value for ability in AbilityId if ability.name.startswith("HARVEST_RETURN")]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(
                name=worker_id, orders__ability_id=ability_id)

        # Gathering workers
        harvest_return_abilities = [
            ability.value for ability in AbilityId if ability.name.startswith("HARVEST_GATHER")]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(
                name=worker_id, orders__ability_id=ability_id)

        # Return manager with idle workers
        if number is not None:
            return UnitManager(idle_workers[:number])
        else:
            return UnitManager(idle_workers)

