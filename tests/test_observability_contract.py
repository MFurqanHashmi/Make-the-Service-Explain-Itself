import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

class ContractTests(unittest.TestCase):
    def test_checkpoint_markers_and_cumulative_states(self):
        checkpoints = ["0-starter", "1-metrics-complete", "2-traces-complete", "3-logs-complete"]
        for checkpoint in checkpoints:
            for name in ("checkout.py", "validation.py"):
                ast.parse((ROOT / "checkpoints" / checkpoint / name).read_text())
        self.assertNotIn("checkout_completed.add", (ROOT / "checkpoints/0-starter/checkout.py").read_text())
        self.assertIn("checkout_completed.add", (ROOT / "checkpoints/1-metrics-complete/checkout.py").read_text())
        trace_code = (ROOT / "checkpoints/2-traces-complete/validation.py").read_text()
        self.assertIn('start_as_current_span("payment.amount_validation")', trace_code)
        self.assertNotIn('"expected_minor_units": expected_minor_units', trace_code)
        log_code = (ROOT / "checkpoints/3-logs-complete/validation.py").read_text()
        self.assertIn("payment.amount_validation_rejected", log_code)
        self.assertIn('"expected_minor_units": expected_minor_units', log_code)

    def test_no_sensitive_or_high_cardinality_metric_labels(self):
        code = (ROOT / "checkpoints/1-metrics-complete/checkout.py").read_text()
        metric_block = code.split("checkout_completed.add", 1)[1].split("return", 1)[0]
        for banned in ("customer_id", "trace_id", '"order_id":', '"product_id":'):
            self.assertNotIn(banned, metric_block)

    def test_dashboard_uses_pinned_datasource(self):
        dashboard = json.loads((ROOT / "telemetry/grafana/dashboards/checkout-overview.json").read_text())
        for panel in dashboard["panels"]:
            if panel.get("datasource"):
                self.assertEqual("lab-prometheus", panel["datasource"]["uid"])

if __name__ == "__main__":
    unittest.main()
