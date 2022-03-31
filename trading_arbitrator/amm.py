import math
from errors import LPDepletedError

def ConstantProductAMM(i, j, am, state, **kwargs):
    """
    Implements prod(x_i) = C, where x_i are the amounts of i coins in the pool,
    and C a constant. Constant product automated market maker.

    :param i: index of starting coin
    :param j: index of target coin
    :param am: amount of starting coin to trade for target coin
    :param state: list of pool sizes
    :param kwargs: Extra stuff that the function may need
    :return: amount of target asset to be sent to trader
    """
    initial_j = state[j]
    # We get the constant C
    C = math.prod(state)
    # We add "am" quantity of coin i to the pool:
    state[i] += am
    prod_no_j = math.prod(state[:j]+state[j+1:])
    final_j = C / prod_no_j
    # We write the new amount of j
    state[j] = final_j
    return initial_j - final_j


def ConstantSumAMM(i, j, am, state, **kwargs):
    """
    Implements sum(x_i) = C, where x_i are the amounts of i coins in the pool,
    and C a constant. Constant sum automated market maker. This implements a
    set of stablecoins.

    :param i: index of starting coin
    :param j: index of target coin
    :param am: amount of starting coin to trade for target coin
    :param state: list of pool sizes
    :param kwargs: Extra stuff that the function may need
    :return: amount of target asset to be sent to trader
    """
    initial_j = state[j]
    # We get the constant C
    C = sum(state)
    # We add "am" quantity of coin i to the pool:
    state[i] += am
    sum_no_j = sum(state[:j]+state[j+1:])
    final_j = C - sum_no_j
    if final_j < 0:
        raise LPDepletedError
    # We write the new amount of j
    state[j] = final_j
    return initial_j - final_j
