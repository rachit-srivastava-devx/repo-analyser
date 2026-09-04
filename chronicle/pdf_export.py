"""Assembles the deep .md reports + charts into one polished PDF, styled to
The DevX Doctrine (v1.0, April 2026): editorial restraint, one accent color
used sparingly, hairline rules over shadows/boxes, sharp corners, real
doctrine fonts (Inter Tight / Source Serif 4 / JetBrains Mono) embedded
directly rather than substituted with a system sans.

Markdown -> HTML (python-markdown, tables extension) -> PDF (WeasyPrint).
Doctrine section 6.3 ("Internal docs, memos, PRDs") governs this surface:
strip slide/deck chrome, keep the type stack, hairline table rules with no
zebra striping, JetBrains Mono code blocks on Paper-3, max-width for prose.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

import markdown as md_lib
from weasyprint import HTML

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


def _font_b64(name: str) -> str:
    return base64.b64encode((_FONTS_DIR / name).read_bytes()).decode("ascii")


def _build_css() -> str:
    inter = _font_b64("InterTight-Regular.ttf")
    serif_italic = _font_b64("SourceSerif4-Italic.ttf")
    serif_regular = _font_b64("SourceSerif4-Regular.ttf")
    mono = _font_b64("JetBrainsMono-Regular.ttf")
    mono_medium = _font_b64("JetBrainsMono-Medium.ttf")
    return f"""
@font-face {{ font-family: 'Inter Tight'; src: url(data:font/ttf;base64,{inter}) format('truetype'); font-weight: 300 700; }}
@font-face {{ font-family: 'Source Serif 4'; src: url(data:font/ttf;base64,{serif_regular}) format('truetype'); font-style: normal; font-weight: 400 600; }}
@font-face {{ font-family: 'Source Serif 4'; src: url(data:font/ttf;base64,{serif_italic}) format('truetype'); font-style: italic; font-weight: 400 600; }}
@font-face {{ font-family: 'JetBrains Mono'; src: url(data:font/ttf;base64,{mono}) format('truetype'); font-weight: 400; }}
@font-face {{ font-family: 'JetBrains Mono'; src: url(data:font/ttf;base64,{mono_medium}) format('truetype'); font-weight: 500; }}

:root {{
  --ink: #0A0A0A; --ink-2: #1A1A1A; --muted: #5C6066; --muted-2: #8A8F96;
  --rule: #E5E5E5; --rule-2: #F0F0F0;
  --paper: #FFFFFF; --paper-2: #FAFAF8; --paper-3: #F4F4F1;
  --accent: #1E6FFF; --accent-soft: #E8F0FF;
  --warn: #C0392B; --ok: #0A7C53;
  --f-display: 'Inter Tight', sans-serif;
  --f-serif: 'Source Serif 4', Georgia, serif;
  --f-mono: 'JetBrains Mono', monospace;
}}

@page {{
    size: A4;
    margin: 24mm 20mm;
    @bottom-center {{ content: counter(page) " / " counter(pages); color: var(--muted-2); font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.08em; }}
}}
body {{
    background: var(--paper);
    color: var(--ink-2);
    font-family: var(--f-display);
    font-weight: 400;
    font-size: 10.5px;
    line-height: 1.6;
    max-width: 960px;
}}

/* -- The monospace eyebrow (doctrine pattern 4.2): a small uppercase label
   emitted by deep_reports.py as <p class="eyebrow"> right before each H1. -- */
p.eyebrow {{
    font-family: var(--f-mono);
    font-size: 9px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 6px 0;
    page-break-before: always;
    page-break-after: avoid;
}}
p.eyebrow:first-of-type {{ page-break-before: avoid; }}

h1 {{
    font-family: var(--f-display);
    font-weight: 500;
    letter-spacing: -0.02em;
    font-size: 22px;
    color: var(--ink);
    margin: 0 0 10px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--ink); /* doctrine 3.4 "Heavy" rule: separates a heading from its content */
    page-break-after: avoid;
}}
/* The signature device (doctrine 4.1): one key word per headline switches
   to italic Source Serif 4 in accent color. deep_reports.py wraps exactly
   one word per H1 in markdown *emphasis* for this; it is scoped to h1 only
   -- body-text emphasis (doctrine's general editorial italic) stays muted,
   not accent, so the accent stays within "used 2-4 times per surface." */
h1 em {{
    font-family: var(--f-serif);
    font-style: italic;
    font-weight: 400;
    color: var(--accent);
}}

