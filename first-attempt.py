import json

import s2clientprotocol.common_pb2 as common
import s2clientprotocol.sc2api_pb2 as api
import time
from websocket import create_connection

from game_data.observations import decode_observation, UnitsProfile

request_payload = api.Request()
print(dir(request_payload))
request_payload.create_game.local_map.map_path = "../Maps/Ladder2018Season1/AbiogenesisLE.SC2Map"

player1 = request_payload.create_game.player_setup.add()
player1.type = dict(api.PlayerType.items())['Computer']
player1.difficulty = dict(api.Difficulty.items())['VeryHard']
player1.race = dict(common.Race.items())['Random']

player2 = request_payload.create_game.player_setup.add()
player2.type = dict(api.PlayerType.items())['Computer']
player2.difficulty = dict(api.Difficulty.items())['VeryEasy']
player2.race = dict(common.Race.items())['Random']

observer = request_payload.create_game.player_setup.add()
observer.type = dict(api.PlayerType.items())['Observer']

ws = create_connection("ws://localhost:12345/sc2api")
print(request_payload)
ws.send(request_payload.SerializeToString())
result = ws.recv()
print("Received '%s'" % result)
response = api.Response.FromString(result)

print(response.status)

request_payload = api.Request()
request_payload.join_game.observed_player_id = 1
request_payload.join_game.options.raw = True
ws.send(request_payload.SerializeToString())
result = ws.recv()
response = api.Response.FromString(result)

request_data = api.Request(data=api.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True))
ws.send(request_data.SerializeToString())
result = ws.recv()
data_response = api.Response.FromString(result)
game_data = data_response.data

print(response.status)
logs = {}

start_time = time.time()
while response.status == 3:
    request_payload = api.Request(observation=api.RequestObservation())
    request_payload.observation.disable_fog = True
    ws.send(request_payload.SerializeToString())
    result = ws.recv()
    info_response = api.Response.FromString(result)

    obj = decode_observation(info_response.observation.observation, game_data)
    units_profile = UnitsProfile(obj)
    logs[obj.game_loop] = units_profile

    request_payload = api.Request()
    request_payload.step.count = 1000
    ws.send(request_payload.SerializeToString())
    result = ws.recv()
    response = api.Response.FromString(result)

print("Elapsed time {}s".format(time.time() - start_time))
print("Game ended")
print("Requesting replay from server")
replay = api.Request(save_replay=api.RequestSaveReplay())
ws.send(replay.SerializeToString())
_replay_response = ws.recv()
replay_response = api.Response.FromString(_replay_response)
print(replay_response)

with open("Example.SC2Replay", "wb") as f:
    f.write(replay_response.save_replay.data)

game_json = {game_loop: observation.to_dict() for game_loop, observation in logs.items()}
game_json = json.dumps(game_json)
log = open("game_log.json", "w")
log.write(game_json)
log.close()
