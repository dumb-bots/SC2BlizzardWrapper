import math
from functools import reduce


def euclidean_distance(pos0, posf):
    dim = len([pos for pos in posf if pos is not None])
    return math.sqrt(reduce(lambda x, y: x + y, [(posf[i] - pos0[i])**2 for i in range(dim)]))
