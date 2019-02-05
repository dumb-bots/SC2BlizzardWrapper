from .server import Server
import asyncio
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.common_pb2 as common
import portpicker
import websockets
import uuid
from  game_data.observations import DecodedObservation
from google.protobuf.json_format import MessageToDict
import json
import time
import traceback

class Game:
    def __init__(self):
        self.status = "init"


class PlayedGame(Game):
    def __init__(self, map):
        self.map = map
        super().__init__()

    async def get_replay(self, filename="Example.SC2Replay"):
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            if self.status == "finished":
                replay = api.Request(save_replay=api.RequestSaveReplay())
                await ws.send(replay.SerializeToString())
                _replay_response = await ws.recv()
                replay_response = api.Response.FromString(_replay_response)
                with open(
                    "Replays/Replay" + str(uuid.uuid4()) + ".SC2Replay", "wb"
                ) as f:
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
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            for player in self.players:
                player1 = request_payload.create_game.player_setup.add()
                player1.type = dict(api.PlayerType.items())["Computer"]
                player1.difficulty = dict(api.Difficulty.items())[player.difficulty]
                player1.race = dict(common.Race.items())[player.race]
                player.server = self.host

            observer = request_payload.create_game.player_setup.add()
            observer.type = dict(api.PlayerType.items())["Observer"]

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
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
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
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())["Computer"]
            player1.difficulty = dict(api.Difficulty.items())[self.computer.difficulty]
            player1.race = dict(common.Race.items())[self.computer.race]
            self.player.server = self.host

            player1 = request_payload.create_game.player_setup.add()
            player1.type = dict(api.PlayerType.items())["Participant"]

            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            print(response)
            self.status = "created"

            request_payload = api.Request()
            request_payload.join_game.race = dict(common.Race.items())[self.player.race]

            request_payload.join_game.options.raw = True
            await ws.send(request_payload.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)
            self.status = "started"

    async def simulate(self, step=300):
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
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
            self.players[0].leave_game(), self.players[1].leave_game()
        )

    async def start_game(self):
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            request_payload = api.Request()
            request_payload.create_game.local_map.map_path = self.map

            # Create slots
            for player in self.players:
                player1 = request_payload.create_game.player_setup.add()
                player1.type = dict(api.PlayerType.items())["Participant"]

            await asyncio.wait_for(ws.send(request_payload.SerializeToString()), 5)
            result = await asyncio.wait_for(ws.recv(), 5)
            response = api.Response.FromString(result)
            print(response)
            self.status = "created"

            tasks = []
            port_config = {
                "players_ports": [],
                "shared_port": self.shared_port,
                "base_port": self.base_port,
                "game_port": self.game_port,
            }
            for human in self.players:
                player_port = {
                    "base_port": human.base_port,
                    "game_port": human.game_port,
                }
                port_config["players_ports"].append(player_port)

            for human in self.players:
                tasks.append(asyncio.ensure_future(human.join_game(port_config)))
            for task in tasks:
                response = await asyncio.wait_for(task, 5)
                if response.status != 3:
                    self.status = "launched"
            if self.status == "created":
                self.status = "started"

    async def simulate(self, step=300):
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            seconds = 0
            while self.status == "started":
                tasks = []
                results = await asyncio.gather(
                    self.players[0].advance_time(step),
                    self.players[1].advance_time(step),
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
        self.game_info = None

    async def create(self):
        port = portpicker.pick_unused_port()
        self.host = await Server.get_server(self.server, self.address, str(port))

    async def load_replay(self, replay_file, id=0):
        print(replay_file)
        async with websockets.connect(
            "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port)
        ) as ws:
            replay_meta = api.Request(
                replay_info=api.RequestReplayInfo(replay_path=replay_file)
            )
            await ws.send(replay_meta.SerializeToString())
            result = await ws.recv()
            metadata = api.Response.FromString(result)
            self.replay_info = {
                "map": metadata.replay_info.map_name,
                "races": [
                    metadata.replay_info.player_info[0].player_info.race_requested,
                    metadata.replay_info.player_info[1].player_info.race_requested,
                ],
                "results": [
                    metadata.replay_info.player_info[0].player_result.result,
                    metadata.replay_info.player_info[1].player_result.result,
                ],
            }
            print(self.replay_info)
            msg = api.Request(
                start_replay=api.RequestStartReplay(
                    replay_path=replay_file,
                    observed_player_id=id,
                    options=api.InterfaceOptions(raw=True, score=False),
                )
            )

            await ws.send(msg.SerializeToString())
            result = await ws.recv()
            response = api.Response.FromString(result)

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
            game_meta = game_meta["gameInfo"]
            game_meta.pop("modNames")
            game_meta.pop("options")
            game_meta.pop("mapName")
            if("localMapPath" in game_meta.keys()):
                game_meta.pop("localMapPath")
            game_meta.pop("playerInfo")
            game_meta.update(game_meta["startRaw"])
            game_meta.pop("startRaw")
            game_meta.pop("mapSize")
            self.game_info = game_meta

            self.status = "started"
    def transform_json(self,dict, previous):
        commons = dict["observation"]["playerCommon"]
        dict["observation"].update(commons)
        dict["observation"].pop("playerCommon")
        dict["metadata"]["playerId"] = dict["observation"]["playerId"]
        dict["observation"].pop("playerId")
        dict["observation"].update(dict["observation"]["rawData"])
        dict["observation"].pop("rawData")
        dict["observation"]["player"].pop("camera")
        dict["observation"].update(dict["observation"]["player"])
        dict["observation"].pop("player")
        dict["observation"].update(dict["observation"]["mapState"])
        dict["observation"].pop("mapState")

        units_by_id = {}
        for unit in previous:
            tag = unit["tag"]
            unit.pop("tag")
            unit.pop("isOnScreen")
            if("isSelected" in unit.keys()):
                unit.pop("isSelected")
            unit = json.loads(json.dumps(unit))
            if "orders" in unit.keys():
                unit.pop("orders")
            if "engagedTargetTag" in unit.keys():
                unit.pop("engagedTargetTag")
            if "addOnTag" in unit.keys():
                unit.pop("addOnTag")
            units_by_id[tag] = unit
        for unit in dict["observation"]["units"]:
            tag = unit["tag"]
            unit.pop("tag")
            unit.pop("isOnScreen")
            if("isSelected" in unit.keys()):
                unit.pop("isSelected")
            unit = json.loads(json.dumps(unit))
            if "orders" in unit.keys():
                unit.pop("orders")
            if "engagedTargetTag" in unit.keys():
                unit.pop("engagedTargetTag")
            if "addOnTag" in unit.keys():
                unit.pop("addOnTag")
            if tag not in units_by_id.keys():
                units_by_id[tag] = unit


        for unit in dict["observation"]["units"]:
            if("orders" in unit.keys()):
                for order in unit["orders"]:
                    if("targetUnitTag" in order.keys()):
                        unit = units_by_id.get(order["targetUnitTag"], {})
                        if unit:
                            order["unit"] = unit
                        order.pop("targetUnitTag")
            if "engagedTargetTag" in unit.keys():
                unit["engagedTarget"] = units_by_id[unit["engagedTargetTag"]]
                unit.pop("engagedTargetTag")
            if "addOnTag" in unit.keys():
                unit["addOn"] = units_by_id[unit["addOnTag"]]
                unit.pop("addOnTag")
                
 
        if("event" in dict["observation"].keys()):
            dunits = []
            for tag in dict["observation"]["event"]["deadUnits"]:
                unit = units_by_id.get(tag, {})
                if (unit):
                    dunits.append(unit)
            if dunits:
                dict["observation"]["event"]["deadUnits"] = dunits
            else:
                dict["observation"].pop("event")
        dict["observation"].pop("creep")
        dict["observation"].pop("visibility")





        return dict


    async def observe_replay(self, step=24, id=0):
        previous = None
        previous_units = []
        while self.status == "started" or self.status == "replay":
            async with websockets.connect(
                "ws://{0}:{1}/sc2api".format(self.host.address, self.host.port), ping_interval=1,ping_timeout=1, close_timeout=1
            ) as ws:
                try:
                    request_payload = api.Request()
                    request_payload.observation.disable_fog = False
                    await asyncio.wait_for(ws.send(request_payload.SerializeToString()), timeout=1)
                    result = await asyncio.wait_for(ws.recv(), timeout=1)

                    response = api.Response.FromString(result)
                    response = MessageToDict(response)
                    response = str(response)
                    response = response.replace("\'", "\"")
                    response = response.replace("False", "false")
                    response = response.replace("True", "true")
                    json_dict = json.loads(response,encoding="UTF-8")
                   
                    if(previous != None):
                        units_by_tag = {}
                        for unit in previous_units:
                            newUnit = json.loads(json.dumps(unit))
                            tag = newUnit["tag"]
                            newUnit.pop("tag")
                            newUnit.pop("isOnScreen")
                            if("isSelected" in newUnit.keys()):
                                newUnit.pop("isSelected")
                            if "orders" in newUnit.keys():
                                newUnit.pop("orders")
                            if "engagedTargetTag" in newUnit.keys():
                                newUnit.pop("engagedTargetTag")
                            if "addOnTag" in newUnit.keys():
                                newUnit.pop("addOnTag")
                            units_by_tag[tag] = newUnit
                        for unit in json_dict["observation"]["observation"]["rawData"]["units"]:
                            newUnit = json.loads(json.dumps(unit))
                            tag = newUnit["tag"]
                            if tag not in units_by_tag.keys():
                                newUnit.pop("tag")
                                newUnit.pop("isOnScreen")
                                if("isSelected" in newUnit.keys()):
                                    newUnit.pop("isSelected")
                                if "orders" in newUnit.keys():
                                    newUnit.pop("orders")
                                if "engagedTargetTag" in unit.keys():
                                    unit.pop("engagedTargetTag")
                                if "addOnTag" in unit.keys():
                                    unit.pop("addOnTag")
                                units_by_tag[tag] = newUnit
                        actions = json_dict["observation"].get("actions", {})
                        actions = list(filter(lambda x : "actionRaw" in x.keys(), actions))
                        unitActions = list(filter(lambda x : "unitCommand" in x["actionRaw"].keys(),actions))
                        castActions = list(filter(lambda x : "toggleAutocast" in x["actionRaw"].keys(), actions))
                        unitActions = list(map(lambda x : x["actionRaw"]["unitCommand"], unitActions))
                        castActions = list(map(lambda x : x["actionRaw"]["toggleAutocast"], castActions))
                        for action in unitActions:
                            units = []
                            for tag in action["unitTags"]:
                                units.append(units_by_tag[tag])
                            action["units"] = units
                            action.pop("unitTags")
                            if "targetUnitTag" in action.keys():
                                action["target"] = units_by_tag[action["targetUnitTag"]]
                                action.pop("targetUnitTag")
                        for action in castActions:
                            units = []
                            for tag in action["unitTags"]:
                                units.append(units_by_tag[tag])
                            action["units"] = units
                            action.pop("unitTags")
                        previous["actions"] = unitActions + castActions
                        if previous["actions"]:
                            yield previous
                    previous = {
                        "metadata" : self.replay_info,
                        "observation": json_dict["observation"]["observation"],
                        "mapMetadata": self.game_info["startLocations"]
                    }
                    anterior_units = previous_units
                    previous_units = json.loads(json.dumps(previous["observation"]["rawData"]["units"]))
                    previous = self.transform_json(previous, anterior_units)
                    print(json_dict["observation"]["observation"]["gameLoop"])
                    request_payload = api.Request()
                    request_payload.step.count = step
                    await asyncio.wait_for(ws.send(request_payload.SerializeToString()), timeout=1)
                    result = await asyncio.wait_for(ws.recv(),timeout=1)
                    response = api.Response.FromString(result)
                    if response.status == 4:
                        self.status = "replay"
                    else:
                        self.status = "finished"
                except Exception:
                    print(traceback.format_exc())
                    continue
        self.host.status = "idle"


class Classifier(Replay):
    async def observe_replay(self, step=300, id=0):
        self.host.status = "idle"
        return self.replay_info