h2 {{
    font-family: var(--f-display);
    font-weight: 500;
    letter-spacing: -0.01em;
    font-size: 13px;
    color: var(--ink);
    margin-top: 22px;
    margin-bottom: 8px;
}}
h3 {{
    font-family: var(--f-mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 16px;
}}

em {{
    font-family: var(--f-serif);
    font-style: italic;
    color: var(--muted);
}}
strong {{
    font-weight: 600;
    color: var(--ink);
}}
p {{ margin: 0 0 10px 0; }}

code {{
    background: var(--paper-3);
    color: var(--ink-2);
    padding: 1px 5px;
    font-family: var(--f-mono);
    font-size: 9px;
}}
pre {{
    background: var(--paper-3);
    padding: 10px 12px;
    overflow-x: auto;
}}
pre code {{ background: none; padding: 0; }}

table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0 18px 0;
    font-size: 9px;
}}
th {{
    font-family: var(--f-mono);
    font-size: 8px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    text-align: left;
    color: var(--muted);
    padding: 6px 10px;
    border-bottom: 1px solid var(--ink);
}}
td {{
    padding: 5px 10px;
    border-bottom: 1px solid var(--rule-2);
    color: var(--ink-2);
    font-family: var(--f-display);
}}
/* doctrine 6.3: hairline rules, no zebra striping, no row backgrounds -- deliberately no tr:nth-child rule here */

img {{
    max-width: 100%;
    margin: 14px 0;
    /* doctrine 4.10 / 5: sharp corners, no border, no shadow on document images */
}}

a {{ color: var(--accent); text-decoration: none; }}
ul, ol {{ padding-left: 20px; }}
li {{ margin-bottom: 4px; }}
hr {{ border: none; border-top: 1px solid var(--rule); margin: 18px 0; }}

.cover {{
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: center;
    height: 100%;
}}
.cover p.eyebrow {{ page-break-before: avoid; font-size: 10px; }}
.cover h1 {{
    border: none;
    font-size: 34px;
    padding-bottom: 0;
    page-break-before: avoid;
    margin: 10px 0 16px 0;
}}
.cover .meta {{
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 0.02em;
    border-top: 1px solid var(--rule);
    padding-top: 12px;
    margin-top: 4px;
}}
"""


CSS = _build_css()

# One key word per report title is wrapped in *emphasis* by deep_reports.py
# for the h1-em accent-serif treatment. A bare "# Title" with no emphasis
# still renders correctly (h1 default color), so older/unmodified report
# generators degrade gracefully rather than breaking.
EYEBROW_RE = re.compile(r"^# (.+)$", re.MULTILINE)


def _inject_eyebrow(markdown_text: str, label: str) -> str:
    """Prepends a doctrine-pattern monospace eyebrow paragraph before the
    first H1 in a markdown document, if one isn't already present."""
    if "class=\"eyebrow\"" in markdown_text or markdown_text.strip().startswith('<p class="eyebrow"'):
        return markdown_text
    return EYEBROW_RE.sub(lambda m: f'<p class="eyebrow">{label}</p>\n\n# {m.group(1)}', markdown_text, count=1)


def build_pdf(report_dir: Path, out_pdf: Path, title: str, report_order: list[str] | None = None) -> Path:
    """report_dir must contain the *.md deep reports and a charts/ subdir
    with the PNGs those reports reference by relative path (`charts/x.png`)."""
    if report_order is None:
        from .deep_reports import REPORT_SEQUENCE
        present = {p.name for p in report_dir.glob("*.md")}
        # narrative order first (matches deep_reports.generate_all's sequence,
        # not alphabetical -- REPO_ANALYSIS must lead, not "C..." < "R..."),
        # then anything else present that generate_all doesn't know about.
        ordered = [name for name, _ in REPORT_SEQUENCE if name in present]
        ordered += sorted(present - set(ordered) - {"REPORT.md"})
        md_files = ordered
    else:
        md_files = report_order
    if not md_files:
        raise FileNotFoundError(f"no .md reports found in {report_dir}")

    from datetime import date
    html_parts = [f"""
    <div class="cover">
        <p class="eyebrow">Chronicle Analyzer</p>
        <h1>{title}</h1>
        <div class="meta">Generated {date.today().isoformat()} &middot; {len(md_files)} sections &middot;
        every figure traces to a CSV/JSON in this run's output directory</div>
    </div>
    """]

    converter = md_lib.Markdown(extensions=["tables", "fenced_code"])
    for i, name in enumerate(md_files, start=1):
        path = report_dir / name
        if not path.exists():
            continue
        text = path.read_text()
        section_label = f"Section {i:02d} / {name[:-3].replace('_', ' ').title()}"
        text = _inject_eyebrow(text, section_label)
        converter.reset()
        html = converter.convert(text)
        html_parts.append(html)

    full_html = f"<html><head><style>{CSS}</style></head><body>{''.join(html_parts)}</body></html>"
    HTML(string=full_html, base_url=str(report_dir)).write_pdf(str(out_pdf))
    return out_pdf
