import pymongo
from pymongo import UpdateOne
from local_settings import *

def update_cases(cases):
    if cases["player_id"] == 0:
        matchup = cases["metadata"].races[0] + cases["metadata"].races[1]
    else:
        matchup = cases["metadata"].races[1] + cases["metadata"].races[0]
    client = MongoClient(DATABASE_ROUTE, DATABASE_PORT)
    db = client[matchup]
    collection = db.cases
    query = []
    for case in cases["cases"]:
        increase_part = {"played_in_games": 1}
        if cases["metadata"]["results"][id] == 1:
            increase_part["wins"] = 1
        query.append(UpdateOne(case, {"$inc" : increase_part}, upsert=True))
    return collection.bulk_write(query, ordered=False)

def get_random_cases(n):
    if cases["player_id"] == 0:
        matchup = cases["metadata"].races[0] + cases["metadata"].races[1]
    else:
        matchup = cases["metadata"].races[1] + cases["metadata"].races[0]
    client = MongoClient(DATABASE_ROUTE, DATABASE_PORT)
    db = client[matchup]
    collection = db.cases
    return collection.aggregate([{"$sample": {"size": n}}])