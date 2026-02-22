#%%
import h5py
import pandas as pd
import numpy as np
import os
from huggingface_hub import hf_hub_download

# Parameters 
S           = 1000   # Total sample size across all years
RANDOM_SEED = 42

# Only these two files have the required PolicyEngine-enhanced structure.
# census_cps_2020/2021/2022.h5 exist on HuggingFace but are raw Census files
# that lack household_weight, household_id, and all income variables.
YEARS = {
    2023: "cps_2023.h5",
    2024: "cps_2024.h5",
}

N_PER_YEAR = S // len(YEARS)  # = S/2 for now

# Income variable definitions
BROAD_INCOME_VARS = [
    'employment_income', 'self_employment_income', 'tip_income',
    'social_security_retirement', 'unemployment_compensation',
    'disability_benefits', 'veterans_benefits',
    'taxable_private_pension_income', 'tax_exempt_private_pension_income',
    'long_term_capital_gains', 'short_term_capital_gains',
    'qualified_dividend_income', 'non_qualified_dividend_income',
    'taxable_interest_income', 'tax_exempt_interest_income',
    'rental_income', 'farm_income', 'alimony_income', 'child_support_received'
]

TAXABLE_INCOME_VARS = [
    'employment_income', 'self_employment_income', 'tip_income',
    'social_security_retirement', 'unemployment_compensation',
    'taxable_private_pension_income', 'taxable_401k_distributions',
    'taxable_ira_distributions', 'long_term_capital_gains',
    'short_term_capital_gains', 'qualified_dividend_income',
    'non_qualified_dividend_income', 'taxable_interest_income',
    'rental_income', 'farm_income', 'alimony_income'
]

#%%
# 1: Download files
print("=== Downloading files ===")
file_paths = {}
for year, filename in YEARS.items():
    print(f"  {year}: {filename}")
    file_paths[year] = hf_hub_download(
        repo_id="policyengine/policyengine-us-data",
        filename=filename
    )

#%%
# 2: Process each year
# For each year:
#   1. Load household and person level data from h5
#   2. Aggregate income variables to household level
#   3. Expand rows by round(household_weight / 10), minimum 1
#   4. Draw random sample of N_PER_YEAR rows
#
# Note: baseline.calculate() returns zeros for computed variables (AGI, MTR,
# income_tax) with current package versions, so I construct BI and TI
# manually from raw h5 variables. MTR remains unresolved (see GitHub issue).

all_samples = []

for year, filename in YEARS.items():
    print(f"\nProcessing {year}...")
    path = file_paths[year]

    with h5py.File(path, 'r') as f:
        keys = list(f.keys())
        household_id     = f['household_id'][:]
        household_weight = f['household_weight'][:]
        person_hh_id     = f['person_household_id'][:]

        # Only use variables that exist in this file
        broad_vars   = [v for v in BROAD_INCOME_VARS   if v in keys]
        taxable_vars = [v for v in TAXABLE_INCOME_VARS if v in keys]

        missing_broad   = [v for v in BROAD_INCOME_VARS   if v not in keys]
        missing_taxable = [v for v in TAXABLE_INCOME_VARS if v not in keys]
        if missing_broad:
            print(f"  WARNING: Missing broad vars: {missing_broad}")
        if missing_taxable:
            print(f"  WARNING: Missing taxable vars: {missing_taxable}")

        broad_person   = sum(f[v][:] for v in broad_vars)
        taxable_person = sum(f[v][:] for v in taxable_vars)

    # Aggregate to household level
    broad_hh = (pd.DataFrame({'household_id': person_hh_id, 'broad_income': broad_person})
                  .groupby('household_id')['broad_income'].sum())
    taxable_hh = (pd.DataFrame({'household_id': person_hh_id, 'taxable_income': taxable_person})
                    .groupby('household_id')['taxable_income'].sum())

    # Build household DataFrame and map income
    df = pd.DataFrame({'household_id': household_id, 'household_weight': household_weight})
    df['broad_income']   = df['household_id'].map(broad_hh)
    df['taxable_income'] = df['household_id'].map(taxable_hh)
    df['year']           = year
    df = df[df['household_weight'] > 0].dropna(subset=['household_weight'])

    print(f"  Households: {len(df):,}")

    # Expand rows by round(weight / 10), minimum 1 per household
    df['repeat_count'] = df['household_weight'].apply(lambda w: max(round(w / 10), 1))
    df_expanded = df.loc[df.index.repeat(df['repeat_count'])].drop(columns=['repeat_count'])

    print(f"  Expanded rows: {len(df_expanded):,}")

    # Sample N_PER_YEAR rows
    df_year_sample = df_expanded.sample(n=N_PER_YEAR, random_state=RANDOM_SEED).copy()
    print(f"  Sampled: {len(df_year_sample):,}")

    all_samples.append(df_year_sample)

#%%
# 3: Combine all years 
df_final = pd.concat(all_samples, ignore_index=True)

# 4: Summary statistics
print(f"\n{'='*45}")
print(f"  Total sample size:    {len(df_final):,}")
print(f"  Years covered:        {sorted(df_final['year'].unique())}")
print(f"{'='*45}")
for yr in sorted(df_final['year'].unique()):
    sub = df_final[df_final['year'] == yr]
    print(f"  {yr} mean broad income:   ${sub['broad_income'].mean():>12,.2f}")
    print(f"  {yr} mean taxable income: ${sub['taxable_income'].mean():>12,.2f}")
print(f"{'='*45}")
print(f"  Overall mean broad income:   ${df_final['broad_income'].mean():>12,.2f}")
print(f"  Overall std broad income:    ${df_final['broad_income'].std():>12,.2f}")
print(f"  Overall mean taxable income: ${df_final['taxable_income'].mean():>12,.2f}")
print(f"  Overall std taxable income:  ${df_final['taxable_income'].std():>12,.2f}")
print(f"{'='*45}")

# 5: Export
export_cols = ['year', 'household_id', 'broad_income', 'taxable_income']
df_final[export_cols].to_csv("policyengine_sample_incomes.csv", index=False)
print(f"\nExported to: {os.path.abspath('policyengine_sample_incomes.csv')}")
