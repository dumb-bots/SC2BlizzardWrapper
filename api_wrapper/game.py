from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
from websocket import create_connection
import portpicker
import websockets
import time
import uuid
from game_data.observations import DecodedObservation
import pymongo

class Game():
    async def create(self, players=[], map="", host=None, server_route=None, server_address=None, matchup=""):
        self.map = map
        self.host = host
        self.status = 'init'
        self.human_players = []
        self.computers = []
        self.shared_port = portpicker.pick_unused_port()
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        self.replay_info = None
        self.required_matchup = matchup
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
            future = asyncio.Future()
            await self.host.start_server(future)
    def load_replay(self, replay_file, id=0):
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))

        replay_meta = api.Request(replay_info=api.RequestReplayInfo(replay_path=replay_file))
        ws.send(replay_meta.SerializeToString())
        result = ws.recv()
        metadata = api.Response.FromString(result)
        print("META " + str(metadata))
        self.replay_info = {
            "map": metadata.replay_info.map_name,
            "races": [metadata.replay_info.player_info[0].player_info.race_requested, metadata.replay_info.player_info[1].player_info.race_requested],
            "results": [metadata.replay_info.player_info[0].player_result.result, metadata.replay_info.player_info[1].player_result.result]
        }
        msg = api.Request(start_replay=api.RequestStartReplay(replay_path=replay_file, observed_player_id=id, options=api.InterfaceOptions(raw=True, score=False)))

        ws.send(msg.SerializeToString())
        result = ws.recv()
        response = api.Response.FromString(result)
        self.status = "started"
        ws.close()

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
            result = ws.recv()
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
            with open("Replays/Replay" + str(uuid.uuid4()) + ".SC2Replay", "wb") as f:
                f.write(replay_response.save_replay.data)
        self.host.process.terminate()
    async def simulate(self, step=300):
        game = ""
        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        seconds = 0
        while self.status == "started" or self.status == "replay":
            if not self.human_players:
                request_payload = api.Request()
                request_payload.step.count = step
                ws.send(request_payload.SerializeToString())
                result = ws.recv()
                response = api.Response.FromString(result)
                seconds += 1
                print(seconds / 60)
                if response.status == 3 :
                    self.status = "started"
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
        log = open("logs/log" + str(uuid.uuid4()) + ".txt", "w")
        log.write(game)
        log.close()

    async def observe_replay(self,step=300, client=None, id=0):
        matchup_string = ""
        if id == 1:
            matchup_string = str(self.replay_info["races"][0]) + str(self.replay_info["races"][1])
        else:
            matchup_string = str(self.replay_info["races"][1]) + str(self.replay_info["races"][0])
        if self.required_matchup:
            if self.required_matchup != matchup_string:
                print("Skipped " + matchup_string)
                return

        ws = create_connection("ws://{0}:{1}/sc2api".format(self.host.address, self.host.port))
        db = client[matchup_string]
        keyspace = db.cases
        insert_cases = []
        while self.status == "started" or self.status == "replay":
            request_payload = api.Request()
            request_payload.observation.disable_fog = False
            ws.send(request_payload.SerializeToString())
            result = ws.recv()
            response = api.Response.FromString(result)
            
            request_data = api.Request(data=api.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True))
            ws.send(request_data.SerializeToString())
            result = ws.recv()
            data_response = api.Response.FromString(result)
            game_data = data_response.data

            observation = DecodedObservation(response.observation.observation, game_data, list(response.observation.actions))
            
            case = observation.to_case(self.replay_info)
            if case["actions"]:
                search = keyspace.find_one(case)
                if search:
                    case.update({
                        "played_in_games" : search["played_in_games"] + 1,
                        "wins" : search["wins"] + 1 if self.replay_info["results"][id - 1] == 1 else search["wins"],
                        "_id" : search["_id"]
                    })
                    keyspace.update({"_id": case["_id"]}, case)
                else :
                    case.update({
                        "played_in_games": 1,
                        "wins": 1 if self.replay_info["results"][id - 1] == 1 else 0,
                    })
                    insert_cases.append(case)
            request_payload = api.Request()
            request_payload.step.count = step
            ws.send(request_payload.SerializeToString())
            result = ws.recv()
            response = api.Response.FromString(result)
            if response.status == 4 :
                self.status = "replay"
            else:
                self.status = "finished"
        if insert_cases:
            keyspace.insert_many(insert_cases)
        ws.close()

