"""Reproducible relevance-rate analysis: recomputes the frozen classification
(screening_table_consolidated.csv, tag paper-data-milestone-2026-09-22) by
rate instead of absolute count, with Wilson 95% confidence intervals.
Produces figure10_relevance_rate_by_compound.png and
relevance_rate_by_compound.csv. No new data is read or acquired.
"""
import csv, math
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': '#52514e',
    'text.color': '#0b0b0b', 'xtick.color': '#52514e', 'ytick.color': '#52514e',
    'axes.grid': True, 'grid.color': '#e8e7e2', 'grid.linewidth': 0.6,
    'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.facecolor': '#fcfcfb',
})
BLUE, ORANGE = '#2a78d6', '#eb6834'
TEXT_PRIMARY, TEXT_SECONDARY = '#0b0b0b', '#52514e'

SRC = '../minesoft_spain_2000_2025_classification/screening_table_consolidated.csv'

COMPOUNDS = ['Brentuximab_vedotin', 'Cytarabine', 'Trabectedin', 'Vidarabine', 'Ziconotide',
             'Plitidepsin', 'Omega3_acid_ethyl_esters', 'Polatuzumab_vedotin',
             'Omega3_carboxylic_acid', 'Enfortumab_vedotin', 'Eribulin_mesylate', 'Lurbinectedin']
LABELS = {'Omega3_acid_ethyl_esters': 'Omega-3 acid ethyl esters',
          'Omega3_carboxylic_acid': 'Omega-3 carboxylic acid'}


def lbl(c):
    return LABELS.get(c, c.replace('_', ' '))


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * n)) / n) / denom
    return (max(0, center - half) * 100, min(1, center + half) * 100)


def main():
    with open(SRC) as f:
        rows = list(csv.DictReader(f))

    screened = {c: Counter() for c in COMPOUNDS}
    for r in rows:
        for c in r['Compound'].split('; '):
            if c in screened:
                screened[c][r['Relevance_Class']] += 1

    data = []
    for c in COMPOUNDS:
        ctr = screened[c]
        n = sum(ctr.values())
        k = ctr['Directly Relevant'] + ctr['Indirectly Relevant']
        rate = k / n * 100 if n else 0
        lo, hi = wilson_ci(k, n)
        data.append((c, n, k, rate, lo, hi))
    data.sort(key=lambda x: -x[3])

    with open('relevance_rate_by_compound.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Compound', 'Screened', 'Relevant', 'Rate_pct', 'Wilson_CI_low_pct', 'Wilson_CI_high_pct'])
        for c, n, k, rate, lo, hi in data:
            w.writerow([c.replace('_', ' '), n, k, round(rate, 1), round(lo, 1), round(hi, 1)])

    fig, ax = plt.subplots(figsize=(8, 5.2), dpi=200)
    y = list(range(len(data)))
    rates = [d[3] for d in data]
    los = [d[3] - d[4] for d in data]
    his = [d[5] - d[3] for d in data]
    colors = [BLUE if d[1] >= 30 else ORANGE for d in data]

    ax.barh(y, rates, height=0.5, color=colors)
    ax.errorbar(rates, y, xerr=[los, his], fmt='none', ecolor='#52514e', elinewidth=1.2, capsize=3)
    for i, (c, n, k, rate, lo, hi) in enumerate(data):
        ax.text(hi + 2, i, f"n={n}", va='center', ha='left', fontsize=8.5, color=TEXT_SECONDARY)

    ax.set_yticks(y)
    ax.set_yticklabels([lbl(d[0]) for d in data], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel('Relevance rate = (Directly + Indirectly Relevant) / screened Spain-relevant families, with 95% Wilson CI', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    ax.legend(handles, ['n ≥ 30 (precise estimate)', 'n < 30 (imprecise — insufficient to support a comparative rate claim)'],
              loc='lower right', frameon=False, fontsize=8.5)
    ax.set_title('Relevance rate per compound is not the same question as\nabsolute relevant-family count — most high-rate compounds have n too small for a comparative claim',
                 fontsize=10.5, color=TEXT_PRIMARY, loc='left')
    fig.tight_layout()
    fig.savefig('figure10_relevance_rate_by_compound.png', bbox_inches='tight')
    plt.close(fig)

    for c, n, k, rate, lo, hi in data:
        print(f"{c:26} n={n:4} k={k:4} rate={rate:5.1f}% CI=[{lo:5.1f},{hi:5.1f}]")


if __name__ == '__main__':
    main()
