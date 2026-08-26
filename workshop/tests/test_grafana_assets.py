"""Guards for the two silent breakages that unit tests missed once already.

A prepared Grafana link can be perfectly well-formed JSON, return HTTP 200, and
still open an empty query editor. Both failures below were invisible to every
other test in this suite.
"""
import json
import re
import unittest
import urllib.parse
from pathlib import Path

from workshop.scripts.links import LINKS

ROOT = Path(__file__).parents[2]

# Loki and Prometheus carry the query in `expr`; Tempo carries it in `query`.
QUERY_FIELD_BY_DATASOURCE = {
    "lab-loki": "expr",
    "lab-prometheus": "expr",
    "lab-tempo": "query",
}


def explore_panes():
    for title, url in LINKS:
        if "/explore?" not in url:
            continue
        encoded = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["left"][0]
        yield title, json.loads(encoded)


class ExploreLinkTests(unittest.TestCase):
    def test_every_explore_link_uses_its_datasource_query_field(self):
        panes = list(explore_panes())
        self.assertEqual(3, len(panes))
        for title, pane in panes:
            datasource = pane["datasource"]
            field = QUERY_FIELD_BY_DATASOURCE[datasource]
            for query in pane["queries"]:
                self.assertIn(field, query, f"{title}: {datasource} needs its query in '{field}'")
                self.assertTrue(query[field].strip(), f"{title}: query is empty")
                # The wrong field would be silently ignored by Grafana.
                wrong = "query" if field == "expr" else "expr"
                self.assertNotIn(wrong, query, f"{title}: '{wrong}' is not read for {datasource}")

    def test_explore_links_open_in_code_mode_with_a_fixed_range(self):
        for title, pane in explore_panes():
            self.assertEqual({"from": "now-15m", "to": "now"}, pane["range"], title)
            for query in pane["queries"]:
                self.assertEqual("code", query.get("editorMode"), title)


class GrafanaAccessTests(unittest.TestCase):
    def test_anonymous_role_can_open_explore(self):
        """Viewer lacks datasources:explore, which silently redirects to the home dashboard."""
        compose = (ROOT / "workshop/compose.yaml").read_text()
        self.assertRegex(compose, r'GF_AUTH_ANONYMOUS_ENABLED:\s*"true"')
        role = re.search(r"GF_AUTH_ANONYMOUS_ORG_ROLE:\s*(\w+)", compose)
        self.assertIsNotNone(role)
        self.assertEqual(
            "Editor", role.group(1),
            "three of the four lab links open Explore, which Viewer cannot access",
        )

    def test_readiness_check_outlasts_a_cold_tempo(self):
        source = (ROOT / "workshop/scripts/check_ready.py").read_text()
        namespace: dict = {}
        for line in source.splitlines():
            if line.startswith("BUDGET_SECONDS"):
                exec(line, namespace)
        self.assertGreaterEqual(
            namespace.get("BUDGET_SECONDS", 0), 120,
            "Tempo took ~27s to become searchable; a tight budget fails the first command",
        )


class DashboardPanelTests(unittest.TestCase):
    def setUp(self):
        self.dashboard = json.loads(
            (ROOT / "workshop/telemetry/grafana/dashboards/checkout-overview.json").read_text())
        self.panels = {p["title"]: p for p in self.dashboard["panels"]}

    def test_value_panels_declare_a_reducer(self):
        """A bargauge without reduceOptions renders an unlabelled bar and no series name."""
        for title, panel in self.panels.items():
            if panel["type"] in ("stat", "bargauge"):
                calcs = panel.get("options", {}).get("reduceOptions", {}).get("calcs")
                self.assertTrue(calcs, f"{title} has no reduceOptions.calcs")

    def test_segment_panel_shows_affected_and_unaffected_groups(self):
        panel = self.panels["Checkout outcomes by segment"]
        expr = panel["targets"][0]["expr"]
        self.assertNotIn('checkout_outcome!="success"', expr,
                         "filtering out successes hides the unaffected segments")
        for label in ("checkout_currency", "checkout_discounted", "checkout_outcome"):
            self.assertIn(label, expr)
        # Reading the counter directly keeps the counts exact whole checkouts.
        self.assertNotIn("increase(", expr)
        self.assertNotIn("rate(", expr)

    def test_segment_panel_names_each_series(self):
        panel = self.panels["Checkout outcomes by segment"]
        legend = panel["targets"][0]["legendFormat"]
        for label in ("checkout_currency", "checkout_discounted", "checkout_outcome"):
            self.assertIn("{{" + label + "}}", legend)

    def test_failure_rate_panel_does_not_vanish_during_healthy_traffic(self):
        expr = self.panels["Peak business failures"]["targets"][0]["expr"]
        self.assertIn("or vector(0)", expr,
                      "without a zero fallback the panel shows No data on healthy traffic")

    def test_failure_rate_panel_ignores_windows_with_almost_no_traffic(self):
        """A window holding only the burst's last request reads 100%, and `max` keeps it."""
        expr = self.panels["Peak business failures"]["targets"][0]["expr"]
        self.assertRegex(
            expr, r"and\s+sum\(rate\(.*\)\)\s*>\s*\d",
            "without a throughput guard the tile latches onto a boundary artifact",
        )

    def test_rate_windows_fit_inside_one_traffic_burst(self):
        """The dashboard window must be shorter than the burst and shorter than the gap."""
        generate = (ROOT / "workshop/traffic/generate.py").read_text()
        spacing = float(re.search(r"REQUEST_SPACING_SECONDS = ([\d.]+)", generate).group(1))
        lead_in = float(re.search(r"LEAD_IN_SECONDS = ([\d.]+)", generate).group(1))
        burst_seconds = 100 * spacing

        windows = set()
        for panel in self.dashboard["panels"]:
            for target in panel.get("targets", []):
                windows.update(int(m) for m in re.findall(r"\[(\d+)s\]", target.get("expr", "")))
        self.assertTrue(windows)
        for window in windows:
            self.assertLessEqual(window, burst_seconds,
                                 "a window wider than the burst never reads a clean rate")
            self.assertLess(window, lead_in,
                            "a window wider than the quiet gap merges consecutive traffic runs")


if __name__ == "__main__":
    unittest.main()
