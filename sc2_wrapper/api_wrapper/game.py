from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
import portpicker
import websockets
import uuid
from sc2_wrapper.game_data.observations import DecodedObservation


class Game():
    def __init__(self):
        self.status = 'init' 

class PlayedGame(Game):
    def __init__(self, map):
        self.map = map
        super().__init__()
    async def get_replay(self, filename="Example.SC2Replay"):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            if self.status == "finished":
                replay = api.Request(save_replay=api.RequestSaveReplay())
                await ws.send(replay.SerializeToString())
                _replay_response = await ws.recv()
                replay_response = api.Response.FromString(_replay_response)
                with open("Replays/Replay" + str(uuid.uuid4()) + ".SC2Replay", "wb") as f:
                    f.write(replay_response.save_replay.data)
        self.host.status = "idle"
            
class IAVSIA(PlayedGame):
    def __init__(self, map, server_route, server_address, players):
        self.server = server_route
        self.address = server_address
        self.players = players
        super().__init__(map)

    async def create(self):
        port = portpicker.pick_unused_port()
        self.host = await Server.get_server(self.server, self.address, str(port))
    async def start_game(self):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            for player in self.players:
                player1 = request_payload.create_game.player_setup.add()
                player1.type = dict(api.PlayerType.items())['Computer']
                player1.difficulty = dict(api.Difficulty.items())[
                    player.difficulty]
                player1.race = dict(common.Race.items())[player.race]
                player.server = self.host

            observer = request_payload.create_game.player_setup.add()
            observer.type = dict(api.PlayerType.items())['Observer']


            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            print(response)
            self.status = "created"

            request_payload = api.Request()
            request_payload.join_game.observed_player_id = 2
            request_payload.join_game.options.raw = True
            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            self.status = "started"

    async def simulate(self, step=300):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            seconds = 0
            while self.status == "started":
                request_payload = api.Request()
                request_payload.step.count = step
                await ws.send(request_payload.SerializeToString())
                result = await ws.recv()
                response = api.Response.FromString(result)
                seconds += 1
                print(seconds / 60)
                if response.status == 3:
                    self.status = "started"
                else:
                    self.status = "finished"

class PlayerVSIA(PlayedGame):
    def __init__(self, map, player, computer):
        self.computer = computer
        self.player = player
        super().__init__(map)

    async def create(self):
        self.host = self.player.server

    async def start_game(self):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())['Computer']
            player1.difficulty = dict(api.Difficulty.items())[
                self.computer.difficulty]
            player1.race = dict(common.Race.items())[self.computer.race]
            self.player.server = self.host

            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())['Participant']

            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            print(response)
            self.status = "created"

            request_payload = api.Request()
            request_payload.join_game.race = dict(common.Race.items())[
                self.player.race]

            request_payload.join_game.options.raw = True
            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            self.status = "started"

    async def simulate(self, step=300):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            seconds = 0
            while self.status == "started":
                results = [await self.player.advance_time(step)]
                if results[0].status == 3:
                    self.status = "started"
                else:
                    self.status = "finished"

class PlayerVSPlayer(PlayedGame):
    def __init__(self, map, players):
        self.players = players
        self.shared_port = portpicker.pick_unused_port()
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        super().__init__(map)
    
    async def create(self):
        self.host = self.players[0].server

    async def get_replay(self, filename="Example.SC2Replay"):
        await super().get_replay(filename)
        results = await asyncio.gather(
            self.players[0].leave_game(),
            self.players[1].leave_game()
        )
    async def start_game(self):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            # Create slots
            for player in self.players:
                player1 = request_payload.create_game.player_setup.add()
                player1.type = dict(api.PlayerType.items())['Participant']

            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            print(response)
            self.status = "created"

            tasks = []
            port_config = {'players_ports': [], 'shared_port': self.shared_port,
                            'base_port': self.base_port, 'game_port': self.game_port}
            for human in self.players:
                player_port = {'base_port': human.base_port,
                                'game_port': human.game_port}
                port_config['players_ports'].append(player_port)

            for human in self.players:
                tasks.append(asyncio.ensure_future(
                    human.join_game(port_config)))
            for task in tasks:
                response = await task
                if response.status != 3:
                    self.status = "launched"
            if self.status == "created":
                self.status = "started"

    async def simulate(self, step=300):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            seconds = 0
            while self.status == "started":
                tasks = []
                results = await asyncio.gather(
                    self.players[0].advance_time(step),
                    self.players[1].advance_time(step)
                )
                if results[0].status == 3:
                    self.status = "started"
                else:
                    self.status = "finished"

class Replay(Game):
    def __init__(self, server, address):
        self.server = server
        self.address = address
        self.replay_info = None

    async def create(self):
        port = portpicker.pick_unused_port()
        self.host = await Server.get_server(self.server, self.address, str(port))

    async def load_replay(self, replay_file, id=0):
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            replay_meta = api.Request(
                replay_info=api.RequestReplayInfo(replay_path=replay_file))
            await ws.send(replay_meta.SerializeToString())
            result = await ws.recv()
            metadata = api.Response.FromString(result)
            self.replay_info = {
                "map": metadata.replay_info.map_name,
                "races": [metadata.replay_info.player_info[0].player_info.race_requested, metadata.replay_info.player_info[1].player_info.race_requested],
                "results": [metadata.replay_info.player_info[0].player_result.result, metadata.replay_info.player_info[1].player_result.result]
            }
            msg = api.Request(start_replay=api.RequestStartReplay(replay_path=replay_file,
                                                                  observed_player_id=id, options=api.InterfaceOptions(raw=True, score=False)))

            await ws.send(msg.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            self.status = "started"

    async def observe_replay(self, step=300, id=0):
        cases = []
        async with websockets.connect("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)) as ws:
            while self.status == "started" or self.status == "replay":
                request_payload = api.Request()
                request_payload.observation.disable_fog = False
                await ws.send(request_payload.SerializeToString())
                result = await ws.recv()
                response = api.Response.FromString(result)

                request_data = api.Request(data=api.RequestData(
                    ability_id=True, unit_type_id=True, upgrade_id=True))
                await ws.send(request_data.SerializeToString())
                result = await ws.recv()
                data_response = api.Response.FromString(result)
                game_data = data_response.data

                observation = DecodedObservation(
                    response.observation.observation, game_data, list(response.observation.actions))

                case = observation.to_case(self.replay_info)
                print(case["game_loop"])
                cases.append(case)
                request_payload = api.Request()
                request_payload.step.count = step
                await ws.send(request_payload.SerializeToString())
                result = await ws.recv()
                response = api.Response.FromString(result)
                if response.status == 4:
                    self.status = "replay"
                else:
                    self.status = "finished"
            self.host.status = "idle"
        result = {"metadata": self.replay_info, "cases":cases, "player_id": id-1}
        return result

class Classifier(Replay):
    async def observe_replay(self, step=300, id=0):
        return self.replay_info
        