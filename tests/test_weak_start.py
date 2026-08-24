"""Section 1 only teaches anything if the starting state is genuinely unhelpful.

Every assertion here corresponds to a way the prose logs previously gave away an
answer that participants were supposed to have to work for.
"""
import ast
import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Files whose prose logging a participant reads in section 1.
PRE_LAB_SOURCES = (
    "checkpoints/0-starter/checkout.py",
    "checkpoints/0-starter/validation.py",
    "payment/app/main.py",
    "inventory/app/main.py",
)

# Anything that would let a participant answer "which segment?" by reading a log line.
LEAKY_TOKENS = ("outcome", "currency", "discount", "rejected", "accepted", "CAD", "USD")


def logging_call_arguments(source: str):
    """Yield the source text of every argument passed to a logger.<level>() call."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        target = func.value
        if not (isinstance(target, ast.Name) and target.id == "logger"):
            continue
        if func.attr not in ("debug", "info", "warning", "error", "critical"):
            continue
        for argument in node.args:
            yield ast.unparse(argument)


def load_generator():
    sys.modules.setdefault("httpx", types.ModuleType("httpx"))
    spec = importlib.util.spec_from_file_location("traffic_generate", ROOT / "traffic/generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreLabLogTests(unittest.TestCase):
    def test_no_prose_log_names_a_business_field(self):
        for relative in PRE_LAB_SOURCES:
            source = (ROOT / relative).read_text()
            for argument in logging_call_arguments(source):
                for token in LEAKY_TOKENS:
                    self.assertNotIn(
                        token.lower(), argument.lower(),
                        f"{relative} logs '{argument}', which reveals '{token}' in section 1",
                    )

    def test_rejection_wording_is_inconsistent_and_unindexed(self):
        source = (ROOT / "checkpoints/0-starter/validation.py").read_text()
        namespace: dict = {}
        exec(re.search(r"_WEAK_MESSAGES = \([^)]*\)", source, re.S).group(0), namespace)
        messages = namespace["_WEAK_MESSAGES"]
        self.assertGreaterEqual(len(messages), 3, "one phrasing makes a text search reliable")
        self.assertEqual(len(messages), len(set(messages)))
        # No shared word long enough to be a useful search term across all three.
        word_sets = [set(re.findall(r"[a-z]{4,}", m.lower())) for m in messages]
        self.assertEqual(set(), set.intersection(*word_sets),
                         "a word common to every phrasing makes them countable with one search")

    def test_pre_lab_rejection_is_not_a_distinct_log_level(self):
        """At WARN the rejections are countable straight off Loki's level histogram."""
        source = (ROOT / "checkpoints/0-starter/validation.py").read_text()
        self.assertIn("logger.info(", source)
        self.assertNotIn("logger.warning(", source)

    def test_completed_lab_promotes_the_event_to_warning(self):
        source = (ROOT / "checkpoints/3-logs-complete/validation.py").read_text()
        self.assertIn("logger.warning(", source)


class OrderIdentifierTests(unittest.TestCase):
    def test_order_ids_are_opaque(self):
        module = load_generator()
        for name in ("healthy", "incident"):
            for row in module.profile(name):
                identifier = row["order_id"]
                # A hex digest cannot encode a segment. The old format was
                # "cad-discount-014", which answered section 1's second question
                # outright, so the shape itself is the thing worth pinning.
                self.assertRegex(identifier, r"^ord-[0-9a-f]{10}$")
                self.assertEqual(2, len(identifier.split("-")))

    def test_order_ids_are_deterministic_and_unique(self):
        first = [row["order_id"] for row in load_generator().profile("incident")]
        second = [row["order_id"] for row in load_generator().profile("incident")]
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))


class InterleavingTests(unittest.TestCase):
    def test_failing_segment_is_evenly_spread_through_the_burst(self):
        sys.path.insert(0, str(ROOT))
        from shared.domain import checkout_amount, payment_expected_amount

        rows = load_generator().profile("incident")
        failing = [
            index for index, row in enumerate(rows)
            if checkout_amount(row["unrounded_total"]) != payment_expected_amount(row["unrounded_total"])
        ]
        self.assertEqual(25, len(failing))
        for start in range(0, len(rows), 4):
            window = [i for i in failing if start <= i < start + 4]
            self.assertEqual(1, len(window),
                             "every four consecutive requests must contain exactly one failure")


if __name__ == "__main__":
    unittest.main()
