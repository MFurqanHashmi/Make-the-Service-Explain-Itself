import json, unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class StructureTests(unittest.TestCase):
    def test_starter_has_one_marker_and_no_add(self):
        text=(ROOT/'checkpoints/0-starter/checkout.py').read_text()
        self.assertEqual(text.count('# LAB 1: record checkout result'),1)
        self.assertNotIn('checkout_completed.add(',text)
    def test_complete_has_one_marker_and_one_add(self):
        text=(ROOT/'checkpoints/1-metrics-complete/checkout.py').read_text()
        self.assertEqual(text.count('# LAB 1: record checkout result'),1)
        self.assertEqual(text.count('checkout_completed.add('),1)
    def test_dashboard_has_pinned_uid_and_queries(self):
        data=json.loads((ROOT/'telemetry/grafana/dashboards/checkout-overview.json').read_text())
        self.assertEqual(data['uid'],'checkout-overview')
        expressions='\n'.join(t.get('expr','') for p in data['panels'] for t in p.get('targets',[]))
        self.assertIn('checkout_completed.*',expressions)
        self.assertIn('checkout_http_responses.*',expressions)

if __name__=='__main__': unittest.main()
