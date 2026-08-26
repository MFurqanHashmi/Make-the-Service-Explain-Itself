import unittest
from shared.domain import checkout_amount, payment_expected_amount

class RoundingTests(unittest.TestCase):
    def test_discounted_cad_differs_by_one_cent(self):
        self.assertEqual(checkout_amount("10.005"), 1001)
        self.assertEqual(payment_expected_amount("10.005"), 1000)
    def test_discounted_usd_agrees(self):
        self.assertEqual(checkout_amount("10.015"), 1002)
        self.assertEqual(payment_expected_amount("10.015"), 1002)
    def test_exact_cad_agrees(self):
        self.assertEqual(checkout_amount("10.00"), 1000)
        self.assertEqual(payment_expected_amount("10.00"), 1000)

if __name__ == '__main__': unittest.main()
