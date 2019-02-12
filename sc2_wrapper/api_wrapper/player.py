import asyncio
import traceback
from collections import namedtuple

from constants.ability_ids import AbilityId
from game_data.observations import decode_observation
from game_data.action import Action
from game_data.units import UnitManager
from .server import Server
import portpicker
import websockets
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
import s2clientprotocol.query_pb2 as query
from google.protobuf.json_format import MessageToDict
import json

class Player:
    async def create(
        self,
        race,
        type,
        difficulty=None,
        server=None,
        server_route=None,
        server_address=None,
        **kwargs
    ):
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
        if (not self.server) and (self.type != "Computer"):
            port = portpicker.pick_unused_port()
            self.server = await Server.get_server(
                server_route, server_address, str(port)
            )
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
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)
        ) as websocket:
            await websocket.send(request_payload.SerializeToString())
            response = await websocket.recv()
            response = api.Response.FromString(response)
            return response

    async def leave_game(self):
        request_payload = api.Request(leave_game=api.RequestLeaveGame())
        self.server.status = "idle"
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)
        ) as websocket:
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
                            unit=unit, ability_id=ab.ability_id, require_target=True
                        )
                    else:
                        action = Action(unit=unit, ability_id=ab.ability_id)
                    available_actions.append(action)
        return available_actions

    async def process_step(self, ws, game_state, raw=None, actions=None):
        pass

    async def play(self, ws, observation):
        success = True
        request_data = api.Request(
            data=api.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True)
        )
        await asyncio.wait_for(ws.send(request_data.SerializeToString()), 5)
        try:
            result = await asyncio.wait_for(ws.recv(), 5)
            data_response = api.Response.FromString(result)
            game_data = data_response.data

            request_game_info = api.Request(game_info=api.RequestGameInfo())
            await asyncio.wait_for(ws.send(request_game_info.SerializeToString()), 5)
            result = await asyncio.wait_for(ws.recv(), 5)
            game_info_response = api.Response.FromString(result)

            # If game is still on
            if game_data.units:
                obj = decode_observation(observation.observation.observation, game_data, game_info_response)
                obs = MessageToDict(observation)
                obs = str(obs)
                obs = obs.replace("\'", "\"")
                obs = obs.replace("False", "false")
                obs = obs.replace("True", "true")
                obs = json.loads(obs,encoding="UTF-8")
                game_meta = api.Request(
                    game_info=api.RequestGameInfo()
                )
                await ws.send(game_meta.SerializeToString())
                result = await ws.recv()
                game_meta = api.Response.FromString(result)
                game_meta = MessageToDict(game_meta)
                game_meta = str(game_meta)
                game_meta = game_meta.replace("\'", "\"")
                game_meta = game_meta.replace("False", "false")
                game_meta = game_meta.replace("True", "true")
                game_meta = json.loads(game_meta,encoding="UTF-8")
                game_meta = game_meta.get("gameInfo", None)
                game_meta.pop("modNames")
                game_meta.pop("options")
                game_meta.pop("mapName")
                if("localMapPath" in game_meta.keys()):
                    game_meta.pop("localMapPath")
                game_meta.pop("playerInfo")
                game_meta.update(game_meta["startRaw"])
                game_meta.pop("startRaw")
                game_meta.pop("mapSize")
                await self.process_step(ws, obj, raw=(obs, game_meta))
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
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)
        ) as ws:
            request_payload = api.Request()
            request_payload.observation.disable_fog = True
            DefaultObs = namedtuple("Observation", "status")
            observation = DefaultObs(3)

            try:
                await asyncio.wait_for(ws.send(request_payload.SerializeToString()), 5)
                result = await asyncio.wait_for(ws.recv(), 5)
                observation = api.Response.FromString(result)
                successfull = True
                if not self.isComputer:
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

        idle_workers = game_state.player_units.filter(name=worker_id, orders=[])

        # Returning workers
        harvest_return_abilities = [
            ability.value
            for ability in AbilityId
            if ability.name.startswith("HARVEST_RETURN")
        ]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(
                name=worker_id, orders__ability_id=ability_id
            )

        # Gathering workers
        harvest_return_abilities = [
            ability.value
            for ability in AbilityId
            if ability.name.startswith("HARVEST_GATHER")
        ]
        for ability_id in harvest_return_abilities:
            idle_workers += game_state.player_units.filter(
                name=worker_id, orders__ability_id=ability_id
            )

        # Return manager with idle workers
        if number is not None:
            return UnitManager(idle_workers[:number])
        else:
            return UnitManager(idle_workers)

