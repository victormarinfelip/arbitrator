from typing import Optional, List, Tuple, Callable
from trading_arbitrator.errors import InvalidLoopError, ImpossibleConversionException, InvalidPoolException
from itertools import combinations
from scipy import optimize


class Converter(object):

    def __init__(self, name: str, conversion_formula: Optional[Callable] = None, fee: float = 0.,
                 gas_cost: int = 0):
        """
        Represents the algorithm used to swap asset amounts. Must be passed to a Pool.

        :param name: A unique name.
        :param conversion_formula: A function that will compute the new state of the pool and will return
            the amount of target asset resulted from the swap. Any function with the following arguments:
            i: index of initial coin
            j: index of target coin
            am: amount of initial coin to be swapped for target coin
            state: list of pool sizes for all coins. This will have to be updated to reflect the new amounts
                of coins i and j after the swap.
            returns: A float representing the amount of target coin obtained after the swap.
        :param fee: Fee of the pool in percentual points (10 = 10%)
        :param gas_cost: Cost of a swap in gas units.
        """
        self.name = name
        self.conversion_formula = conversion_formula
        self._fee = fee
        self.gas_cost: int = gas_cost
        self.processing_cost: int = 0

    @property
    def fee(self) -> float:
        return self._fee / 100.  # Fee is in %

    def apply_conversion(self, *args) -> float:
        return self.conversion_formula(*args)

    def __repr__(self):
        return "{}".format(self.name)


class Pair(object):

    def __init__(self, asset0: str, asset1: str, index_0: int, index_1: int, convert_function: Callable):
        self.asset0 = asset0
        self.asset1 = asset1
        self.index_0 = index_0
        self.index_1 = index_1
        self.convert_function = convert_function
        self.parent_pool = None

    def convert(self, asset: str, amount: float, with_fees: bool = True) -> Tuple[str, float]:
        if asset == self.asset0:
            target = self.asset1
        elif asset == self.asset1:
            target = self.asset0
        else:
            raise ImpossibleConversionException()
        target_amount = self.convert_function(asset, amount, target, with_fees)
        return target, target_amount

    def __repr__(self):
        return "{}/{}{}".format(self.asset0, self.asset1, " ex: {}".format(self.parent_pool.name)
        if self.parent_pool.name != "GENERIC" else "")


class Pool(object):

    def __init__(self,
                 name: str,
                 assets: List[str],
                 amounts: Optional[List[float]] = None,
                 rate: Optional[float] = None,
                 converter: Optional[Converter] = None
                 ):
        """
        A pool representing any relation between assets. The simplest one is 2 assets
        with infinite pool sizes and exchangable by a rate, like a forex trade. However this
        is generalized to a general pool with many types of assets related by a custom function
        (such as a CFMM).

        :param name: Unique name of the pool.
        :param assets: List of assets present in the pool, like ["USDT", "USDC", "DAI"]
        :param amounts: Amounts of each asset present in the pool, like [500, 400, 600]
        :param rate: Exchange rate between 2 assets. Use only to recreate a simple Forex exchange bewteen 2 assets.
        :param converter: Conversion logic represented by a Converter object. Set to None for a Forex-like simple rate.
        """

        if len(assets) < 2:
            raise InvalidPoolException()
        if 2 < len(assets) != len(amounts):
            raise InvalidPoolException()
        if converter is None and (len(assets) != 2 or rate is None):
            raise InvalidPoolException()
        if converter is None:
            converter = Converter("GENERIC",
                                  conversion_formula=lambda i, j, x, am, **kwargs: rate * x if i == 0 else (1 / rate) * x)

        self.name = name
        self.exchange: Converter = converter
        self.assets = assets

        self._initial_amounts = amounts
        self.amounts = amounts
        if amounts is not None:
            self.amounts = self._initial_amounts.copy()

    def convert(self, asset: str, amount: float, target: str, with_fees: bool) -> float:
        """
        Swaps 'asset' into 'target'. Returns the resulting target asset amount. Applies the full
        swap to the liquidity pools, changing the amount of each asset present in the pools.

        :param asset: Asset to swap such as "USDT".
        :param amount: Amount of asset to be swapped.
        :param target: Target asset to swap the asset for, such as "DAI".
        :param with_fees: Set to true to apply Converter fees.
        :return: Amount obtained of target asset after the swap.
        """
        if asset == target:
            raise ImpossibleConversionException()
        start_i = self.assets.index(asset)
        end_i = self.assets.index(target)
        final_amount = self.exchange.apply_conversion(start_i, end_i, amount, self.amounts)
        if with_fees:
            final_amount *= (1 - self.exchange.fee)
        return final_amount

    def reset(self) -> None:
        """
        Resets the state of the pools to the initial one.
        """
        if self._initial_amounts is not None:
            self.amounts = self._initial_amounts.copy()

    def get_pairs(self) -> List[Pair]:
        """
        Returns a list of Pair objects representing all possible exchange pairs using the assets
        present in the Pool.
        :return: A list of Pair objects.
        """
        pairs = list(combinations(self.assets, 2))
        pairs_obj: List[Pair] = []
        for pair in pairs:
            parsed_pair = Pair(pair[0], pair[1], self.assets.index(pair[0]), self.assets.index(pair[1]), self.convert)
            parsed_pair.parent_pool = self
            pairs_obj.append(parsed_pair)
        return pairs_obj

    def __repr__(self):
        return "-".join([str(p) for p in self.assets]) + " {}".format(str(self.exchange))


