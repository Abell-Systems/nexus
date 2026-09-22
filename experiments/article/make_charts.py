import collections
import os
import openpyxl
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pycountry

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "patentes_CEIMAR_master.xlsx")
OUT = os.path.join(HERE, "figures")

BLUE = "#2a78d6"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# infogram-style sequential ramps (5 discrete bins, matching the original figures)
ORANGE_BINS = ["#fdf1ea", "#f8cbb0", "#f2a06f", "#ee7a3b", "#e8590c"]
GREEN_BINS = ["#eef5ee", "#c9e2c9", "#a0cea0", "#77ba77", "#4ea44e"]

def stepped_colorscale(bins):
    """Hard-edged (non-blended) colorscale from N bin colors, infogram style."""
    n = len(bins)
    scale = []
    for i, c in enumerate(bins):
        scale.append([i / n, c])
        scale.append([(i + 1) / n, c])
    scale[0][0] = 0.0
    scale[-1][0] = 1.0
    return scale

YEAR_MIN, YEAR_MAX = 2000, 2026

wb = openpyxl.load_workbook(SRC, read_only=True)
ws = wb["Sheet1"]
rows = list(ws.iter_rows(values_only=True))
header, data_all = rows[0], rows[1:]
idx = {h: i for i, h in enumerate(header)}
data = [r for r in data_all if YEAR_MIN <= int(r[idx["earliest_priority_year"]]) <= YEAR_MAX]
n_families = len(data)

# ---- jurisdiction counts (exclude EP/WO: not countries) ----
juris = collections.Counter()
for r in data:
    for c in (r[idx["jurisdictions"]] or "").split(";"):
        c = c.strip()
        if c and c not in ("EP", "WO"):
            juris[c] += 1

def iso3(code2):
    try:
        return pycountry.countries.get(alpha_2=code2).alpha_3
    except AttributeError:
        return None

rows_iso = []
for code2, count in juris.items():
    c3 = iso3(code2)
    if c3:
        rows_iso.append((code2, c3, count))
df = pd.DataFrame(rows_iso, columns=["iso2", "iso3", "n_patents"])

EUROPE = {
    "AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV",
    "LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE","CH","NO","IS","GB","UA",
    "RS","AL","MK","MD","GE","AM","AZ","BY",
}

# ---- Figure 1: world map (infogram style: orange bins, bottom horizontal legend, no title in image) ----
zmax1 = 400  # matches original figure's 0-400 legend scale
fig = go.Figure(go.Choropleth(
    locations=df["iso3"], z=df["n_patents"], locationmode="ISO-3",
    zmin=0, zmax=zmax1,
    colorscale=stepped_colorscale(ORANGE_BINS),
    marker_line_color="white", marker_line_width=0.6,
    colorbar=dict(
        orientation="h", thickness=16, len=0.9, x=0.5, y=-0.08,
        tickvals=[0, 100, 200, 300, 400], ticks="outside",
        outlinewidth=0, title=None,
    ),
))
fig.add_annotation(text=f"Priority years {YEAR_MIN}–{YEAR_MAX}", x=0.01, y=0.98,
                    xref="paper", yref="paper", showarrow=False,
                    font=dict(size=13, color="#888888"), xanchor="left")
fig.update_layout(
    geo=dict(showframe=False, showcoastlines=False, projection_type="natural earth",
              bgcolor="white", landcolor="#e4e4e2", subunitcolor="white",
              countrycolor="white", showcountries=True),
    paper_bgcolor="white", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=10, b=70),
    font=dict(family="Arial", size=14, color="#333333"),
)
fig.write_image(f"{OUT}/figure1_world_map.png", width=1400, height=850, scale=2)

# ---- Figure 2: Europe map (infogram style: green bins, bold top-left title baked into image) ----
df_eu = df[df["iso2"].isin(EUROPE)]
zmax2 = 250  # matches original figure's 0-250 legend scale
fig2 = go.Figure(go.Choropleth(
    locations=df_eu["iso3"], z=df_eu["n_patents"], locationmode="ISO-3",
    zmin=0, zmax=zmax2,
    colorscale=stepped_colorscale(GREEN_BINS),
    marker_line_color="white", marker_line_width=0.6,
    colorbar=dict(
        orientation="h", thickness=16, len=0.9, x=0.5, y=-0.06,
        tickvals=[0, 50, 100, 150, 200, 250], ticks="outside",
        outlinewidth=0, title=None,
    ),
))
fig2.update_layout(
    title=dict(text=f"<b>Number of patents by European country</b><br>"
                    f"<span style='font-size:13px;color:#888888'>Priority years {YEAR_MIN}–{YEAR_MAX}</span>",
               x=0.03, xanchor="left", y=0.97, yanchor="top",
               font=dict(size=20, color="#333333")),
    geo=dict(scope="europe", showframe=False, showcoastlines=False,
              bgcolor="white", landcolor="#e4e4e2", subunitcolor="white",
              countrycolor="white", showcountries=True),
    paper_bgcolor="white", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=60, b=60),
    font=dict(family="Arial", size=14, color="#333333"),
)
fig2.write_image(f"{OUT}/figure2_europe_map.png", width=1100, height=1000, scale=2)

# ---- Table 5 replacement: top applicant companies (bar chart) ----
apps = collections.Counter()
for r in data:
    for a in (r[idx["applicants"]] or "").split(";"):
        a = a.strip()
        if a:
            apps[a] += 1
top10 = apps.most_common(10)
labels = [t[0].title() for t in top10][::-1]
values = [t[1] for t in top10][::-1]

plt.rcParams["font.family"] = "sans-serif"
INK = "#333333"
MUTED = "#6b6b6b"

def infogram_style(ax, title):
    ax.set_title(title, loc="left", fontsize=20, fontweight="bold", color=INK, pad=22)
    ax.text(0.0, 1.02, f"Priority years {YEAR_MIN}–{YEAR_MAX}",
            transform=ax.transAxes, ha="left", fontsize=13, color="#888888")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors=MUTED, labelsize=11)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)

fig3, ax = plt.subplots(figsize=(11, 6), dpi=200)
ax.barh(labels, values, color=ORANGE_BINS[-1], height=0.62)
for y, v in enumerate(values):
    ax.text(v + 0.15, y, str(v), va="center", fontsize=10, color=MUTED)
ax.set_xlabel("Number of patent families")
infogram_style(ax, "Top 10 applicants by number of patents")
fig3.tight_layout()
fig3.savefig(f"{OUT}/figure5_top_applicants.png")

# ---- Legal status breakdown (supports PSR/status discussion) ----
status = collections.Counter(r[idx["legal_status_summary"]] for r in data)
labels_s = list(status.keys())
values_s = [status[k] for k in labels_s]

fig4, ax4 = plt.subplots(figsize=(8, 6), dpi=200)
ax4.bar(labels_s, values_s, color=GREEN_BINS[-1], width=0.6)
for i, v in enumerate(values_s):
    ax4.text(i, v + 3, str(v), ha="center", fontsize=10, color=MUTED)
ax4.set_ylabel("Number of patent families")
infogram_style(ax4, "Legal status of CEIMAR patent families")
fig4.tight_layout()
fig4.savefig(f"{OUT}/figure6_legal_status.png")

print("done")
print(df.sort_values("n_patents", ascending=False).head(15).to_string(index=False))
