import csv, textwrap
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'axes.edgecolor': '#c3c2b7',
    'axes.labelcolor': '#52514e',
    'text.color': '#0b0b0b',
    'xtick.color': '#52514e',
    'ytick.color': '#52514e',
    'axes.grid': True,
    'grid.color': '#e8e7e2',
    'grid.linewidth': 0.6,
    'figure.facecolor': '#fcfcfb',
    'axes.facecolor': '#fcfcfb',
    'savefig.facecolor': '#fcfcfb',
})

BLUE, ORANGE, AQUA, YELLOW = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
TEXT_PRIMARY, TEXT_SECONDARY = '#0b0b0b', '#52514e'

SRC = '/home/valentin/code/active/nexus/experiments/article/minesoft_spain_2000_2025_classification/screening_table_consolidated.csv'
OUT = '/home/valentin/code/active/nexus/experiments/article/figures'

with open(SRC) as f:
    rows = list(csv.DictReader(f))

COMPOUNDS = ['Brentuximab_vedotin','Cytarabine','Trabectedin','Vidarabine','Ziconotide',
             'Plitidepsin','Omega3_acid_ethyl_esters','Polatuzumab_vedotin',
             'Omega3_carboxylic_acid','Enfortumab_vedotin','Eribulin_mesylate','Lurbinectedin']
LABELS = {'Omega3_acid_ethyl_esters':'Omega-3 acid\nethyl esters','Omega3_carboxylic_acid':'Omega-3\ncarboxylic acid'}
def lbl(c):
    return LABELS.get(c, c.replace('_',' '))

# ---------- Figure A: overall classification composition (methodology validation) ----------
rc = Counter(r['Relevance_Class'] for r in rows)
cats = ['Directly Relevant','Indirectly Relevant','Incidental Mention','Uncertain']
colors = [BLUE, ORANGE, AQUA, YELLOW]
vals = [rc[c] for c in cats]
total = sum(vals)

fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=200)
left = 0
for cat, val, col in zip(cats, vals, colors):
    ax.barh(0, val, left=left, height=0.5, color=col, edgecolor='#fcfcfb', linewidth=2)
    pct = val/total*100
    if val >= 40:
        label_color = 'white' if col in (BLUE, ORANGE) else TEXT_PRIMARY
        ax.text(left+val/2, 0, f"{val} ({pct:.0f}%)", ha='center', va='center',
                 fontsize=9, color=label_color, fontweight='bold')
    else:
        # small segment: label outside the bar with a leader line, avoids overflow/collision
        ax.text(left+val/2, 0.42, f"{val} ({pct:.0f}%)", ha='center', va='bottom',
                 fontsize=8.5, color=TEXT_PRIMARY)
        ax.plot([left+val/2, left+val/2], [0.25, 0.38], color='#c3c2b7', linewidth=0.8)
    left += val
ax.set_xlim(0, total)
ax.set_ylim(-0.5, 0.75)
ax.set_yticks([])
ax.set_xlabel(f'Spain-relevant patent families, 2000–2025 (n = {total})', fontsize=9.5)
ax.spines[['top','right','left']].set_visible(False)
ax.grid(False)
handles = [plt.Rectangle((0,0),1,1, color=c) for c in colors]
ax.legend(handles, cats, loc='upper center', bbox_to_anchor=(0.5, 1.62), ncol=4,
           frameon=False, fontsize=9)
ax.set_title('Figure 7 – Relevance classification of Spain-relevant\nmarine-derived-drug patent families',
             fontsize=11, pad=52, color=TEXT_PRIMARY, loc='left')
fig.tight_layout()
fig.savefig(f'{OUT}/figure7_classification_composition.png', bbox_inches='tight')
plt.close(fig)

# ---------- Figure B: relevant families per compound (Direct + Indirect, stacked) ----------
per_compound = {c: Counter() for c in COMPOUNDS}
for r in rows:
    for c in r['Compound'].split('; '):
        if c in per_compound:
            per_compound[c][r['Relevance_Class']] += 1

