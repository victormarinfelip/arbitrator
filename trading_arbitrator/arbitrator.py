import matplotlib.pyplot as plt

from trading_arbitrator.primitives import Loop, Pair, Pool, LoopPool, Exchange, DexRateFormulaType, ExchangeTypes
from trading_arbitrator.errors import InvalidLoopError
from typing import Optional, List, Union
from itertools import combinations, permutations
import math


class Arbitrator(object):

    def __init__(self,
                 pairs: Optional[List[List[str]]] = None,
                 pools: Optional[List[Pool]] = None,
                 initial_assets: List[str] = None,
                 rates: Optional[List[float]] = None,
                 gas_price: float = 0
                 ):
        if pairs is not None and pools is not None:
            raise ValueError
        if pairs is not None and rates is None:
            raise ValueError
        self.pools = None
        self.pairs = pairs
        self.initial_assets = initial_assets
        self.gas_price = gas_price
        if pools is not None and pairs is None:
            self.pools = pools
            self.pairs = self._get_pairs_from_pools(pools)
        else:
            # Now we have to create a pool for each pair with the basic rate rule
            self.pools = self._create_pools_from_str_pairs(pairs, rates)
            self.pairs = self._get_pairs_from_pools(self.pools)
        pass

    def _get_pairs_from_pools(self, pools: List[Pool]) -> List[Pair]:
        pairs: List[Pair] = []
        for pool in pools:
            pairs += pool.get_pairs()
        return pairs

    def _create_pools_from_str_pairs(self, pairs: List[List[str]], rates: List[float]) -> List[Pool]:
        pools: List[Pool] = []
        for pair, rate in zip(pairs, rates):
            pool = Pool(assets=[pair[0], pair[1]], rate=rate)
            pools.append(pool)
        return pools

    def get_loops(self, sizes: Optional[List[int]] = None, with_fees: bool = True) -> List[Loop]:
        if sizes is None:
            sizes = [3]
        pool = LoopPool(self._generate_loops(sizes))
        return pool.sort_loops(with_fees)

    def _generate_loops(self, sizes: List[int]) -> List[Loop]:

        candidate_loop_list: List[Pair] = []
        final_loop_list: List[Loop] = []
        for size in sizes:
            candidate_loop_list += list(combinations(self.pairs, size))
        for candidate_loop in candidate_loop_list:
            for permutation_of_candidate in list(permutations(list(candidate_loop))):
                try:
                    l_ = Loop(permutation_of_candidate)
                    if l_.initial_asset not in self.initial_assets:
                        continue
                    final_loop_list.append(l_)
                except InvalidLoopError:
                    pass
        return final_loop_list


# Let's test this...

pairs = [
    ["A", "B"],
    ["A", "C"],
    ["B", "C"],
    ["C", "D"],
    ["D", "A"],
    ["B", "D"]
]

rates = [
    1.,
    2.,
    3.,
    0.7,
    0.9,
    2
]

# arb = Arbitrator(pairs=pairs, rates=rates, initial_assets=["A", "B"])
# loops = arb.get_loops(sizes=[2,3,4,5])
# for l in loops:
#     print(l, l.rate())

# Now let's do some shit

def ConstantProductAMM(i, j, am, state, **kwargs):
    """
    Implements prid(x_i) = C, where x_i are the amounts of i coins in the pool,
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

# Let's create an exchange:
ex = Exchange("CPAMM", type_=ExchangeTypes.DEX, conversion_formula=ConstantProductAMM)

# Let's have 2 pools:
pool1 = Pool(assets=["A", "B", "C"], amounts=[500,400,200], exchange=ex)
pool2 = Pool(assets=["A", "B", "C", "D"], amounts=[500,400,300, 200], exchange=ex)

# Create arbi
arb = Arbitrator(pools=[pool1, pool2], initial_assets=["A", "D"])
loops = arb.get_loops(sizes=[2,3,4,5])
best = loops[15]

results = []
for i in range(1,500,2):
    results.append(best.convert(i) - i)

print(best.get_max_absolute_profit())
plt.plot(results)
plt.grid()
plt.show()





