"""
Fetch the 85th percentile income for the City of Los Angeles from ACS data.
"""

import censusdata
import numpy as np


def get_la_income_percentile(percentile: float = 85, year: int = 2022) -> dict:
    """
    Get income percentile for City of Los Angeles from ACS data.

    Args:
        percentile: The percentile to calculate (default: 85)
        year: ACS year to use (default: 2022, which is ACS 2022 5-year estimates)

    Returns:
        Dictionary with results
    """
    print(f"Fetching ACS {year} 5-year estimates for Los Angeles...")

    # Los Angeles city FIPS codes
    # State: 06 (California)
    # County: 037 (Los Angeles County)
    # Place: 44000 (Los Angeles city)

    # Get household income data for LA city
    # B19001 is the table for household income distribution

    try:
        # Fetch data for Los Angeles city
        la_city = censusdata.download(
            "acs5",
            year,
            censusdata.censusgeo([("state", "06"), ("place", "44000")]),
            ["B19001_001E"]  # Total households
            + [f"B19001_{str(i).zfill(3)}E" for i in range(2, 18)],  # Income brackets
        )

        print(f"\nData retrieved successfully for {len(la_city)} geographies")

        # Income brackets (midpoints in dollars)
        # B19001_002E: Less than $10,000
        # B19001_003E: $10,000 to $14,999
        # ... continuing through
        # B19001_017E: $200,000 or more

        income_brackets = {
            "B19001_002E": 5000,  # < $10k
            "B19001_003E": 12500,  # $10k-$14,999
            "B19001_004E": 17500,  # $15k-$19,999
            "B19001_005E": 22500,  # $20k-$24,999
            "B19001_006E": 27500,  # $25k-$29,999
            "B19001_007E": 32500,  # $30k-$34,999
            "B19001_008E": 37500,  # $35k-$39,999
            "B19001_009E": 42500,  # $40k-$44,999
            "B19001_010E": 47500,  # $45k-$49,999
            "B19001_011E": 55000,  # $50k-$59,999
            "B19001_012E": 67500,  # $60k-$74,999
            "B19001_013E": 87500,  # $75k-$99,999
            "B19001_014E": 112500,  # $100k-$124,999
            "B19001_015E": 137500,  # $125k-$149,999
            "B19001_016E": 175000,  # $150k-$199,999
            "B19001_017E": 250000,  # $200k+
        }

        # Extract household counts and create distribution
        households = []
        incomes = []

        for var, income in income_brackets.items():
            count = la_city.iloc[0][var]
            households.append(count)
            incomes.append(income)

        # Create expanded list of incomes weighted by household count
        income_distribution = []
        for income, count in zip(incomes, households):
            income_distribution.extend([income] * int(count))

        # Calculate percentile
        pct_value = np.percentile(income_distribution, percentile)

        # Also get median for context
        median = np.percentile(income_distribution, 50)

        total_households = la_city.iloc[0]["B19001_001E"]

        results = {
            "year": year,
            "percentile": percentile,
            "income": pct_value,
            "median_income": median,
            "total_households": total_households,
            "geography": "Los Angeles city, California",
        }

        return results

    except Exception as e:
        print(f"Error fetching data: {e}")
        raise


if __name__ == "__main__":
    # Get 85th percentile income for LA
    results = get_la_income_percentile(percentile=85, year=2022)

    print("\n" + "=" * 60)
    print("RESULTS: Los Angeles City Income Percentile")
    print("=" * 60)
    print(f"Geography: {results['geography']}")
    print(f"ACS Year: {results['year']} (5-year estimates)")
    print(f"Total Households: {results['total_households']:,}")
    print(f"\nMedian Household Income: ${results['median_income']:,.0f}")
    print(f"{results['percentile']}th Percentile Income: ${results['income']:,.0f}")
    print("=" * 60)
