import s2clientprotocol.sc2api_pb2 as api;
import s2clientprotocol.common_pb2 as common;
from websocket import create_connection

request_payload = api.Request()
print dir(request_payload)
request_payload.create_game.local_map.map_path = "../Maps/AbiogenesisLE.SC2Map"

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
print request_payload
ws.send(request_payload.SerializeToString())
result = ws.recv()
print "Received '%s'" % result
response = api.Response.FromString(result)

print response.status

request_payload = api.Request()
request_payload.join_game.observed_player_id = 0
request_payload.join_game.options.raw = True
ws.send(request_payload.SerializeToString())
result = ws.recv();
response = api.Response.FromString(result)


print response.status
game = ""
while response.status == 3:
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

log = open("log.txt", "w")
log.write(game)
log.close()
