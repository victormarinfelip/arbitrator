import math
from trading_arbitrator.errors import LPDepletedError


def constant_product_amm(i, j, am, state):
    """
    Implements prod(x_i) = C, where x_i are the amounts of i coins in the pool,
    and C a constant. Constant product automated market maker.

    :param i: index of starting coin
    :param j: index of target coin
    :param am: amount of starting coin to trade for target coin
    :param state: list of pool sizes
    :return: amount of target asset to be sent to trader
    """
    initial_j = state[j]
    # We get the constant C
    c = math.prod(state)
    # We add "am" quantity of coin i to the pool:
    state[i] += am
    prod_no_j = math.prod(state[:j]+state[j+1:])
    final_j = c / prod_no_j
    # We write the new amount of j
    state[j] = final_j
    return initial_j - final_j


def constant_sum_amm(i, j, am, state):
    """
    Implements sum(x_i) = C, where x_i are the amounts of i coins in the pool,
    and C a constant. Constant sum automated market maker. This implements a
    set of stablecoins.

    :param i: index of starting coin
    :param j: index of target coin
    :param am: amount of starting coin to trade for target coin
    :param state: list of pool sizes
    :return: amount of target asset to be sent to trader
    """
    initial_j = state[j]
    # We get the constant C
    c = sum(state)
    # We add "am" quantity of coin i to the pool:
    state[i] += am
    sum_no_j = sum(state[:j]+state[j+1:])
    final_j = c - sum_no_j
    if final_j < 0:
        raise LPDepletedError
    # We write the new amount of j
    state[j] = final_j
    return initial_j - final_j
