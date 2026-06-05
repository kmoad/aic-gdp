"""
AIC-vs-GDP "welfare vs. national power" scatter plots from ICP 2021 data.

Reproduces three plots from P_Data_Extract_From_ICP_2021.xlsx:
  1. AIC_share_vs_GDP_per_capita.png   - all economies, log x-axis
  2. AIC_share_vs_GDP_over10k_linear.png - GDP/capita > $10k, linear x-axis
  3. AIC_share_vs_GDP_over5k_linear.png  - GDP/capita > $5k,  linear x-axis

Derived variable: AIC as % of GDP = AIC per capita / GDP per capita.
  High  = more of the economy flows to citizens' actual consumption.
  Low   = output directed to investment, collective government, net exports.
Bubble area is proportional to total GDP (PPP); colour is continent.

Requires: pandas, numpy, matplotlib, country_converter, adjustText
    pip install pandas numpy matplotlib country_converter adjustText
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import country_converter as coco
from adjustText import adjust_text

DATA_FILE = "P_Data_Extract_From_ICP_2021.xlsx"

PALETTE = {"Asia": "#E4572E", "Europe": "#2E86AB", "Africa": "#8A6FB0",
           "America": "#1B998B", "Oceania": "#D4A017", "Other": "#999999"}


def load_data(path=DATA_FILE):
    """Pivot the long ICP extract to one row per economy with GDP/AIC,
    per-capita and total, plus AIC share of GDP and continent."""
    df = pd.read_excel(path, sheet_name="Data").rename(columns={"2021 [YR2021]": "v"})
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["agg"] = df["Series Code"].map({9020000: "AIC", 1000000: "GDP"})
    df["unit"] = df["Classification Code"].map({"PCAP.PP": "pc", "PP.CD": "tot"})

    w = df.pivot_table(index=["Country Name", "Country Code"],
                       columns=["agg", "unit"], values="v", aggfunc="first")
    w.columns = [f"{a}_{u}" for a, u in w.columns]
    w = w.reset_index()

    # world reference share (from the WORLD aggregate row, before dropping aggregates)
    world = w[w["Country Name"].str.contains("WORLD", na=False)]
    world_share = float((world["AIC_pc"] / world["GDP_pc"]).iloc[0] * 100)

    # countries only
    c = w[~w["Country Name"].str.contains(r"\(Benchmark\)", na=False)].copy()
    c = c.dropna(subset=["AIC_pc", "GDP_pc", "GDP_tot"])
    c["share"] = 100 * c["AIC_pc"] / c["GDP_pc"]

    cc = coco.CountryConverter()
    c["cont"] = cc.convert(names=c["Country Code"].tolist(), src="ISO3",
                           to="continent", not_found="Other")
    c["color"] = c["cont"].map(PALETTE).fillna("#999999")
    return c, world_share


def clean_name(name):
    for a, b in [(" Darussalam", ""), (", Rep.", ""), (", Arab Rep.", ""),
                 (", Islamic Rep.", ""), ("United Arab Emirates", "UAE"),
                 ("United States", "USA"), ("United Kingdom", "UK"),
                 ("Russian Federation", "Russia")]:
        name = name.replace(a, b)
    return name


def make_plot(c, world_share, cfg):
    """Render one scatter according to a config dict."""
    d = c.copy()
    if cfg["min_gdp_pc"]:
        d = d[d["GDP_pc"] > cfg["min_gdp_pc"]]

    fig, ax = plt.subplots(figsize=(14.5, 9.2), dpi=150)
    if cfg["logx"]:
        ax.set_xscale("log")

    ax.scatter(d["GDP_pc"], d["share"], s=14 * np.sqrt(d["GDP_tot"]),
               c=d["color"], alpha=0.62, edgecolors="white", linewidths=0.6, zorder=3)

    # reference lines
    tx = cfg["line_text_x"]
    ax.axhline(world_share, color="#444", ls="--", lw=1.2, zorder=2)
    ax.text(tx, world_share + cfg["world_dy"],
            cfg["world_label"].format(ws=world_share), fontsize=9.5,
            color="#444", style="italic")
    ax.axhline(100, color="#c0392b", ls=":", lw=1.0, alpha=0.7, zorder=2)
    ax.text(tx, cfg["line100_y"], cfg["line100_label"], fontsize=8.3,
            color="#c0392b", alpha=0.85)

    # labels: largest economies + notable cases present in this subset
    keep = set(d.nlargest(cfg["n_big"], "GDP_tot")["Country Name"]).union(cfg["notable"])
    show = d[d["Country Name"].isin(keep)]
    texts = [ax.text(r["GDP_pc"], r["share"], clean_name(r["Country Name"]),
                     fontsize=8.5, zorder=5, color="#222") for _, r in show.iterrows()]
    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="#999", lw=0.5),
                expand_points=(1.4, 1.6), force_text=(0.5, 0.7))

    # axes / titles
    ax.set_xlabel(cfg["xlabel"], fontsize=10.5)
    ax.set_ylabel("Actual Individual Consumption as % of GDP\n"
                  "\u2191 more of the economy flows to citizens' consumption", fontsize=10.5)
    ax.set_title(cfg["title"], fontsize=15, fontweight="bold", pad=14)
    ax.text(0.5, 1.012, cfg["subtitle"], transform=ax.transAxes, ha="center",
            fontsize=9, color="#555")
    ax.set_xlim(*cfg["xlim"])
    ax.set_ylim(*cfg["ylim"])
    ax.grid(True, which="both", alpha=0.18)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # legends
    cont_handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE[k],
                    markersize=9, label=k) for k in ["Asia", "Europe", "Africa", "America", "Oceania"]]
    leg1 = ax.legend(handles=cont_handles, title="Continent", loc="upper right",
                     frameon=True, fontsize=9, title_fontsize=9.5)
    ax.add_artist(leg1)
    size_handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor="#bbb",
                    markeredgecolor="gray", markersize=np.sqrt(14 * np.sqrt(v)) / 2.5,
                    label=f"${v:,}B") for v in [500, 5000, 25000]]
    ax.legend(handles=size_handles, title="Total GDP (PPP)", loc=cfg["size_loc"],
              bbox_to_anchor=cfg.get("size_anchor"), frameon=True, fontsize=8.5,
              title_fontsize=9, labelspacing=1.7, borderpad=1.1)

    plt.tight_layout()
    fig.savefig(cfg["fname"], dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", cfg["fname"], "|", len(d), "economies")


RICH = ["Ireland", "Singapore", "Qatar", "Luxembourg", "Brunei Darussalam", "Norway",
        "United Arab Emirates", "Saudi Arabia", "Switzerland", "Korea, Rep."]

CONFIGS = [
    dict(  # 1. all economies, log scale
        fname="AIC_share_vs_GDP_per_capita.png",
        min_gdp_pc=None, logx=True, xlim=(900, 200000), ylim=(20, 165),
        line_text_x=1080, world_dy=1.4,
        world_label="World average: {ws:.0f}% of GDP to citizen consumption",
        line100_y=101.2,
        line100_label="AIC = GDP  (consumption financed beyond domestic output: aid/remittances)",
        n_big=14, notable=set(RICH + ["Lebanon", "Somalia", "South Africa", "Nigeria",
                                      "Vietnam", "Turkiye", "Turkey"]),
        title="How nations split their economy: citizen welfare vs. everything else",
        subtitle='Bubble area \u221d total GDP (PPP). Low share = output directed to '
                 'investment, collective government, net exports \u2014 the "national-power" bucket.  ICP 2021.',
        xlabel="GDP per capita, PPP (international $, 2021)  \u2014  log scale  "
               "\u2192  more prosperous / greater economic capacity",
        size_loc="upper left"),
    dict(  # 2. > $10k, linear
        fname="AIC_share_vs_GDP_over10k_linear.png",
        min_gdp_pc=10000, logx=False, xlim=(10000, 145000), ylim=(20, 105),
        line_text_x=11500, world_dy=1.1,
        world_label="World average (all economies): {ws:.0f}%",
        line100_y=100.8, line100_label="AIC = GDP (consumption exceeds domestic output)",
        n_big=16, notable=set(RICH + ["Netherlands", "Poland", "Greece", "Portugal",
                                      "Chile", "Malaysia", "Kazakhstan", "Gabon", "Oman",
                                      "Moldova", "Czechia", "Hungary", "Romania"]),
        title="Welfare vs. national power among higher-income economies (GDP/capita > $10k)",
        subtitle="Bubble area \u221d total GDP (PPP). Low share = output directed to "
                 "investment, collective government, net exports.  ICP 2021. Linear scale.",
        xlabel="GDP per capita, PPP (international $, 2021)  "
               "\u2192  more prosperous / greater economic capacity",
        size_loc="lower left"),
    dict(  # 3. > $5k, linear
        fname="AIC_share_vs_GDP_over5k_linear.png",
        min_gdp_pc=5000, logx=False, xlim=(5000, 145000), ylim=(20, 125),
        line_text_x=5600, world_dy=1.1,
        world_label="World average (all economies): {ws:.0f}%",
        line100_y=100.9,
        line100_label="AIC = GDP (consumption exceeds domestic output: aid / remittances)",
        n_big=18, notable=set(RICH + ["Netherlands", "Poland", "Greece", "Portugal",
                                      "Chile", "Malaysia", "Kazakhstan", "Gabon",
                                      "Egypt, Arab Rep.", "India", "Vietnam", "Philippines",
                                      "Iran, Islamic Rep.", "Lebanon", "South Africa",
                                      "Thailand", "Colombia", "Ukraine"]),
        title="Welfare vs. national power among middle- and high-income economies (GDP/capita > $5k)",
        subtitle="Bubble area \u221d total GDP (PPP). Low share = output directed to "
                 "investment, collective government, net exports.  ICP 2021. Linear scale.",
        xlabel="GDP per capita, PPP (international $, 2021)  "
               "\u2192  more prosperous / greater economic capacity",
        size_loc="center right", size_anchor=(0.995, 0.68)),
]


def main():
    c, world_share = load_data()
    print(f"loaded {len(c)} economies | world AIC share = {world_share:.2f}%")
    for cfg in CONFIGS:
        make_plot(c, world_share, cfg)


if __name__ == "__main__":
    main()
