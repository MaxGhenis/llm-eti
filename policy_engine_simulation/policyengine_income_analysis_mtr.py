# %%
import h5py
import pandas as pd
import numpy as np
import os
from policyengine_us import Microsimulation
from huggingface_hub import hf_hub_download

# ── Parameters ─────────────────────────────────────────────────────────────
S           = 1000  # Total sample size across all years
RANDOM_SEED = 42

# Only these two files have the required PolicyEngine-enhanced structure.
# census_cps_2020/2021/2022.h5 exist on HuggingFace but are raw Census files
# that lack household_weight, household_id, and all income variables.
YEARS = {
    2023: "cps_2023.h5",
    2024: "cps_2024.h5",
}

N_PER_YEAR = S // len(YEARS)  # = S/2 for now

# ── Step 1: Download files ─────────────────────────────────────────────────
print("Downloading files")
file_paths = {}
for year, filename in YEARS.items():
    print(f"  {year}: {filename}")
    file_paths[year] = hf_hub_download(
        repo_id="policyengine/policyengine-us-data", filename=filename
    )


# ── Step 2: Process each year ──────────────────────────────────────────────
# For each year:
#   1. Load household IDs and weights from h5
#   2. Use PE's market_income (person-level) for broad income
#   3. Use PE's taxable_income (tax-unit level) aggregated to household for taxable income
#   4. Use PE's marginal_tax_rate (person-level) aggregated to household via max
#   5. Expand rows by round(household_weight / 10), minimum 1
#   6. Draw random sample of N_PER_YEAR rows
 
all_samples = []
 
for year, filename in YEARS.items():
    print(f"\nProcessing {year}...")
    path = file_paths[year]
 
    with h5py.File(path, "r") as f:
        household_id     = f["household_id"][:]
        household_weight = f["household_weight"][:]
        person_hh_id     = f["person_household_id"][:]
        person_tu_id     = f["person_tax_unit_id"][:]
        tax_unit_id      = f["tax_unit_id"][:]
 
    # Instantiate simulation once per year
    baseline = Microsimulation(dataset=path)
 
    # Broad income: PE's market_income is already at the household level
    market_income_person = baseline.calculate("market_income", period=year).values
    broad_hh = (
        pd.DataFrame({"household_id": person_hh_id, "broad_income": market_income_person})
        .groupby("household_id")["broad_income"]
        .sum()
    )
 
    # Taxable income: PE's TI is at the tax unit level — aggregate to household
    # via person-level bridge to avoid double-counting
    tu_to_hh = (
        pd.DataFrame({"tax_unit_id": person_tu_id, "household_id": person_hh_id})
        .drop_duplicates("tax_unit_id")
        .set_index("tax_unit_id")["household_id"]
    )
    taxable_tu = baseline.calculate("taxable_income", period=year).values
    taxable_hh = (
        pd.DataFrame({"tax_unit_id": tax_unit_id, "taxable_income": taxable_tu})
        .assign(household_id=lambda d: d["tax_unit_id"].map(tu_to_hh))
        .groupby("household_id")["taxable_income"]
        .sum()
    )
    
 
    # MTR: PE computes at person level — aggregate to household via max
    mtr_person = baseline.calculate("marginal_tax_rate", period=year).values
    mtr_hh = (
        pd.DataFrame({"household_id": person_hh_id, "mtr": mtr_person})
        .groupby("household_id")["mtr"]
        .max()
    )
 
    # Build household DataFrame
    df = pd.DataFrame({"household_id": household_id, "household_weight": household_weight})
    df["broad_income"]   = df["household_id"].map(broad_hh)
    df["taxable_income"] = df["household_id"].map(taxable_hh)
    df["mtr"]            = df["household_id"].map(mtr_hh)
    df["year"]           = year
    df = df[df["household_weight"] > 0].dropna(subset=["household_weight"])
    df = df[df["broad_income"] > 0]
 
    print(f"  Households: {len(df):,}")
    print(f"  Mean broad income:   ${df['broad_income'].mean():,.2f}")
    print(f"  Mean taxable income: ${df['taxable_income'].mean():,.2f}")
    print(f"  Mean MTR:             {df['mtr'].mean():.3f}")
 
    # Expand rows by round(weight / 10), minimum 1
    df["repeat_count"] = df["household_weight"].apply(lambda w: max(round(w / 10), 1))
    df_expanded = df.loc[df.index.repeat(df["repeat_count"])].drop(columns=["repeat_count"])
    print(f"  Expanded rows: {len(df_expanded):,}")
 
    # Sample N_PER_YEAR rows
    df_year_sample = df_expanded.sample(n=N_PER_YEAR, random_state=RANDOM_SEED).copy()
    print(f"  Sampled: {len(df_year_sample):,}")
 
    all_samples.append(df_year_sample)

# ── Step 3: Combine all years ──────────────────────────────────────────────
df_final = pd.concat(all_samples, ignore_index=True)

# ── Step 4: Generate R' (post-reform rate) ────────────────────────────────
# R' is a small perturbation around R (MTR), representing a hypothetical
# tax reform. Drawn from N(0, 0.025) and added to MTR.
np.random.seed(RANDOM_SEED)
df_final["mtr_prime"] = df_final["mtr"] + np.random.normal(0, 0.025, size=len(df_final))

# ── Step 5: Summary statistics ─────────────────────────────────────────────
print(f"\n{'='*45}")
print(f"  Total sample size:    {len(df_final):,}")
print(f"  Years covered:        {sorted(df_final['year'].unique())}")
print(f"{'='*45}")
for yr in sorted(df_final["year"].unique()):
    sub = df_final[df_final["year"] == yr]
    print(f"  {yr} mean broad income:   ${sub['broad_income'].mean():>12,.2f}")
    print(f"  {yr} mean taxable income: ${sub['taxable_income'].mean():>12,.2f}")
    print(f"  {yr} mean MTR:             {sub['mtr'].mean():>12.3f}")
    print(f"  {yr} mean MTR':            {sub['mtr_prime'].mean():>12.3f}")
print(f"{'='*45}")
print(f"  Overall mean broad income:   ${df_final['broad_income'].mean():>12,.2f}")
print(f"  Overall std broad income:    ${df_final['broad_income'].std():>12,.2f}")
print(f"  Overall mean taxable income: ${df_final['taxable_income'].mean():>12,.2f}")
print(f"  Overall std taxable income:  ${df_final['taxable_income'].std():>12,.2f}")
print(f"  Overall mean MTR:             {df_final['mtr'].mean():>12.3f}")
print(f"  Overall mean MTR':            {df_final['mtr_prime'].mean():>12.3f}")
print(f"{'='*45}")

# ── Step 6: Export ─────────────────────────────────────────────────────────
export_cols = ["year", "household_id", "broad_income", "taxable_income", "mtr", "mtr_prime"]
df_final[export_cols].to_csv("policyengine_sample_incomes.csv", index=False)
print(f"\nExported to: {os.path.abspath('policyengine_sample_incomes.csv')}")