class Loop(object):

    def __init__(self, pairs: List[Pair]):
        """
        Represents the abstraction of an arbitrage, as a set of chained swaps
        between assets, such as "ETH to DAI" then "DAI to USDC" then "USD to ETH",
        which would be a triangular arbitrage. Loops always start and end with the same asset.

        :param pairs: A list of Pair objects representing the neccessary swaps to run the whole loop.
        """
        self.pairs = pairs
        self._validate()

    @property
    def initial_asset(self) -> str:
        """
        Returns the initial asset of the loop, like "ETH"
        """
        # The asset that exists both in the first and the last pair of the loop
        first_pair = self.pairs[0]
        last_pair = self.pairs[-1]
        last_pair_data = [last_pair.asset0, last_pair.asset1]
        if first_pair.asset0 in last_pair_data:
            return first_pair.asset0
        elif first_pair.asset1 in last_pair_data:
            return first_pair.asset1
        else:
            raise InvalidLoopError(self.pairs)

    @property
    def size(self) -> int:
        """
        Returns the size of the loop, as in 3 in triangular arbitrage.
        """
        return len(self.pairs)

    def convert(self, amount: float, with_fees: bool = True, reset: bool = True) -> float:
        # Run the full loop
        asset = self.initial_asset
        for pair in self.pairs:
            asset, amount = pair.convert(asset, amount, with_fees)
        # Reset pool state:
        if reset:
            for pair in self.pairs:
                pair.parent_pool.reset()
        return amount

    def get_max_absolute_profit(self) -> Tuple[float, float]:
        """
        Optimizes the amount to be traded to maximize absolute profits, taking into account the
        slippage created in LPs when trading large amounts.
        :return: A tuple of (<optimal amount to trade>, <absolute profits for that amount>)
        """
        max_x = optimize.fmin(lambda x: -(self.convert(x) - x), 1)
        return max_x, self.convert(max_x) - max_x

    def _validate(self):
        # 4 conditions:
        # - At least 2 pairs.
        # - Start and end pairs contain the same asset.
        # - There is a valid chain of conversions.

        # Condition 1:
        if len(self.pairs) < 2:
            raise InvalidLoopError(self.pairs)

        # Condition 2:
        first_pair = self.pairs[0]
        last_pair = self.pairs[-1]
        target_assets = [last_pair.asset0, last_pair.asset1]
        if not (first_pair.asset0 in target_assets or first_pair.asset1 in target_assets):
            raise InvalidLoopError(self.pairs)

        # Condition 3:
        asset = self.initial_asset
        for pair in self.pairs:
            try:
                asset, _ = pair.convert(asset, 1)
            except ImpossibleConversionException:
                raise InvalidLoopError(self.pairs)
            finally:
                pair.parent_pool.reset()
        if asset != self.initial_asset:
            raise InvalidLoopError(self.pairs)

    def __repr__(self):
        return " -> ".join([str(p) for p in self.pairs])


class LoopPool(object):
    _loops: List[Loop]

    def __init__(self, loops: Optional[List[Loop]]):
        self._loops = loops

    def sort_loops(self, with_fees: bool = True) -> List[Loop]:
        self._loops.sort(key=lambda l: l.convert(1, with_fees), reverse=True)
        return self._loops
