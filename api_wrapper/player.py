import asyncio
from .server import Server
import portpicker
import websockets
import s2clientprotocol.sc2api_pb2 as api;
import s2clientprotocol.common_pb2 as common;
class Player():
    def __init__(self, race, type, difficulty=None, server=None, server_route=None, server_address=None):
        self.race = race
        self.type = type
        self.difficulty = difficulty
        self.server = server
        self.isComputer = type == "Computer"
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
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
    async def advance_time(self, step=100):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.server.address, self.server.port)) as websocket:
            await websocket.send(request_payload.SerializeToString())
            response = await websocket.recv()
            response = api.Response.FromString(response)
            return response
            
    