totals = {c: per_compound[c]['Directly Relevant'] + per_compound[c]['Indirectly Relevant'] for c in COMPOUNDS}
ordered = sorted(COMPOUNDS, key=lambda c: totals[c], reverse=True)

fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
y = range(len(ordered))
direct = [per_compound[c]['Directly Relevant'] for c in ordered]
indirect = [per_compound[c]['Indirectly Relevant'] for c in ordered]
ax.barh(list(y), direct, height=0.6, color=BLUE, label='Directly Relevant')
ax.barh(list(y), indirect, height=0.6, left=direct, color=ORANGE, label='Indirectly Relevant')
for i, c in enumerate(ordered):
    t = totals[c]
    if t > 0:
        ax.text(t + max(totals.values())*0.015, i, str(t), va='center', ha='left',
                 fontsize=9, color=TEXT_PRIMARY)
ax.set_yticks(list(y))
ax.set_yticklabels([lbl(c) for c in ordered], fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('Directly + Indirectly Relevant patent families (Spain, 2000–2025)', fontsize=9.5)
ax.spines[['top','right']].set_visible(False)
ax.legend(loc='lower right', frameon=False, fontsize=9)
ax.set_title('Figure 8 – Spain-relevant marine-derived-drug patent\nfamilies per compound (corrected methodology)',
             fontsize=11, color=TEXT_PRIMARY, loc='left')
fig.tight_layout()
fig.savefig(f'{OUT}/figure8_relevant_by_compound.png', bbox_inches='tight')
plt.close(fig)

# ---------- Figure C: application-type profile among the 157 relevant families ----------
rel157 = [r for r in rows if r['Relevance_Class'] in ('Directly Relevant','Indirectly Relevant')]
flags = ['Therapeutic_Application','Combination_Therapy','Formulation','Drug_Delivery',
         'Chemical_Modification','Manufacturing','Diagnostic_Application','Conjugation','Purification_Isolation']
flag_labels = {'Therapeutic_Application':'Therapeutic application','Combination_Therapy':'Combination therapy',
               'Formulation':'Formulation','Drug_Delivery':'Drug delivery',
               'Chemical_Modification':'Chemical modification','Manufacturing':'Manufacturing',
               'Diagnostic_Application':'Diagnostic application','Conjugation':'Conjugation',
               'Purification_Isolation':'Purification / isolation'}
counts = {f_: sum(1 for r in rel157 if r[f_].strip().lower()=='yes') for f_ in flags}
ordered_flags = sorted(flags, key=lambda f_: counts[f_], reverse=True)

fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
y = range(len(ordered_flags))
vals = [counts[f_] for f_ in ordered_flags]
ax.barh(list(y), vals, height=0.6, color=BLUE)
for i, v in enumerate(vals):
    ax.text(v + max(vals)*0.015, i, str(v), va='center', ha='left', fontsize=9, color=TEXT_PRIMARY)
ax.set_yticks(list(y))
ax.set_yticklabels([flag_labels[f_] for f_ in ordered_flags], fontsize=9)
ax.invert_yaxis()
ax.set_xlabel(f'Number of families (of {len(rel157)} Directly/Indirectly Relevant)', fontsize=9.5)
ax.spines[['top','right']].set_visible(False)
ax.set_title('Figure 9 – Application-type profile of Spain-relevant,\nsubstantively relevant patent families',
             fontsize=11, color=TEXT_PRIMARY, loc='left')
fig.tight_layout()
fig.savefig(f'{OUT}/figure9_application_profile.png', bbox_inches='tight')
plt.close(fig)

# ---------- Table 2 replacement (CSV + printed) ----------
with open(f'{OUT}/table2_relevant_by_compound.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Compound','Directly Relevant','Indirectly Relevant','Total Relevant','Incidental Mention','Uncertain'])
    for c in ordered:
        ctr = per_compound[c]
        w.writerow([c.replace('_',' '), ctr['Directly Relevant'], ctr['Indirectly Relevant'],
                    totals[c], ctr['Incidental Mention'], ctr['Uncertain']])

print("done")
print("Total relevant (Direct+Indirect):", sum(totals.values()), "-- note: sums to 161 not 157 (4 families shared across compounds, counted once per compound)")
