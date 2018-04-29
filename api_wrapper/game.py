from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api;
import s2clientprotocol.common_pb2 as common;
from websocket import create_connection
RESTARTS = 100
class Game():
    port = 9000
    def __init__(self, players=[], map="", host=None, server_route=None, server_address=None):
        self.players = players
        self.map = map
        self.host = host
        self.status = 'init'
        port = Game.port
        for i in range(0, RESTARTS):
            port += 1
            print( port)
            self.host =  Server(server_route, server_address, str(port))
            loop = asyncio.get_event_loop()
            future = asyncio.Future()
            asyncio.ensure_future(self.host.start_server(future))
            try:
                loop.run_until_complete(future)
                Game.port = port
                break
            except Exception:
                pass

    def start_game(self):
        request_payload = api.Request()
        request_payload.create_game.local_map.map_path = self.map
        for player in self.players:
            if player.isComputer:
                player1 = request_payload.create_game.player_setup.add()
                player1.type = dict(api.PlayerType.items())['Computer']
                player1.difficulty = dict(api.Difficulty.items())[player.difficulty]
                player1.race = dict(common.Race.items())[player.race]

        observer = request_payload.create_game.player_setup.add()
        observer.type = dict(api.PlayerType.items())['Observer']
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        ws.send(request_payload.SerializeToString())
        result = ws.recv()
        self.status = "created"
        response = api.Response.FromString(result)
        request_payload = api.Request()
        request_payload.join_game.observed_player_id = 0
        request_payload.join_game.options.raw = True
        ws.send(request_payload.SerializeToString())
        result = ws.recv();
        response = api.Response.FromString(result)
        self.status = "started"

    async def simulate(self, step=300):
        game = ""
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        while self.status == "started":
            request_payload = api.Request()
            request_payload.observation.disable_fog = True
            ws.send(request_payload.SerializeToString())
            result = ws.recv()
            response = api.Response.FromString(result)

            game += str(response) + "\n\n"

            request_payload = api.Request()
            request_payload.step.count = 1000
            ws.send(request_payload.SerializeToString())
            result = ws.recv();
            response = api.Response.FromString(result)
            if response.status == 3:
                self.status = "started"
            else:
                self.status = "finished"


        log = open("log.txt", "w")
        log.write(game)
        log.close()