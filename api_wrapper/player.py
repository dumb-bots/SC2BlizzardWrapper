import asyncio

from constants.ability_ids import AbilityId
from game_data.observations import decode_observation
from .server import Server
import portpicker
import websockets
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common

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

    def query_alvailable_actions(self):
        return None

    async def process_step(self, ws, game_state):
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
            print(obj.to_dict())
            await self.process_step(ws, obj)
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
            
    