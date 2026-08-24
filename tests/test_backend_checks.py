import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import check_logs, check_metrics, check_traces

class MetricsDeltaTests(unittest.TestCase):
    def test_series_born_inside_window_uses_zero_baseline(self):
        rows=[{"metric":{"checkout_outcome":"payment_rejected"},"values":[[105,"11"],[110,"25"]]}]
        self.assertEqual(25.0, check_metrics.deltas(rows,100)[0][1])
    def test_existing_series_uses_pre_window_baseline(self):
        rows=[{"metric":{},"values":[[99,"7"],[101,"8"],[110,"17"]]}]
        self.assertEqual(10.0, check_metrics.deltas(rows,100)[0][1])
    def test_counter_reset_uses_zero_baseline(self):
        rows=[{"metric":{},"values":[[99,"80"],[101,"1"],[110,"25"]]}]
        self.assertEqual(25.0, check_metrics.deltas(rows,100)[0][1])

    def test_reset_hidden_behind_a_stale_pre_reload_value(self):
        """A series the reloaded process has not touched keeps reporting its old value.

        The drop only appears once traffic reaches that series, so a reset check
        that looks only at the window's first sample computes a negative delta and
        clamps it to zero. This is what broke './lab recover metrics'.
        """
        rows=[{"metric":{},"values":[[99,"100"],[101,"100"],[103,"100"],[105,"2"],[110,"25"]]}]
        self.assertEqual(25.0, check_metrics.deltas(rows,100)[0][1])

    def test_multiple_resets_in_one_window(self):
        rows=[{"metric":{},"values":[[101,"5"],[103,"2"],[105,"7"],[107,"3"]]}]
        # 5 + 2 + (7-2) + 3 = 15
        self.assertEqual(15.0, check_metrics.deltas(rows,100)[0][1])

class TraceCheckTests(unittest.TestCase):
    def test_finds_error_span_without_explanation_fields(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)/"state.json"; out=Path(td)/"trace.json"
            state.write_text(json.dumps({"started_at":100.0}))
            def fake(_base,path,params=None):
                if path=="/api/search": return {"traces":[{"traceID":"abc123"}]}
                return {"batches":[
                    {"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"checkout"}}]},"scopeSpans":[{"spans":[{"name":"POST /checkout","status":{"code":0},"attributes":[{"key":"http.response.status_code","value":{"intValue":200}}]}]}]},
                    {"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"inventory"}}]},"scopeSpans":[{"spans":[{"name":"POST /reserve","status":{"code":0},"attributes":[]}]}]},
                    {"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"payment"}}]},"scopeSpans":[{"spans":[{"name":"payment.amount_validation","status":{"code":2},"attributes":[{"key":"validation.result","value":{"stringValue":"rejected"}},{"key":"payment.currency","value":{"stringValue":"CAD"}},{"key":"payment.discounted","value":{"boolValue":True}}]}]}]}
                ]}
            with patch.object(check_traces,"STATE",state), patch.object(check_traces,"OUT",out), patch.object(check_traces,"get_json",fake):
                self.assertEqual("abc123",check_traces.find()[0])
                self.assertEqual("abc123",json.loads(out.read_text())["trace_id"])

class LogCheckTests(unittest.TestCase):
    def test_parses_loki_structured_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)/"state.json"; state.write_text(json.dumps({"started_at":100.0}))
            metadata={"event_name":"payment.amount_validation_rejected","reason_code":"minor_unit_mismatch","payment_currency":"CAD","payment_discounted":"true","expected_minor_units":"1000","received_minor_units":"1001","checkout_rounding_mode":"HALF_UP","payment_rounding_mode":"HALF_EVEN","trace_id":"a"*32,"span_id":"b"*16}
            payload={"status":"success","data":{"result":[{"stream":{"service_name":"payment"},"values":[["1","Payment amount validation rejected",metadata]]}]}}
            with patch.object(check_logs,"STATE",state), patch.object(check_logs,"get_json",return_value=payload):
                rows=check_logs.find()
                self.assertEqual(1,len(rows)); self.assertEqual("1001",rows[0]["received_minor_units"])

if __name__=="__main__": unittest.main()
