"""Render the lab documents as self-contained HTML pages.

`participant-guide.md` stays the source of truth. This script converts it (and
the worksheet) into `guide.html` / `worksheet.html`, injecting the prepared
Grafana URLs from `scripts.links` so the page and `./lab links` can never
disagree.

The Markdown subset is deliberately narrow and the parser is strict: anything it
cannot classify raises, so a document can never lose content silently.

Run it with `./lab build-guide`.
"""
import html
import re
import sys
from pathlib import Path

from workshop.scripts.links import LINKS

ROOT = Path(__file__).parents[2]
TEMPLATE_DIR = Path(__file__).parent / "guide_template"
FIGURE_DIR = TEMPLATE_DIR / "figures"

DOCUMENTS = [
    ("guide/participant-guide.md", "guide/guide.html"),
    ("guide/worksheet.md", "guide/worksheet.html"),
]

LINK_BY_TITLE = dict(LINKS)
STATE_QUESTIONS = ["Detect", "Scope", "Isolate", "Explain"]


class GuideError(RuntimeError):
    """A document used syntax this renderer does not support."""


# --------------------------------------------------------------------------
# inline
# --------------------------------------------------------------------------

def slug(text):
    """GitHub's heading slug, so existing in-page anchors keep working."""
    text = re.sub(r"`|\*|_", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r"\s+", "-", text)


def view_button(title, inline=True):
    url = LINK_BY_TITLE[title]
    cls = "view-link" if inline else "view-button"
    return (
        f'<a class="{cls}" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">'
        f'<span class="view-name">{html.escape(title)}</span>'
        f'<span class="view-arrow" aria-hidden="true">↗</span>'
        f'<span class="print-url">{html.escape(url)}</span></a>'
    )


def inline(text):
    """Convert inline Markdown.

    Code spans are lifted out first and put back last, so emphasis that wraps a
    code span (`**`set_status(...)`**`) still resolves, and nothing inside a
    code span is ever treated as markup.
    """
    if text.count("`") % 2:
        raise GuideError(f"unbalanced code span: {text!r}")
    spans = []
    parts = []
    for index, part in enumerate(text.split("`")):
        if index % 2:
            parts.append(f"\x00{len(spans)}\x00")
            spans.append(f"<code>{html.escape(part)}</code>")
        else:
            parts.append(part)
    rendered = _inline_plain("".join(parts))
    for index, span in enumerate(spans):
        rendered = rendered.replace(f"\x00{index}\x00", span)
    return rendered


