#!/usr/bin/env python3
"""Generate the skills pipeline diagram."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── Settings ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis('off')
fig.patch.set_facecolor('#FAFAFA')

# ── Colour palette ────────────────────────────────────────
PHASE_COLORS = {
    1: ('#FFF3E0', '#FF9800'),  # orange – Idea & Init
    2: ('#E3F2FD', '#1976D2'),  # blue   – Literature
    3: ('#F3E5F5', '#7B1FA2'),  # purple – Idea Refine
    4: ('#FFF8E1', '#F9A825'),  # amber  – Writing
    5: ('#E8F5E9', '#388E3C'),  # green  – Finalize
    6: ('#FFEBEE', '#C62828'),  # red    – Revision
    'tool': ('#F5F5F5', '#757575'),  # grey – Cross-cutting
}

# ── Helper: rounded box ──────────────────────────────────
def skill_box(ax, cx, cy, label, phase, w=1.5, h=0.52):
    bg, border = PHASE_COLORS[phase]
    box = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.08", linewidth=1.3,
        edgecolor=border, facecolor=bg, zorder=3,
    )
    ax.add_patch(box)
    ax.text(cx, cy, label, ha='center', va='center',
            fontsize=8.5, fontfamily='sans-serif', fontweight='bold',
            color='#333333', zorder=4)

def phase_header(ax, cx, cy, label, phase, w=1.8):
    _, border = PHASE_COLORS[phase]
    ax.text(cx, cy, label, ha='center', va='center',
            fontsize=9, fontfamily='sans-serif', fontweight='bold',
            color=border, zorder=4)

def arrow(ax, x1, y1, x2, y2, color='#BDBDBD', style='->', lw=1.2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=2)

def dashed_arrow(ax, x1, y1, x2, y2, color='#BDBDBD'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.0,
                                linestyle='dashed'),
                zorder=2)

# ── Phase column positions (x-centers) ───────────────────
PX = {1: 1.5, 2: 4.0, 3: 6.5, 4: 9.2, 5: 12.2, 6: 14.5}

# ── Phase 1: Idea & Init ─────────────────────────────────
phase_header(ax, PX[1], 8.2, 'Phase 1: Idea & Init', 1)
skill_box(ax, PX[1], 7.3, '/idea-mine', 1)
skill_box(ax, PX[1], 6.3, '/paper-init', 1)
# PDF input annotation
ax.text(PX[1], 7.95, 'PDF corpus', ha='center', va='center',
        fontsize=7, color='#999999', style='italic')
dashed_arrow(ax, PX[1], 7.04, PX[1], 6.56)

# ── Phase 2: Literature ──────────────────────────────────
phase_header(ax, PX[2], 8.2, 'Phase 2: Literature', 2)
lit_skills = ['/lit-plan', '/lit-review', '/lit-tag', '/lit-pool']
lit_y = [7.3, 6.6, 5.9, 5.2]
for s, y in zip(lit_skills, lit_y):
    skill_box(ax, PX[2], y, s, 2)
for i in range(len(lit_y) - 1):
    arrow(ax, PX[2], lit_y[i] - 0.26, PX[2], lit_y[i+1] + 0.26,
          color=PHASE_COLORS[2][1])
# WoS annotation
ax.text(PX[2] + 1.05, 6.95, 'WoS search', ha='left', va='center',
        fontsize=7, color='#999999', style='italic')

# ── Phase 3: Idea Refine ─────────────────────────────────
phase_header(ax, PX[3], 8.2, 'Phase 3: Idea Refine', 3)
skill_box(ax, PX[3], 7.3, '/idea-refine', 3, w=1.6)
# loop arrow (iterate)
ax.annotate('', xy=(PX[3] - 0.8, 7.55), xytext=(PX[3] + 0.8, 7.55),
            arrowprops=dict(arrowstyle='->', color=PHASE_COLORS[3][1],
                            lw=1.0, connectionstyle='arc3,rad=-0.5'),
            zorder=2)
ax.text(PX[3], 7.85, 'iterate until satisfied', ha='center', va='center',
        fontsize=7, color='#7B1FA2', style='italic')
# idea-reviewer agent annotation
ax.text(PX[3], 6.7, 'idea-reviewer\nagent', ha='center', va='center',
        fontsize=7, color='#9E9E9E', style='italic')
dashed_arrow(ax, PX[3], 6.9, PX[3], 7.04, color='#BDBDBD')

# ── Phase 4: Writing ─────────────────────────────────────
phase_header(ax, PX[4], 8.2, 'Phase 4: Writing', 4)
# Technical track (left sub-column)
tx = PX[4] - 0.9
# Narrative track (right sub-column)
nx = PX[4] + 0.9

# method-audit & method-end (technical)
skill_box(ax, tx, 7.3, '/method-audit', 4, w=1.45)
skill_box(ax, tx, 6.5, '/method-end', 4, w=1.45)
arrow(ax, tx, 7.04, tx, 6.76, color=PHASE_COLORS[4][1])

# pen-outline (narrative)
skill_box(ax, nx, 7.3, '/pen-outline', 4, w=1.45)

# Both merge into pen-draft
skill_box(ax, PX[4], 5.6, '/pen-draft', 4)
arrow(ax, tx, 6.24, PX[4] - 0.3, 5.86, color=PHASE_COLORS[4][1])
arrow(ax, nx, 7.04, PX[4] + 0.3, 5.86, color=PHASE_COLORS[4][1])

# pen-polish
skill_box(ax, PX[4], 4.8, '/pen-polish', 4)
arrow(ax, PX[4], 5.34, PX[4], 5.06, color=PHASE_COLORS[4][1])

# Track labels
ax.text(tx, 7.75, 'Technical', ha='center', va='center',
        fontsize=7, color='#999999')
ax.text(nx, 7.75, 'Narrative', ha='center', va='center',
        fontsize=7, color='#999999')

# Sub-agents annotation
ax.text(PX[4], 5.2, 'journal-scout + sci-writer agents',
        ha='center', va='center', fontsize=6.5, color='#9E9E9E', style='italic')

# ── Phase 5: Finalize ────────────────────────────────────
phase_header(ax, PX[5], 8.2, 'Phase 5: Finalize', 5)
skill_box(ax, PX[5], 7.3, '/finalize', 5)
skill_box(ax, PX[5], 6.4, '/pre-submit', 5)
arrow(ax, PX[5], 7.04, PX[5], 6.66, color=PHASE_COLORS[5][1])
ax.text(PX[5], 6.87, 'Conc → Abs → CL → Cleanup',
        ha='center', va='center', fontsize=6.5, color='#999999', style='italic')

# ── Phase 6: Revision ────────────────────────────────────
phase_header(ax, PX[6], 8.2, 'Phase 6: Revision', 6)
skill_box(ax, PX[6], 7.3, '/rev-init', 6)
skill_box(ax, PX[6], 6.4, '/rev-respond', 6)
arrow(ax, PX[6], 7.04, PX[6], 6.66, color=PHASE_COLORS[6][1])
ax.text(PX[6], 5.9, 'Multi-round R1/R2/R3...',
        ha='center', va='center', fontsize=6.5, color='#999999', style='italic')

# ── Cross-phase arrows (between phases) ──────────────────
# Phase 1 → Phase 2
arrow(ax, PX[1] + 0.75, 6.3, PX[2] - 0.75, 6.3, color='#BDBDBD')
# Phase 2 → Phase 3
arrow(ax, PX[2] + 0.75, 6.3, PX[3] - 0.8, 7.1, color='#BDBDBD')
# Phase 3 → Phase 4
arrow(ax, PX[3] + 0.8, 7.3, PX[4] - 1.63, 7.3, color='#BDBDBD')
# Phase 4 → Phase 5
arrow(ax, PX[4] + 0.75, 4.8, PX[5] - 0.75, 6.4, color='#BDBDBD')
# Phase 5 → Phase 6
arrow(ax, PX[5] + 0.75, 6.4, PX[6] - 0.75, 6.4, color='#BDBDBD')

# ── Cross-cutting Utilities bar ──────────────────────────
bar_y = 3.2
bar = FancyBboxPatch(
    (0.5, bar_y - 0.65), 15, 1.3,
    boxstyle="round,pad=0.12", linewidth=1.0,
    edgecolor='#BDBDBD', facecolor='#FAFAFA', linestyle='--', zorder=1,
)
ax.add_patch(bar)
ax.text(8, bar_y + 0.45, 'Cross-cutting Utilities',
        ha='center', va='center', fontsize=9, fontweight='bold',
        color='#757575')

tools = ['/resume', '/figure', '/latex-table', '/web-access', '/peer-review']
tool_x = [2.0, 5.0, 8.0, 11.0, 14.0]
for t, x in zip(tools, tool_x):
    skill_box(ax, x, bar_y - 0.15, t, 'tool', w=1.6)

# ── Subtitle ─────────────────────────────────────────────
ax.text(8, 0.95, 'Academic Writing Skills Pipeline',
        ha='center', va='center', fontsize=11, fontweight='bold',
        color='#555555')
ax.text(8, 0.55, 'Each skill is invoked via /command in Claude Code  ·  No skipping forward, backtracking always allowed',
        ha='center', va='center', fontsize=7.5, color='#999999')

plt.tight_layout(pad=0.5)
plt.savefig('/Users/zylen/.claude/assets/skills_pipeline.png', dpi=200,
            bbox_inches='tight', facecolor='#FAFAFA')
plt.close()
print('Done – saved to assets/skills_pipeline.png')
