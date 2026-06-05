"""
Export a clean data.json for the interactive AIC-vs-GDP web tool.

Reuses the pivot logic from make_plots.py (load_data) to produce one record
per economy with per-capita and total GDP/AIC, AIC share of GDP, and region.
Also bakes in the world-average share from the brief.
"""

import json
import pandas as pd
import country_converter as coco

DATA_FILE = "P_Data_Extract_From_ICP_2021.xlsx"

REGIONS = {"Asia", "Europe", "Africa", "America", "Oceania"}

# Non-standard ISO3 codes in this dataset -> standard codes for region lookup.
ISO3_FIXUPS = {"RUT": "RUS"}  # Russian Federation


def load_data(path=DATA_FILE):
    df = pd.read_excel(path, sheet_name="Data").rename(columns={"2021 [YR2021]": "v"})
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["agg"] = df["Series Code"].map({9020000: "AIC", 1000000: "GDP"})
    df["unit"] = df["Classification Code"].map({"PCAP.PP": "pc", "PP.CD": "tot"})

    w = df.pivot_table(index=["Country Name", "Country Code"],
                       columns=["agg", "unit"], values="v", aggfunc="first")
    w.columns = [f"{a}_{u}" for a, u in w.columns]
    w = w.reset_index()

    world = w[w["Country Name"].str.contains("WORLD", na=False)]
    world_share = float((world["AIC_pc"] / world["GDP_pc"]).iloc[0] * 100)

    c = w[~w["Country Name"].str.contains(r"\(Benchmark\)", na=False)].copy()
    c = c.dropna(subset=["AIC_pc", "GDP_pc", "GDP_tot"])
    c["share"] = 100 * c["AIC_pc"] / c["GDP_pc"]

    cc = coco.CountryConverter()
    codes = [ISO3_FIXUPS.get(code, code) for code in c["Country Code"].tolist()]
    c["region"] = cc.convert(names=codes, src="ISO3", to="continent", not_found="Other")
    return c, world_share


def main():
    c, world_share = load_data()
    records = []
    for _, r in c.iterrows():
        region = r["region"] if r["region"] in REGIONS else "Other"
        records.append({
            "name": r["Country Name"],
            "iso3": r["Country Code"],
            "region": region,
            "gdp_pc": round(float(r["GDP_pc"]), 1),
            "aic_pc": round(float(r["AIC_pc"]), 1),
            "gdp_tot": round(float(r["GDP_tot"]), 2),
            "aic_tot": round(float(r["AIC_tot"]), 2),
            "share": round(float(r["share"]), 2),
        })

    records.sort(key=lambda x: x["name"])
    out = {
        "world_share": round(world_share, 2),
        "source": "World Bank, International Comparison Program (ICP) 2021 cycle (released May 2024). Reference year 2021, PPP terms.",
        "countries": records,
    }
    with open("data.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote data.json | {len(records)} economies | world share {world_share:.2f}%")


if __name__ == "__main__":
    main()
