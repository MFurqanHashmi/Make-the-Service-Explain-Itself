"""Guards for the generated HTML guide.

The page is committed, so the failure mode that matters is drift: someone edits
`participant-guide.md` and never runs `./lab build-guide`. The first test below
catches exactly that, and the rest check the properties the page is useless
without — working view buttons, no unconverted Markdown, and nothing that needs
the network.
"""
import html
import json
import re
import unittest
import urllib.parse
from pathlib import Path

from workshop.scripts.build_guide import DOCUMENTS, FIGURE_DIR, render_document
from workshop.scripts.links import LINKS

ROOT = Path(__file__).parents[2]
GUIDE = (ROOT / "guide/guide.html").read_text(encoding="utf-8")
BODY = GUIDE.split('<main class="content"', 1)[1]


class BuildFreshnessTests(unittest.TestCase):
    def test_committed_pages_match_the_markdown(self):
        for source, target in DOCUMENTS:
            with self.subTest(target):
                self.assertEqual(
                    render_document(ROOT / source),
                    (ROOT / target).read_text(encoding="utf-8"),
                    f"{target} is stale; run './lab build-guide'",
                )


class GrafanaLinkTests(unittest.TestCase):
    def test_every_prepared_view_is_reachable_from_the_page(self):
        for title, url in LINKS:
            with self.subTest(title):
                self.assertIn(url.replace("&", "&amp;"), GUIDE)

    def test_every_view_title_renders_as_a_button_in_the_prose(self):
        for title, _ in LINKS:
            with self.subTest(title):
                self.assertIn(f'<span class="view-name">{title}</span>', BODY)

    def test_no_view_title_is_left_as_bold_markdown(self):
        for title, _ in LINKS:
            self.assertNotIn(f"**{title}**", BODY)


class OfflineTests(unittest.TestCase):
    def test_nothing_outside_localhost_is_requested(self):
        hosts = set(re.findall(r"https?://([^\"'/\s)]+)", GUIDE))
        self.assertEqual({"localhost:3000"}, hosts)

    def test_page_is_self_contained(self):
        self.assertNotIn("<link rel=\"stylesheet\"", GUIDE)
        self.assertNotIn("<script src=", GUIDE)


class ConversionTests(unittest.TestCase):
    def test_no_unconverted_markdown_survives(self):
        without_code = re.sub(r"<code>.*?</code>", "", BODY, flags=re.S)
        self.assertNotIn("**", without_code)
        self.assertNotIn("&lt;details", without_code)
        self.assertFalse([line for line in without_code.split("\n") if line.startswith("|")])

    def test_structure_survives_the_conversion(self):
        self.assertEqual(11, BODY.count('<section class="step"'))
        self.assertEqual(4, BODY.count('<figure class="shot">'))
        self.assertEqual(5, BODY.count('<ul class="state-grid">'))
        self.assertIn('<div class="prediction">', BODY)

    def test_quoted_queries_match_the_prepared_views(self):
        """A query printed in the guide is a promise about what its button runs."""
        for title, url in LINKS:
            if "left=" not in url:
                continue  # the dashboard link carries no query
            pane = json.loads(urllib.parse.unquote(url.split("left=", 1)[1]))
            query = pane["queries"][0].get("expr") or pane["queries"][0].get("query")
            with self.subTest(title):
                self.assertIn(
                    html.escape(query), GUIDE,
                    f"{title}: the guide quotes a query the button does not run",
                )

    def test_no_table_renders_without_rows(self):
        """The state tables become pills; their header rows have to leave with them."""
        self.assertNotIn("<tbody></tbody>", GUIDE)

    def test_in_page_anchors_resolve(self):
        targets = set(re.findall(r'id="([^"]+)"', GUIDE))
        for anchor in set(re.findall(r'href="#([^"]+)"', GUIDE)):
            with self.subTest(anchor):
                self.assertIn(anchor, targets)


class FigureTests(unittest.TestCase):
    def test_every_figure_is_used_once(self):
        for path in FIGURE_DIR.glob("*.html"):
            with self.subTest(path.stem):
                self.assertEqual(1, BODY.count(path.read_text(encoding="utf-8").strip()))

    def test_every_figure_has_a_text_equivalent(self):
        figures = re.findall(r'<figure class="diagram">.*?</figure>', BODY, flags=re.S)
        self.assertEqual(len(list(FIGURE_DIR.glob("*.html"))), len(figures))
        for figure in figures:
            self.assertIn("<title", figure)
            self.assertIn("<desc", figure)
            self.assertIn("<figcaption>", figure)
            self.assertIn('role="img"', figure)

    def test_figures_carry_no_hardcoded_colours(self):
        for path in FIGURE_DIR.glob("*.html"):
            with self.subTest(path.stem):
                self.assertFalse(re.search(r"#[0-9a-fA-F]{3,6}\b", path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
