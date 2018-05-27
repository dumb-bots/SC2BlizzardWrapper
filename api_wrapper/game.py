from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api;
import s2clientprotocol.common_pb2 as common;
from websocket import create_connection
import portpicker
import websockets
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
    def load_replay(self, replay_file, id=0):
        msg = api.Request(start_replay=api.RequestStartReplay(replay_path=replay_file, observed_player_id=id, options=api.InterfaceOptions(raw=True, score=False)))
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        ws.send(msg.SerializeToString())
        result = ws.recv()
        response = api.Response.FromString(result)
        self.status = "started"
        print (response)

    async def start_game(self):
        request_payload = api.Request()
        request_payload.create_game.local_map.map_path = self.map
        
        for player in self.computers:
            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())['Computer']
            player1.difficulty = dict(api.Difficulty.items())[player.difficulty]
            player1.race = dict(common.Race.items())[player.race]
            player.server = self.host

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
        print (response)
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
            self.status = "started"
        else:
            tasks = []
            port_config = {'players_ports':[], 'shared_port': self.shared_port, 'base_port': self.base_port, 'game_port': self.game_port}
            for human in self.human_players:
                player_port = {'base_port': human.base_port, 'game_port': human.game_port}
                port_config['players_ports'].append(player_port)
                
            for human in self.human_players:    
                tasks.append(asyncio.ensure_future(human.join_game(port_config)))
            for task in tasks:
                response = await task
                if response.status != 3:
                    self.status = "launched"
            if self.status == "created":
                self.status = "started"
    def get_replay(self, filename="Example.SC2Replay"):
        if self.status == "finished":
            ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
            replay = api.Request(save_replay=api.RequestSaveReplay())
            ws.send(replay.SerializeToString())
            _replay_response = ws.recv()
            replay_response = api.Response.FromString(_replay_response)
            with open("Example.SC2Replay", "wb") as f:
                f.write(replay_response.save_replay.data)
        self.host.process.terminate()
    async def simulate(self, step=300):
        game = ""
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        while self.status == "started" or self.status == "replay":
            if not self.human_players:
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
                if response.status == 3 :
                    self.status = "started"
                elif response.status == 4:
                    self.status = "replay"
                else:
                    self.status = "finished"
            else:
                tasks = []
                for player in self.human_players:
                    tasks.append(asyncio.ensure_future(player.advance_time(step)))
                for task in tasks:
                    results = await task
                    game += str(results)
                    if results.status == 3:
                        self.status = "started"
                    else:
                        self.status = "finished"
        for player in self.human_players:
            if player.server != self.host:
                player.server.process.terminate()
        log = open("log.txt", "w")
        log.write(game)
        log.close()