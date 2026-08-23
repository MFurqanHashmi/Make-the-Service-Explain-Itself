import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('traffic_generate', Path(__file__).parents[1]/'traffic/generate.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
from shared.domain import checkout_amount, payment_expected_amount

class ProfileTests(unittest.TestCase):
    def test_incident_profile_is_exact(self):
        rows=mod.profile('incident')
        self.assertEqual(len(rows),100)
        failures=[r for r in rows if checkout_amount(r['unrounded_total']) != payment_expected_amount(r['unrounded_total'])]
        self.assertEqual(len(failures),25)
        self.assertTrue(all(r['currency']=='CAD' and r['discounted'] for r in failures))
    def test_healthy_profile_has_no_failures(self):
        rows=mod.profile('healthy')
        self.assertEqual(len(rows),100)
        self.assertFalse([r for r in rows if checkout_amount(r['unrounded_total']) != payment_expected_amount(r['unrounded_total'])])

if __name__=='__main__': unittest.main()