def _inline_plain(text):
    text = html.escape(text)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy">',
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{_rewrite_href(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    for title in LINK_BY_TITLE:
        text = text.replace(f"**{html.escape(title)}**", view_button(title))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"_{4,}", '<span class="blank"></span>', text)
    return text


def _rewrite_href(href):
    if href == "worksheet.md":
        return "worksheet.html"
    return html.escape(href, quote=True)


# --------------------------------------------------------------------------
# blocks
# --------------------------------------------------------------------------

class Reader:
    def __init__(self, lines):
        self.lines = lines
        self.index = 0

    def peek(self, offset=0):
        position = self.index + offset
        return self.lines[position] if position < len(self.lines) else None

    def next(self):
        line = self.lines[self.index]
        self.index += 1
        return line

    @property
    def done(self):
        return self.index >= len(self.lines)


def render_blocks(lines, figures_used):
    reader = Reader(lines)
    parts = []
    while not reader.done:
        block = _render_block(reader, figures_used)
        if not block:
            continue
        # A prediction and the reveal that answers it are one card, not two.
        if (
            block.startswith('<details class="reveal reveal-answer"')
            and parts
            and parts[-1].startswith('<aside class="callout callout-prediction"')
        ):
            parts[-1] = f'<div class="prediction">{parts[-1]}{block}</div>'
        else:
            parts.append(block)
    return "\n".join(parts)


def _render_block(reader, figures_used):
    line = reader.peek()

    if not line.strip():
        reader.next()
        return ""

    if line.startswith("```"):
        return _fence(reader)

    if line.startswith("<!--"):
        return _comment(reader, figures_used)

    if line.startswith("<details>"):
        return _details(reader, figures_used)

    if line.startswith("#"):
        return _heading(reader)

    if line.startswith("---"):
        reader.next()
        return '<hr class="rule">'

    if line.startswith("> "):
        return _blockquote(reader)

    if line.startswith("|"):
        return _table(reader)

    if re.match(r"^(-|\d+\.) ", line):
        return _list(reader)

    if line.startswith("<"):
        raise GuideError(f"unsupported raw HTML block: {line!r}")

    if line.startswith("    "):
        raise GuideError(f"indented code blocks are not supported: {line!r}")

    return _paragraph(reader)


def _fence(reader):
    language = reader.next()[3:].strip() or "text"
    if language not in {"bash", "python", "text"}:
        raise GuideError(f"unsupported code fence language: {language!r}")
    body = []
    while not reader.done and not reader.peek().startswith("```"):
        body.append(reader.next())
    if reader.done:
        raise GuideError("unterminated code fence")
    reader.next()
    code = "\n".join(body)
    raw = html.escape(code, quote=True)

    if language == "text":
        return f'<pre class="plain"><code>{html.escape(code)}</code></pre>'

    kind = "terminal" if language == "bash" else "code"
    label = "Terminal" if language == "bash" else "python"
    lines_html = []
    for entry in code.split("\n"):
        if language == "bash" and entry.strip():
            lines_html.append(f'<span class="cmd">{html.escape(entry)}</span>')
        else:
            lines_html.append(html.escape(entry))
    return (
        f'<div class="{kind} card">'
        f'<div class="card-bar"><span class="card-label">{label}</span>'
        f'<button class="copy" type="button" hidden data-copy="{raw}">Copy</button></div>'
        f'<pre><code>{chr(10).join(lines_html)}</code></pre></div>'
    )


def _comment(reader, figures_used):
    line = reader.next().strip()
    match = re.fullmatch(r"<!-- figure: ([a-z0-9-]+)( replaces-next)? -->", line)
    if not match:
        raise GuideError(f"unsupported HTML comment: {line!r}")
    name, replaces = match.group(1), bool(match.group(2))
    path = FIGURE_DIR / f"{name}.html"
    if not path.exists():
        raise GuideError(f"no figure named {name!r} in {FIGURE_DIR}")
    figures_used.add(name)
    if replaces:
        while not reader.done and not reader.peek().strip():
            reader.next()
        _render_block(reader, figures_used)
    return path.read_text(encoding="utf-8").strip()


def _details(reader, figures_used):
    reader.next()
    summary_line = reader.next().strip()
    match = re.fullmatch(r"<summary>(.*)</summary>", summary_line)
    if not match:
        raise GuideError(f"<details> must be followed by a single <summary>: {summary_line!r}")
    summary = match.group(1)
    body = []
    depth = 1
    while not reader.done:
        line = reader.next()
        if line.startswith("<details>"):
            depth += 1
        if line.startswith("</details>"):
            depth -= 1
            if not depth:
                break
        body.append(line)
    else:
        raise GuideError("unterminated <details> block")
    return (
        f'<details class="reveal reveal-{_reveal_kind(summary)}">'
        f"<summary>{inline(summary)}</summary>"
        f'<div class="reveal-body">{render_blocks(body, figures_used)}</div>'
        f"</details>"
    )


def _reveal_kind(summary):
    lowered = summary.lower()
    if lowered.startswith("show"):
        return "spoiler"
    if lowered.startswith("verify"):
        return "verify"
    if lowered.startswith(("predict", "check")):
        return "answer"
    return "note"


def _heading(reader):
    line = reader.next()
    level = len(line) - len(line.lstrip("#"))
    if level > 3:
        raise GuideError(f"heading deeper than h3: {line!r}")
    text = line[level:].strip()
    if level == 1:
        return f'<h1 class="doc-title">{inline(text)}</h1>'
    return f'<h{level} id="{slug(text)}">{inline(text)}</h{level}>'


def _blockquote(reader):
    body = []
    while not reader.done and reader.peek().startswith(">"):
        body.append(reader.next().lstrip(">").strip())
    text = " ".join(body).strip()
    for marker, kind, label in [
        ("**Your move:**", "move", "Your move"),
    ]:
        if text.startswith(marker):
            return _callout(kind, label, text, marker if marker.endswith("**") else None)
    return f'<blockquote class="quote">{inline(text)}</blockquote>'


def _callout(kind, label, text, strip):
    if strip:
        text = text[len(strip):].strip()
    return (
        f'<aside class="callout callout-{kind}">'
        f'<p class="callout-label">{html.escape(label)}</p>'
        f"<p>{inline(text)}</p></aside>"
    )


def _table(reader):
    rows = []
    while not reader.done and reader.peek().startswith("|"):
        rows.append([cell.strip() for cell in reader.next().strip().strip("|").split("|")])
    if len(rows) < 2 or not set("".join(rows[1])) <= set("-: "):
        raise GuideError(f"table without a header separator: {rows[:2]!r}")
    header, body = rows[0], rows[2:]
    head = "".join(f"<th>{inline(cell)}</th>" for cell in header)
    out = [f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>']
    for row in body:
        cells = "".join(f"<td>{inline(cell)}</td>" for cell in row)
        out.append(f"<tr>{cells}</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _list(reader):
    ordered = bool(re.match(r"^\d+\. ", reader.peek()))
    items = []
    while not reader.done:
        line = reader.peek()
        if not line.strip():
            following = reader.peek(1) or ""
            if not re.match(r"^(-|\d+\.) ", following):
                break
            reader.next()
            continue
        if re.match(r"^(-|\d+\.) ", line):
            items.append([re.sub(r"^(-|\d+\.) ", "", reader.next())])
        elif line.startswith("  ") and items:
            items[-1].append(reader.next().strip())
        else:
            break
    rendered = []
    for item in items:
        text = " ".join(item)
        task = re.match(r"^\[( |x)\] (.*)", text)
        if task:
            box = '<span class="task-box" aria-hidden="true"></span>'
            rendered.append(f'<li class="task">{box}{inline(task.group(2))}</li>')
        else:
            rendered.append(f"<li>{inline(text)}</li>")
    tag = "ol" if ordered else "ul"
    return f'<{tag} class="list">{"".join(rendered)}</{tag}>'


def _paragraph(reader):
    body = []
    while not reader.done and reader.peek().strip():
        line = reader.peek()
        if line.startswith(("#", "```", "|", ">", "<", "---")) or re.match(r"^(-|\d+\.) ", line):
            break
        body.append(reader.next().strip())
    text = " ".join(body)

    if re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", text):
        return _screenshot(text)

    for marker, kind, label in [
        ("**Before you move on:**", "checkpoint", "Before you move on"),
        ("**Prediction:**", "prediction", "Prediction"),
        ("**Prediction before you move on:**", "prediction", "Prediction"),
    ]:
        if text.startswith(marker):
            return _callout(kind, label, text, marker)
    return f"<p>{inline(text)}</p>"


def _screenshot(text):
    alt, src = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", text).groups()
    return (
        '<figure class="shot">'
        f'<button class="shot-zoom" type="button" aria-label="Enlarge screenshot">'
        f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt)}" loading="lazy">'
        "</button>"
        f"<figcaption>{html.escape(alt)}</figcaption></figure>"
    )


# --------------------------------------------------------------------------
# document structure
# --------------------------------------------------------------------------

def split_sections(lines):
    """Split a document into (heading, body-lines) pairs on `##` headings."""
    preamble, sections, current = [], [], None
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = [line[3:].strip(), []]
        elif current:
            current[1].append(line)
        else:
            preamble.append(line)
    if current:
        sections.append(current)
    return preamble, sections


def take_state_table(body):
    """Pull a Detect/Scope/Isolate/Explain table out of a section body.

    Returns (lines before the table, lines after it, {question: (glyph, reason)},
    the heading lines it was introduced by) so the table can be rendered as
    status pills in its own place and reused in the sidebar. The rows above
    `| **Detect**` — the header and its `| --- |` separator — have to come away
    with it, or the page keeps a table that renders nothing but a header.
    """
    for index, line in enumerate(body):
        if not line.startswith("| **Detect**"):
            continue
        end = index
        while end < len(body) and body[end].startswith("|"):
            end += 1
        state = {}
        for row in body[index:end]:
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            question = re.sub(r"\*\*(.+?)\*\*.*", r"\1", cells[0])
            descriptor = re.sub(r"^\*\*.+?\*\*\s*—?\s*", "", cells[0])
            glyph, _, reason = cells[1].partition(" ")
            state[question] = (glyph, descriptor or reason)
        start = index
        while start and body[start - 1].startswith("|"):
            start -= 1
        while start and not body[start - 1].strip():
            start -= 1
        if start and body[start - 1].startswith("### "):
            start -= 1
            while start and not body[start - 1].strip():
                start -= 1
        return body[:start], body[end:], state, body[start:index]
    return body, [], None, []


def state_block(heading_lines, state):
    heading = ""
    for line in heading_lines:
        if line.startswith("### "):
            title = line[4:].strip()
            heading = f'<h3 id="{slug(title)}">{inline(title)}</h3>'
    pills = []
    for question in STATE_QUESTIONS:
        glyph, reason = state[question]
        answered = "yes" if glyph == "✅" else "no"
        pills.append(
            f'<li class="pill pill-{answered}">'
            f'<span class="pill-glyph" aria-hidden="true">{glyph}</span>'
            f'<span class="pill-name">{question}</span>'
            f'<span class="pill-reason">{inline(reason)}</span>'
            f'<span class="visually-hidden">: {"answered" if answered == "yes" else "not answered"}</span>'
            "</li>"
        )
    return f'{heading}<ul class="state-grid">{"".join(pills)}</ul>'


def render_document(md_path):
    lines = md_path.read_text(encoding="utf-8").split("\n")
    figures_used = set()
    preamble, sections = split_sections(lines)

    title_line = next((line for line in preamble if line.startswith("# ")), None)
    if not title_line:
        raise GuideError(f"{md_path.name} has no H1")
    title = title_line[2:].strip()

    body_parts = [render_blocks(preamble, figures_used)]
    nav_items = []
    tracked = False
    running_state = {question: ("—", "not yet") for question in STATE_QUESTIONS}

    for number, (heading, section_body) in enumerate(sections, start=1):
        section_body, after_state, state, state_heading = take_state_table(section_body)
        if state:
            running_state = state
            tracked = True

        match = re.match(r"^(\d+)\.\s+(.*)", heading)
        step_number, step_title = (match.group(1), match.group(2)) if match else ("", heading)

        time_chip = ""
        for index, line in enumerate(section_body):
            found = re.match(r"^\*\*(\d{2}:\d{2})\.\*\*\s*(.*)", line)
            if found:
                time_chip = found.group(1)
                section_body[index] = found.group(2)
                break

        anchor = slug(heading)
        nav_items.append(
            f'<li><a href="#{anchor}" data-nav="{anchor}">'
            f'<span class="nav-time">{time_chip or "&nbsp;"}</span>'
            f'<span class="nav-title">{html.escape(step_title)}</span></a></li>'
        )

        badge = f'<span class="step-badge">{step_number}</span>' if step_number else ""
        chip = f'<span class="step-time">{time_chip}</span>' if time_chip else ""
        rendered = render_blocks(section_body, figures_used)
        if state:
            # The pills stand where the table stood, so the heading that
            # introduces them is not left stranded above a section divider.
            rendered += state_block(state_heading, state)
        rendered += render_blocks(after_state, figures_used)

        data_state = " ".join(
            f'data-{question.lower()}="{"yes" if glyph == chr(9989) else "no" if glyph == chr(10060) else "unknown"}"'
            for question, (glyph, _) in running_state.items()
        )
        body_parts.append(
            f'<section class="step" id="{anchor}" data-step="{anchor}" {data_state}>'
            f'<header class="step-head">{badge}{chip}'
            f'<h2 id="{anchor}-title">{inline(heading if not step_number else step_title)}</h2>'
            f"</header>{rendered}</section>"
        )

    unused = {path.stem for path in FIGURE_DIR.glob("*.html")} - figures_used
    if unused and md_path.name == "participant-guide.md":
        raise GuideError(f"figures never referenced by the guide: {sorted(unused)}")

    return assemble(title, "".join(nav_items), "\n".join(body_parts), tracked)


def assemble(title, nav_items, body, tracked):
    template = (TEMPLATE_DIR / "page.html").read_text(encoding="utf-8")
    style = (TEMPLATE_DIR / "style.css").read_text(encoding="utf-8")
    script = (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")
    views = "".join(f"<li>{view_button(name, inline=False)}</li>" for name, _ in LINKS)
    readout = "".join(
        f'<li class="readout-item" data-readout="{question.lower()}">'
        f'<span class="readout-glyph" aria-hidden="true">—</span>{question}</li>'
        for question in STATE_QUESTIONS
    ) if tracked else ""
    if not tracked:
        template = template.replace(
            '<p class="nav-label">What you can answer</p>\n      <ul class="readout" id="readout">{{readout}}</ul>',
            "",
        )
    replacements = {
        "{{title}}": html.escape(title),
        "{{style}}": style,
        "{{script}}": script,
        "{{views}}": views,
        "{{nav}}": nav_items,
        "{{readout}}": readout,
        "{{body}}": body,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def main():
    for source, target in DOCUMENTS:
        rendered = render_document(ROOT / source)
        (ROOT / target).write_text(rendered, encoding="utf-8")
        print(f"BUILT: {target} from {source}")


if __name__ == "__main__":
    try:
        main()
    except GuideError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
