"""Chart rendering, styled to The DevX Doctrine (v1.0, April 2026): editorial
restraint, one accent color used sparingly, hairline rules, no shadows, no
rounded shapes. Real doctrine fonts (Inter Tight, Source Serif 4, JetBrains
Mono) are bundled alongside this module in fonts/ and registered with matplotlib
directly -- not a generic sans-serif standing in for them.

Each function takes plain Python data (lists/dicts) and a Path, writes a PNG,
and returns the path. No function reads a CSV itself -- callers pass parsed
data so this module stays independently testable.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import networkx as nx

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


def _font(name: str) -> fm.FontProperties:
    return fm.FontProperties(fname=str(_FONTS_DIR / name))


F_DISPLAY = _font("InterTight-Regular.ttf")
F_SERIF_ITALIC = _font("SourceSerif4-Italic.ttf")
F_MONO = _font("JetBrainsMono-Regular.ttf")
F_MONO_MEDIUM = _font("JetBrainsMono-Medium.ttf")

# --- Doctrine tokens (section 3.1 / 7) -- do not add colors outside this set ---
INK = "#0A0A0A"
INK_2 = "#1A1A1A"
MUTED = "#5C6066"
MUTED_2 = "#8A8F96"
RULE = "#E5E5E5"
RULE_2 = "#F0F0F0"
PAPER = "#FFFFFF"
PAPER_2 = "#FAFAF8"
PAPER_3 = "#F4F4F1"
ACCENT = "#1E6FFF"
ACCENT_SOFT = "#E8F0FF"
WARN = "#C0392B"
OK = "#0A7C53"

# A neutral grayscale ramp for charts that inherently need several series
# (e.g. a 6-category stacked share) without inventing new hues -- doctrine
# principle 2.4: "one accent, used sparingly." Only the single most
# important series in such a chart gets ACCENT; everything else is a step
# on this ramp.
GRAY_RAMP = [INK, "#3A3D42", MUTED, "#9CA0A6", MUTED_2, "#C9CCD1", RULE]


def _new_fig(w=12, h=6.5):
    fig, ax = plt.subplots(figsize=(w, h), dpi=160)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(F_MONO)
    ax.grid(True, color=RULE_2, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def _title(fig, ax, title: str, subtitle: str | None = None):
    fig.text(0.06, 0.94, title, fontsize=16, fontproperties=F_DISPLAY, fontweight="medium", color=INK, ha="left")
    # heavy rule under the title -- doctrine 3.4 "Heavy" token, used to
    # separate a section heading from its content.
    fig.add_artist(plt.Line2D([0.06, 0.985], [0.905, 0.905], transform=fig.transFigure, color=INK, linewidth=1))
    if subtitle:
        fig.text(0.06, 0.875, subtitle, fontsize=9.5, fontproperties=F_MONO, color=MUTED, ha="left")


def _save(fig, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=PAPER, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    return out_path


def dual_axis_trend(x_labels: list[str], series_a: list[float], series_b: list[float],
                     label_a: str, label_b: str, title: str, out_path: Path,
                     subtitle: str | None = None) -> Path:
    """series_a is treated as the neutral/volume series (Ink), series_b as
    the metric of interest for this chart (Accent) -- doctrine reserves the
    one accent for what the chart is actually about, not an arbitrary
    second color."""
    fig, ax1 = _new_fig()
    fig.subplots_adjust(top=0.78, bottom=0.12, left=0.08, right=0.92)
    ax2 = ax1.twinx()
    ax2.set_facecolor("none")
    for spine in ax2.spines.values():
        spine.set_visible(False)
    idx = range(len(x_labels))
    ax1.plot(idx, series_a, color=MUTED, linewidth=1.6, label=label_a)
    ax2.plot(idx, series_b, color=ACCENT, linewidth=2.2, label=label_b)
    ax1.tick_params(axis="y", colors=MUTED)
    ax2.tick_params(axis="y", colors=ACCENT)
    for label in ax2.get_yticklabels():
        label.set_fontproperties(F_MONO)
    ax2.grid(False)
    step = max(1, len(x_labels) // 14)
    ax1.set_xticks(list(idx)[::step])
    ax1.set_xticklabels([x_labels[i] for i in idx][::step], rotation=0, fontsize=8.5)
    lines = ax1.get_lines() + ax2.get_lines()
    leg = fig.legend(lines, [ln.get_label() for ln in lines], loc="upper left",
                      bbox_to_anchor=(0.06, 0.865), frameon=False, ncol=2,
                      prop=F_MONO, fontsize=9)
    for text, color in zip(leg.get_texts(), [MUTED, ACCENT], strict=True):
        text.set_color(color)
    _title(fig, ax1, title, subtitle)
    return _save(fig, out_path)


def single_line_trend(x_labels: list[str], values: list[float], title: str, out_path: Path,
                       subtitle: str | None = None, ylabel: str | None = None,
                       annotation: str | None = None, semantic: str = "accent") -> Path:
    """semantic: "accent" (neutral focus metric), "warn" (a rising-is-bad
    metric), or "ok" (a rising-is-good metric) -- picks from the doctrine's
    semantic tokens rather than an arbitrary color."""
    color = {"accent": ACCENT, "warn": WARN, "ok": OK}.get(semantic, ACCENT)
    fig, ax = _new_fig()
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.07, right=0.96)
    idx = range(len(x_labels))
    ax.plot(idx, values, color=color, linewidth=2.2)
    ax.fill_between(idx, values, 0, color=color, alpha=0.06)
    step = max(1, len(x_labels) // 14)
    ax.set_xticks(list(idx)[::step])
    ax.set_xticklabels([x_labels[i] for i in idx][::step], fontsize=8.5)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9.5, fontproperties=F_MONO)
    if annotation:
        ax.text(0.02, 0.92, annotation, transform=ax.transAxes, fontsize=11,
                color=color, fontproperties=F_DISPLAY, fontweight="medium", va="top")
    _title(fig, ax, title, subtitle)
    return _save(fig, out_path)


def stacked_share_bar(period_labels: list[str], category_series: dict[str, list[float]],
                       title: str, out_path: Path, subtitle: str | None = None,
                       highlight: str | None = None) -> Path:
    """One category (`highlight`, defaulting to the largest) is drawn in
    Accent; every other category steps down a neutral gray ramp. This is
    the doctrine-compliant way to render an inherently multi-category
    chart without inventing new hues."""
    fig, ax = _new_fig()
    fig.subplots_adjust(top=0.80, bottom=0.16, left=0.07, right=0.98)
    cats = list(category_series.keys())
    if highlight is None:
        highlight = max(cats, key=lambda c: sum(category_series[c]))
    others = [c for c in cats if c != highlight]
    color_for = {highlight: ACCENT}
    for i, c in enumerate(others):
        color_for[c] = GRAY_RAMP[min(i, len(GRAY_RAMP) - 1)]

    idx = range(len(period_labels))
    draw_order = others + [highlight]  # highlight drawn last so it's visually on top
    bottom_by_cat = {}
    running = [0.0] * len(period_labels)
    for cat in cats:
        bottom_by_cat[cat] = list(running)
        running = [r + v for r, v in zip(running, category_series[cat], strict=True)]
    for cat in draw_order:
        ax.bar(idx, category_series[cat], bottom=bottom_by_cat[cat], color=color_for[cat],
               width=0.85, label=cat)
    step = max(1, len(period_labels) // 16)
    ax.set_xticks(list(idx)[::step])
    ax.set_xticklabels([period_labels[i] for i in idx][::step], rotation=45, ha="right", fontsize=8)
    ax.set_ylim(0, 1.0)
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=len(cats),
                     frameon=False, prop=F_MONO, fontsize=8)
    for text in leg.get_texts():
        text.set_color(ACCENT if text.get_text() == highlight else MUTED)
    _title(fig, ax, title, subtitle)
    return _save(fig, out_path)


def lorenz_curve(sorted_shares_cumulative: list[float], title: str, out_path: Path,
                  gini: float, n_entities: int, entity_label: str = "engineers",
                  subtitle: str | None = None) -> Path:
    fig, ax = _new_fig(w=9, h=8)
    fig.subplots_adjust(top=0.82, bottom=0.10, left=0.10, right=0.96)
    n = len(sorted_shares_cumulative)
    xs = [i / n for i in range(n + 1)]
    ys = [0.0] + sorted_shares_cumulative
    ax.plot([0, 1], [0, 1], "--", color=MUTED_2, linewidth=1.1)
    ax.text(0.55, 0.5, "line of equality", color=MUTED_2, fontsize=8.5, rotation=38,
            fontproperties=F_MONO, transform=ax.transData)
    ax.plot(xs, ys, color=ACCENT, linewidth=2.3)
    ax.fill_between(xs, ys, 0, color=ACCENT_SOFT)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel(f"cumulative share of {entity_label} (least -> most active)",
                  color=MUTED, fontsize=9, fontproperties=F_MONO)
    ax.set_ylabel("cumulative share of commits", color=MUTED, fontsize=9, fontproperties=F_MONO)

    def pct_at(cum_frac: float) -> float:
        i = min(n, max(0, round(cum_frac * n)))
        return ys[i]

    top10 = 1 - pct_at(0.9)
    top20 = 1 - pct_at(0.8)
    bottom50 = pct_at(0.5)
    callout = (f"Top 10% of {entity_label} -> {top10*100:.0f}% of commits\n"
               f"Top 20% -> {top20*100:.0f}%   Bottom 50% -> {bottom50*100:.0f}%")
    ax.text(0.06, 0.94, callout, transform=ax.transAxes, fontsize=10.5, color=INK,
            fontproperties=F_DISPLAY, va="top", linespacing=1.7)
    sub = subtitle or f"{n_entities} {entity_label} | Gini = {gini:.3f}"
    _title(fig, ax, title, sub)
    return _save(fig, out_path)


def horizontal_bar_ranked(labels: list[str], values: list[float], title: str, out_path: Path,
                           subtitle: str | None = None, value_fmt: str = "{:.0f}") -> Path:
    fig, ax = _new_fig(w=11, h=max(4, 0.5 * len(labels) + 2))
    fig.subplots_adjust(top=0.85, bottom=0.08, left=0.32, right=0.94)
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels_o = [labels[i] for i in order]
    values_o = [values[i] for i in order]
    ax.barh(range(len(labels_o)), values_o, color=INK, height=0.55)
    ax.set_yticks(range(len(labels_o)))
    for i, lab in enumerate(labels_o):
        ax.text(-0.01, i, lab, ha="right", va="center", fontsize=9, color=INK_2,
                fontproperties=F_MONO, transform=ax.get_yaxis_transform())
    ax.set_yticklabels([])
    for i, v in enumerate(values_o):
        ax.text(v, i, f"  {value_fmt.format(v)}", va="center", fontsize=9, color=ACCENT, fontproperties=F_MONO)
    ax.grid(axis="y", visible=False)
    _title(fig, ax, title, subtitle)
    return _save(fig, out_path)


def scatter_plot(x: list[float], y: list[float], labels: list[str], title: str, out_path: Path,
                  xlabel: str, ylabel: str, subtitle: str | None = None,
                  annotate_top_n: int = 5) -> Path:
    fig, ax = _new_fig()
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.08, right=0.96)
    ax.scatter(x, y, color=MUTED_2, alpha=0.6, s=26, edgecolors="none")
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9.5, fontproperties=F_MONO)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9.5, fontproperties=F_MONO)
    scored = sorted(range(len(x)), key=lambda i: -(x[i] * y[i]))[:annotate_top_n]
    xs_top = [x[i] for i in scored]
    ys_top = [y[i] for i in scored]
    ax.scatter(xs_top, ys_top, color=ACCENT, alpha=0.9, s=40, edgecolors="none", zorder=3)
    for i in scored:
        ax.annotate(labels[i], (x[i], y[i]), fontsize=8, color=INK, fontproperties=F_MONO,
                    xytext=(6, 6), textcoords="offset points")
    _title(fig, ax, title, subtitle)
    return _save(fig, out_path)


def network_clusters(nodes: list[str], edges: list[tuple[str, str]], title: str, out_path: Path,
                      node_size: dict[str, float] | None = None,
                      node_color: dict[str, str] | None = None,
                      subtitle: str | None = None) -> Path:
    fig, ax = _new_fig(w=12, h=10)
    fig.subplots_adjust(top=0.90, bottom=0.02, left=0.02, right=0.98)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from([e for e in edges if e[0] in nodes and e[1] in nodes])
    pos = nx.spring_layout(G, seed=42, k=1.4 / max(1, len(nodes) ** 0.5))
    colors = [node_color.get(n, INK) if node_color else INK for n in G.nodes()]
    sizes = [max(30, (node_size.get(n, 1) if node_size else 1) * 40) for n in G.nodes()]
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=RULE, width=0.9)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, node_size=sizes, linewidths=0)
    labels = {n: n for n in G.nodes() if (node_size.get(n, 0) if node_size else 0) > (
        sorted(node_size.values())[-min(12, len(node_size))] if node_size and len(node_size) > 12 else 0)}
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=8, font_color=INK, font_family="monospace")
    _title(fig, ax, title, subtitle)
    return _save(fig, out_path)
