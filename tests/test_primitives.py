import unittest
from trading_arbitrator.primitives import Pool, Converter, Pair, Loop
from trading_arbitrator.errors import InvalidPoolException, ImpossibleConversionException, InvalidLoopError
from trading_arbitrator.amm import constant_product_amm, constant_sum_amm


class PoolTests(unittest.TestCase):

    def setUp(self) -> None:
        self.assets = ["A", "B"]
        self.assets_multi = ["A", "B", "C"]
        self.amounts = [200, 300, 400]
        self.rate = 1.2

    def test_instantiates_converter(self):
        p = Pool(name="test", assets=self.assets, rate=self.rate)
        self.assertTrue(isinstance(p.exchange, Converter))

    def test_creates_classic_converter(self):
        p = Pool(name="test", assets=self.assets, rate=self.rate)
        conv_f = p.exchange.conversion_formula
        self.assertEqual(conv_f(0, 1, 1, 1), self.rate)
        self.assertEqual(conv_f(1, 0, 1, 1), 1 / self.rate)

    def test_raises(self):
        args = {
            "name": "test",
            "assets": ["A"],
            "rate": 1.2
        }
        self.assertRaises(InvalidPoolException, Pool, **args)
        args = {
            "name": "test",
            "assets": ["A", "B", "C"],
            "amounts": [100, 200, 300, 400],
            "converter": Converter("test", conversion_formula=constant_product_amm)
        }
        self.assertRaises(InvalidPoolException, Pool, **args)
        args = {
            "name": "test",
            "assets": ["A", "B"],
            "amounts": [100, 200]
        }
        self.assertRaises(InvalidPoolException, Pool, **args)

    def test_raises_conversion(self):
        args = {
            "name": "test",
            "assets": ["A", "B", "C"],
            "amounts": [100, 200, 300],
            "converter": Converter("test", conversion_formula=constant_product_amm)
        }
        p = Pool(**args)
        c_args = {
            "asset": "A",
            "amount": 1,
            "target": "A",
            "with_fees": False
        }
        self.assertRaises(ImpossibleConversionException, p.convert, **c_args)

    def test_resets_amounts(self):
        args = {
            "name": "test",
            "assets": ["A", "B", "C"],
            "amounts": [100, 200, 300],
            "converter": Converter("test", conversion_formula=constant_product_amm)
        }
        p = Pool(**args)
        p.convert("A", 100, "B", False)
        self.assertTrue([100, 200, 300] != p.amounts)
        p.reset()
        self.assertTrue([100, 200, 300] == p.amounts)

    def test_generates_pairs(self):
        args = {
            "name": "test",
            "assets": ["A", "B", "C"],
            "amounts": [100, 200, 300],
            "converter": Converter("test", conversion_formula=constant_product_amm)
        }
        p = Pool(**args)
        pairs = p.get_pairs()
        for pair in pairs:
            self.assertTrue(isinstance(pair, Pair))
        self.assertEqual(len(pairs), 3)
        expected = [["A", "B"], ["A", "C"], ["B", "C"]]
        for pair in pairs:
            self.assertTrue([pair.asset0, pair.asset1] in expected)

    def test_properly_converts(self):
        args = {
            "name": "test",
            "assets": ["A", "B", "C"],
            "amounts": [100, 200, 300],
            "converter": Converter("test", conversion_formula=constant_sum_amm, fee=10)
        }
        p = Pool(**args)
        result = p.convert("A", 10, "B", True)
        self.assertEqual(9, result)  # 10% fee on a stablecoin swap


class LoopTests(unittest.TestCase):

    def setUp(self) -> None:
        self.assets = ["A", "B", "C"]
        self.amounts = [100, 200, 300]
        self.converter = Converter("test", conversion_formula=constant_sum_amm)
        self.p = Pool(name="test", assets=self.assets, amounts=self.amounts, converter=self.converter)
        self.pairs = self.p.get_pairs()
        self.loop = Loop(self.pairs)

    def test_initial_asset(self):
        self.assertEqual(self.loop.initial_asset, "B")

    def test_size(self):
        self.assertEqual(self.loop.size, 3)

    def test_convert(self):
        result = self.loop.convert(1, False)
        self.assertEqual(result, 1)
        self.converter._fee = 10
        result = self.loop.convert(1, True)
        self.assertAlmostEqual(result, 1 * 0.9 * 0.9 * 0.9)  # Fucking rounding errors...

    def test_validate(self):
        self.pairs[0].asset0 = "C"
        self.assertRaises(InvalidLoopError, Loop, self.pairs)
        self.pairs[0].asset0 = "A"
        self.assertRaises(InvalidLoopError, Loop, self.pairs[:-1])
        self.assertRaises(InvalidLoopError, Loop, self.pairs[:-1] + [self.pairs[1]])
