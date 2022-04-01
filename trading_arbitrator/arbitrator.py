from trading_arbitrator.primitives import Loop, Pair, Pool, LoopPool
from trading_arbitrator.errors import InvalidLoopError
from typing import Optional, List
from itertools import combinations, permutations


class Arbitrator(object):

    def __init__(self,
                 pairs: Optional[List[List[str]]] = None,
                 pools: Optional[List[Pool]] = None,
                 initial_assets: List[str] = None,
                 rates: Optional[List[float]] = None,
                 gas_price: float = 0
                 ):
        """
        Generates arbitrage "loops" and computes their performance. Can be used in "simple mode"
        by passing a list of pairs and rates, and it will generate all possible valid "loops" of N swaps
        and their profitability (3 for triangular arbitrage).

        Can also use any combination of Pool objects representing AMMs of as many token types as possible
        (say, a curve pool with 3 tokens, and another with 4 tokens). Pools incorporate a converter that can
        apply any function as conversion, such as constant function market makers.

        For simple mode pass pairs and rates. For AMM modes pass pools. Initial assets must be always passed.

        :param pairs: List of pairs such as [["ETH", "BTC"], ["BTC", "USDT"], ["ETH", "USDT"]]
        :param pools: List of Pool objects.
        :param initial_assets: List of assets to be used as initial assets for the arbitrage as in ["ETH", "USDT"]
        :param rates: List of change rates for the pairs if used in simple mode.
        :param gas_price: Price of gas unit.
        """
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
            pool = Pool(name="GENERIC", assets=[pair[0], pair[1]], rate=rate)
            pools.append(pool)
        return pools

    def get_loops(self, sizes: Optional[List[int]] = None, with_fees: bool = True) -> List[Loop]:
        """
        Returns a list of simulated Loop objects sorted by relative returns after investing a single unit of
        starting asset.

        :param sizes: List of desired loop sizes: [3] for triangular arbitrage, [3, 4, 5] for that and more.
        :param with_fees: True to apply fees. Fees must be specified when creating a Converter for a Pool.
        :return: A list of Pool objects sorted by simulated returns.
        """
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
