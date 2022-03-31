from typing import Dict, Optional, Any, List, Tuple, Callable, TypedDict, Union
from enum import Enum
from trading_arbitrator.errors import InvalidLoopError, ImpossibleConversionException, WrongExTypeError, LPDepletedError, InvalidPoolException
from copy import deepcopy
from itertools import combinations
from scipy import optimize

# We need...
# Exchanges, assets, pairs and loops


class ExchangeTypes(str, Enum):
    CLASSIC = "CLASSIC"
    DEX = "DEX"


class DexRateFormulaType(TypedDict):
    asset_amounts: List[float]
    params: Optional[Dict]


class Exchange():

    def __init__(self, name: str, type_: ExchangeTypes, conversion_formula: Optional[Callable] = None, fee: float = 0., gas_cost: int = 0):
        self.name = name
        self.ex_type = type_
        self.conversion_formula = conversion_formula
        self._fee = fee
        self.gas_cost: int = gas_cost
        self.processing_cost: int = 0

    @property
    def fee(self) -> float:
        return self._fee / 100. # Fee is in %

    def apply_conversion(self, *args) -> float:
        return self.conversion_formula(*args)

    def __repr__(self):
        return "{}".format(self.name)


class Pair(object):

    def __init__(self, asset0: str, asset1: str, index_0: int, index_1: int, convertion: Callable):
        self.asset0 = asset0
        self.asset1 = asset1
        self.index_0 = index_0
        self.index_1 = index_1
        self.convertion = convertion
        self.parent_pool = None

    def convert(self, asset: str, amount: float, with_fees: bool = True) -> Tuple[str, float]:
        if asset == self.asset0:
            target = self.asset1
        elif asset == self.asset1:
            target = self.asset0
        else:
            raise ImpossibleConversionException()
        target_amount = self.convertion(asset, amount, target)
        return target, target_amount

    def __repr__(self):
        return "{}/{}".format(self.asset0, self.asset1)


class Pool(object):

    def __init__(self,
                 assets: List[str],
                 amounts: Optional[List[float]] = None,
                 rate: Optional[float] = None,
                 exchange: Optional[Exchange] = None
                 ):

        if len(assets) < 2:
            raise InvalidPoolException()
        if len(assets) > 2 and len(amounts) != len(assets):
            raise InvalidPoolException()
        if exchange is None and (len(assets) != 2 or rate is None):
            raise InvalidPoolException()
        if exchange is None:
            exchange = Exchange("GENERIC", type_=ExchangeTypes.CLASSIC, conversion_formula=lambda i, j, x, am, **kwargs: rate*x if i == 0 else (1/rate)*x)

        self.exchange: Exchange = exchange
        self.assets = assets

        self._initial_amounts = amounts
        self.amounts = self._initial_amounts.copy()

    def convert(self, asset:str, amount: float, target:str) -> float:
        if asset == target:
            raise ImpossibleConversionException()
        start_i = self.assets.index(asset)
        end_i = self.assets.index(target)
        return self.exchange.apply_conversion(start_i, end_i, amount, self.amounts)

    def reset(self):
        self.amounts = self._initial_amounts.copy()
        pass

    def get_pairs(self) -> List[Pair]:
        pairs = list(combinations(self.assets, 2))
        pairs_obj: List[Pair] = []
        for pair in pairs:
            parsed_pair = Pair(pair[0], pair[1], self.assets.index(pair[0]), self.assets.index(pair[1]), self.convert)
            parsed_pair.parent_pool = self
            pairs_obj.append(parsed_pair)
        return pairs_obj

    def __repr__(self):
        return "-".join([str(p) for p in self.assets])+" {}".format(str(self.exchange))


class Loop(object):

    def __init__(self, pairs: List[Pair]):
        self.pairs = pairs
        self._validate()

    @property
    def initial_asset(self) -> str:
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
        return len(self.pairs)

    def convert(self, amount: float, with_fees: bool = True) -> float:
        # Run the full loop
        asset = self.initial_asset
        for pair in self.pairs:
            asset, amount = pair.convert(asset, amount, with_fees)
        # Reset pool state:
        for pair in self.pairs:
            pair.parent_pool.reset()
        return amount

    def get_max_absolute_profit(self) -> Tuple[float, float]:
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
        self._loops.sort(key = lambda l: l.convert(1, with_fees), reverse= True)
        return self._loops
