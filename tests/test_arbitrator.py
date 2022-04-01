import unittest
from trading_arbitrator.primitives import Pool, Converter
from trading_arbitrator.amm import constant_sum_amm
from trading_arbitrator.arbitrator import Arbitrator


class ArbitratorTests(unittest.TestCase):

    def setUp(self) -> None:
        self.pairs_simple = [["A", "B"], ["A", "C"], ["B", "C"]]
        self.assets = ["A", "B", "C"]
        self.assets2 = ["A", "B", "C", "D"]
        self.rates = [1.2, 0.8, 1.1]
        self.amounts = [100, 200, 300]
        self.amounts2 = [100, 200, 300, 400]
        self.converter = Converter("testC", conversion_formula=constant_sum_amm)
        self.p1 = Pool("test1", assets=self.assets, amounts=self.amounts, converter=self.converter)
        self.p2 = Pool("test2", assets=self.assets2, amounts=self.amounts2, converter=self.converter)

    def test_admits_simple_input(self):
        arb = Arbitrator(pairs=self.pairs_simple, rates=self.rates, initial_assets=["A"])
        loops = arb.get_loops(sizes=[3])
        self.assertEqual(len(loops), 2)
        loop = loops[0]
        self.assertEqual(loop.size, 3)
        expected = [["A", "B"], ["A", "C"], ["B", "C"]]
        for pair in loop.pairs:
            self.assertTrue([pair.asset0, pair.asset1] in expected)

    def test_admits_complex_pools(self):
        arb = Arbitrator(pools=[self.p1, self.p2], initial_assets=["A", "B"])
        loops = arb.get_loops(sizes=[3, 4])
        for loop in loops:
            self.assertTrue((loop.size > 2) and (loop.size < 5))
            self.assertTrue(loop.initial_asset in ["A", "B"])
