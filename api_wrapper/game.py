from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api;
import s2clientprotocol.common_pb2 as common;
from websocket import create_connection
import portpicker
class Game():
    def __init__(self, players=[], map="", host=None, server_route=None, server_address=None):
        self.map = map
        self.host = host
        self.status = 'init'
        self.human_players = []
        self.computers = []
        self.shared_port = portpicker.pick_unused_port()
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        for player in players:
            if player.isComputer:
                self.computers.append(player)
            else:
                self.human_players.append(player)
        if self.human_players:
            self.host = self.human_players[0].server
        else:
            port = portpicker.pick_unused_port()
            self.host =  Server(server_route, server_address, str(port))
            loop = asyncio.get_event_loop()
            future = asyncio.Future()
            asyncio.ensure_future(self.host.start_server(future))
            loop.run_until_complete(future)

    def start_game(self):
        request_payload = api.Request()
        request_payload.create_game.local_map.map_path = self.map
        
        for player in self.computers:
            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())['Computer']
            player1.difficulty = dict(api.Difficulty.items())[player.difficulty]
            player1.race = dict(common.Race.items())[player.race]

        #Computer vs computer
        if not self.human_players:
            observer = request_payload.create_game.player_setup.add()
            observer.type = dict(api.PlayerType.items())['Observer']
        
        #Create slots
        for player in self.human_players:
            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())['Participant']

        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        ws.send(request_payload.SerializeToString())
        result = ws.recv()
        response = api.Response.FromString(result)
        print(response)
        self.status = "created"

        if len(self.human_players) < 2:
            request_payload = api.Request()
            if self.human_players:
                request_payload.join_game.race = dict(common.Race.items())[self.human_players[0].race]
            else:
                request_payload.join_game.observed_player_id = 2
            request_payload.join_game.options.raw = True
            ws.send(request_payload.SerializeToString())
            result = ws.recv();
            response = api.Response.FromString(result)
            print(response)
            self.status = "started"

        # if len(self.human_players) == 1:
            
        # for human in self.human_players:
        #     ws_player = create_connection("ws://{0}:{1}/sc2api".format(human.server.address, human.server.port))
        #     request_payload = api.Request()
        #     request_payload.join_game.race =  dict(common.Race.items())[human.race]
        #     ports = request_payload.join_game.client_ports.add()
        #     request_payload.join_game.server_ports.base_port = int(self.host.port) + 1
        #     request_payload.join_game.server_ports.game_port = int(self.host.port) + 1
        #     request_payload.join_game.shared_port = int(self.host.port) + 1
        #     ports.base_port= int(human.server.port) + 2
        #     ports.game_port= int(human.server.port) + 2
            
            # request_payload.join_game.options.raw = True
            # ws_player.send(request_payload.SerializeToString())
            # result = ws_player.recv();
            # response = api.Response.FromString(result)
            # print (response)
            # self.status = "started"

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