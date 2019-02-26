import json
import math

import matplotlib.pyplot as plt


a = open('../observations_3.json', 'r')
b = a.read()
b = b.replace("'", '"')
b = b.replace("ObjectId(", '')
b = b.replace(")", '')
b = b.replace("None", 'null')
observations = json.loads(b)
a.close()


def plot_stats():
    # Attacks
    raw_data = {}
    for o in observations:
        loop = o['observation']['loop']
        raw_data[loop] = raw_data.get(loop, {})
        raw_data[loop]['attacks'] = raw_data[loop].get('attacks', 0) + len(list(filter(lambda a: a['id'] in [23, 3674], o['actions'])))
        raw_data[loop]['actions'] = raw_data[loop].get('actions', 0) + len(o['actions'])
        raw_data[loop]['games'] = raw_data[loop].get('games', 0) + o['games']

    attack_data = [(loop, v['attacks']) for loop, v in raw_data.items()]
    action_data = [(loop, v['actions']) for loop, v in raw_data.items()]
    games_data = [(loop, v['games']) for loop, v in raw_data.items()]
    x1, y1 = list(zip(*attack_data))
    x2, y2 = list(zip(*action_data))
    x3, y3 = list(zip(*games_data))

    # Plot attacks and actions
    plt.scatter(x1, y1, label='attacks per gameloop', s=1)
    plt.scatter(x2, y2, label='actions per gameloop', s=1)
    plt.show()

    # Plot attacks
    plt.scatter(x1, y1, label='attacks per gameloop', s=1)
    plt.show()

    # Plot games
    plt.scatter(x3, list(map(math.log, y3)), label='games per gameloop', s=1)
    plt.show()

    print("Attack / Actions stats ------------")
    print("Actions mean: {0:.2f}".format(sum(y2) / len(y2)))
    print("Attacks mean: {0:.2f}".format(sum(y1) / len(y1)))
    print("Proportion: {0:.2f}".format((sum(y1) / len(y1)) / (sum(y2) / len(y2))))

    print("Aggregation stats ------------")
    a = [o['games'] for o in observations]
    print("Total cases: {}".format(len(a)))
    print("Grouped: {}".format(len(a) - a.count(1)))
    print("Proportion grouped: {0:.2f}%".format(100 * (len(a) - a.count(1)) / len(a)))
    highest_grouped_case =  max(filter(lambda o: o['games'] > 1, observations), key=lambda o: o['observation']['loop'])
    print("Highest grouped case in GL {} with {} games".format(
        highest_grouped_case['observation']['loop'],
        highest_grouped_case['games'])
    )
    print("-----------------------------")


plot_stats()
