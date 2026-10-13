
from pathlib import Path
import pandas as pd

folder = Path(__file__).resolve().parent
csv_path = folder / "dibbs_index_preview.csv"

df = pd.read_csv(csv_path, dtype=str).fillna("")

print("DIBBS INDEX VALIDATION")
print("-" * 40)
print(f"Total records: {len(df)}")
print(
    "Distinct solicitation references:",
    df["solicitation_reference"].nunique()
)
print("Distinct NSNs:", df["nsn_candidate"].nunique())
print(
    "Duplicate solicitation references:",
    df["solicitation_reference"].duplicated().sum()
)

print("\nMissing-value checks:")
for column in [
    "solicitation_reference",
    "nsn_candidate",
    "date_candidate",
    "pdf_filename_candidate",
    "item_details_raw",
]:
    print(f"{column}: {(df[column].str.strip() == '').sum()} blank")

print("\nDate values:")
print(df["date_candidate"].value_counts().to_string())

print("\nFirst 10 records:")
print(
    df[
        [
            "solicitation_reference",
            "nsn_candidate",
            "date_candidate",
            "pdf_filename_candidate",
            "item_details_raw",
        ]
    ].head(10).to_string(index=False)
)

print("\nValidation report completed. No database changes made.")
