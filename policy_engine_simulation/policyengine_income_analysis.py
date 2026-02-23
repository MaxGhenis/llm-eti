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

#  Federal tax brackets
# Approximates MTR from federal income tax brackets by filing status.
# Filing status is inferred: households with 2+ people in the same marital
# unit are treated as married filing jointly (MFJ); all others as single.
# NOTE: Still an approximation — ignores deductions, credits, AMT, FICA,
# and state taxes. To be replaced with baseline.calculate("marginal_tax_rate")
# once memory issues are resolved. See GitHub issue for full context.
TAX_BRACKETS = {
    2023: {
        'single': [
            (11_000,    0.10),
            (44_725,    0.12),
            (95_375,    0.22),
            (182_050,   0.24),
            (231_250,   0.32),
            (578_125,   0.35),
            (np.inf,    0.37),
        ],
        'mfj': [
            (22_000,    0.10),
            (89_450,    0.12),
            (190_750,   0.22),
            (364_200,   0.24),
            (462_500,   0.32),
            (693_750,   0.35),
            (np.inf,    0.37),
        ],
    },
    2024: {
        'single': [
            (11_600,    0.10),
            (47_150,    0.12),
            (100_525,   0.22),
            (191_950,   0.24),
            (243_725,   0.32),
            (609_350,   0.35),
            (np.inf,    0.37),
        ],
        'mfj': [
            (23_200,    0.10),
            (94_300,    0.12),
            (201_050,   0.22),
            (383_900,   0.24),
            (487_450,   0.32),
            (731_200,   0.35),
            (np.inf,    0.37),
        ],
    },
}

def compute_mtr(taxable_income: pd.Series, is_mfj: pd.Series, year: int) -> pd.Series:
    """Return the marginal federal income tax rate for each household,
    using MFJ brackets for married households and single brackets otherwise."""
    result = pd.Series(np.nan, index=taxable_income.index)
    for status, mask in [('mfj', is_mfj), ('single', ~is_mfj)]:
        brackets = TAX_BRACKETS[year][status]
        thresholds = [b[0] for b in brackets]
        rates      = [b[1] for b in brackets]
        ti = taxable_income[mask]
        if len(ti) == 0:
            continue
        conditions = [ti <= t for t in thresholds]
        result[mask] = np.select(conditions, rates, default=rates[-1])
    return result

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
#   2. Infer filing status (MFJ vs single) from marital unit structure
#   3. Aggregate income variables to household level
#   4. Compute approximate MTR using filing-status-appropriate brackets
#   5. Expand rows by round(household_weight / 10), minimum 1
#   6. Draw random sample of N_PER_YEAR rows

all_samples = []

for year, filename in YEARS.items():
    print(f"\nProcessing {year}...")
    path = file_paths[year]

    with h5py.File(path, 'r') as f:
        keys = list(f.keys())
        household_id     = f['household_id'][:]
        household_weight = f['household_weight'][:]
        person_hh_id     = f['person_household_id'][:]
        person_marital   = f['person_marital_unit_id'][:]

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

    # Infer MFJ: households where any marital unit has 2+ members
    person_df = pd.DataFrame({
        'household_id':    person_hh_id,
        'marital_unit_id': person_marital
    })
    marital_size = person_df.groupby('marital_unit_id').size().rename('marital_unit_size')
    person_df = person_df.join(marital_size, on='marital_unit_id')
    is_mfj_hh = (person_df[person_df['marital_unit_size'] >= 2]
                 .groupby('household_id').size() > 0)
    print(f"  MFJ households: {is_mfj_hh.sum():,} / {len(household_id):,}")

    # Aggregate income to household level
    broad_hh = (pd.DataFrame({'household_id': person_hh_id, 'broad_income': broad_person})
                  .groupby('household_id')['broad_income'].sum())
    taxable_hh = (pd.DataFrame({'household_id': person_hh_id, 'taxable_income': taxable_person})
                    .groupby('household_id')['taxable_income'].sum())

    # Build household DataFrame
    df = pd.DataFrame({'household_id': household_id, 'household_weight': household_weight})
    df['broad_income']   = df['household_id'].map(broad_hh)
    df['taxable_income'] = df['household_id'].map(taxable_hh)
    df['is_mfj']         = df['household_id'].map(is_mfj_hh).fillna(False)
    df['filing_status']  = df['is_mfj'].map({True: 'mfj', False: 'single'})
    df['year']           = year
    df = df[df['household_weight'] > 0].dropna(subset=['household_weight'])

    # Compute approximate MTR using filing-status-appropriate brackets
    df['mtr_approx'] = compute_mtr(df['taxable_income'], df['is_mfj'], year)
    print(f"  Households: {len(df):,}")

    # Expand rows by round(weight / 10), minimum 1
    df['repeat_count'] = df['household_weight'].apply(lambda w: max(round(w / 10), 1))
    df_expanded = df.loc[df.index.repeat(df['repeat_count'])].drop(columns=['repeat_count', 'is_mfj'])

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
print(f"  Filing status mix:    {df_final['filing_status'].value_counts().to_dict()}")
print(f"{'='*45}")
for yr in sorted(df_final['year'].unique()):
    sub = df_final[df_final['year'] == yr]
    print(f"  {yr} mean broad income:   ${sub['broad_income'].mean():>12,.2f}")
    print(f"  {yr} mean taxable income: ${sub['taxable_income'].mean():>12,.2f}")
    print(f"  {yr} mean MTR (approx):    {sub['mtr_approx'].mean():>12.3f}")
print(f"{'='*45}")
print(f"  Overall mean broad income:   ${df_final['broad_income'].mean():>12,.2f}")
print(f"  Overall std broad income:    ${df_final['broad_income'].std():>12,.2f}")
print(f"  Overall mean taxable income: ${df_final['taxable_income'].mean():>12,.2f}")
print(f"  Overall std taxable income:  ${df_final['taxable_income'].std():>12,.2f}")
print(f"  Overall mean MTR (approx):    {df_final['mtr_approx'].mean():>12.3f}")
print(f"{'='*45}")

# 5: Export
export_cols = ['year', 'household_id', 'filing_status', 'broad_income', 'taxable_income', 'mtr_approx']
df_final[export_cols].to_csv("policyengine_sample_incomes.csv", index=False)
print(f"\nExported to: {os.path.abspath('policyengine_sample_incomes.csv')}")
