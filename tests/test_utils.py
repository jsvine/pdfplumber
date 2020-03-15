import unittest
import pdfplumber
import logging
from decimal import Decimal

logging.disable(logging.ERROR)


class Test(unittest.TestCase):

    def test_cluster_list(self):
        # For a tolerance of 2, this list of Decimals should be split into three groups
        test_numbers = list(map(Decimal, ['0', '1.1', '2.2', '3.3', '4.4', '5.5']))
        expected = [
            [Decimal('0'), Decimal('1.1')],
            [Decimal('2.2'), Decimal('3.3')],
            [Decimal('4.4'), Decimal('5.5')]
        ]
        actual = pdfplumber.utils.cluster_list(test_numbers, 2)
        assert expected == actual
