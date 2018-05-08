import s2clientprotocol.common_pb2 as common
import s2clientprotocol.sc2api_pb2 as api
import s2clientprotocol.query_pb2 as api_query


async def find_placement(ws, ability_id, target_point, circles=3, circle_distance=2):
    for circle in range(1, circles + 1):
        distance = circle * circle_distance
        options = [(target_point[0] + distance, target_point[1] + distance),
                   (target_point[0] + distance, target_point[1]),
                   (target_point[0] + distance, target_point[1] - distance),
                   (target_point[0] - distance, target_point[1] + distance),
                   (target_point[0] - distance, target_point[1]),
                   (target_point[0] - distance, target_point[1] - distance),
                   (target_point[0], target_point[1] + distance),
                   (target_point[0], target_point[1] - distance),]
        for point in options:
            can_place = await query_building_placement(ws, ability_id, point)
            if can_place:
                return point


async def query_building_placement(ws, ability_id, point):
    if not isinstance(point, common.Point2D):
        point = common.Point2D(x=point[0], y=point[1])
    api_request = api.Request(query=api_query.RequestQuery(placements=[api_query.RequestQueryBuildingPlacement(
        ability_id=ability_id, target_pos=point)]))
    await ws.send(api_request.SerializeToString())
    result = await ws.recv()
    response = api.Response.FromString(result)
    return response.query.placements[0].result == 1
