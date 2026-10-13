
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

OUTPUT_FILE = PROJECT_DIR / "dibbs_duplicate_audit.xlsx"

SQL = """
SELECT
    source_line,
    solicitation_reference,
    nsn_candidate,
    date_candidate,
    pdf_filename_candidate,
    quantity_candidate,
    unit_of_measure_candidate,
    item_description_candidate,
    additional_codes_candidate,
    parsing_status
FROM public.dibbs_index_records
ORDER BY source_line;
"""


def main():
    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(text(SQL), conn)
    finally:
        engine.dispose()

    if df.empty:
        print("No DIBBS records found.")
        return

    # Identify repeated solicitation references.
    ref_counts = df["solicitation_reference"].value_counts(dropna=False)
    repeated_refs = ref_counts[ref_counts > 1].rename_axis(
        "solicitation_reference"
    ).reset_index(name="record_count")

    ref_audit = df.merge(
        repeated_refs,
        on="solicitation_reference",
        how="inner",
    ).sort_values(["solicitation_reference", "source_line"])

    # Identify repeated NSNs.
    nsn_counts = df["nsn_candidate"].value_counts(dropna=False)
    repeated_nsns = nsn_counts[nsn_counts > 1].rename_axis(
        "nsn_candidate"
    ).reset_index(name="record_count")

    nsn_audit = df.merge(
        repeated_nsns,
        on="nsn_candidate",
        how="inner",
    ).sort_values(["nsn_candidate", "source_line"])

    # Flag candidate-field issues for review.
    quality = df.copy()

    candidate_columns = [
        "solicitation_reference",
        "nsn_candidate",
        "date_candidate",
        "pdf_filename_candidate",
        "quantity_candidate",
        "unit_of_measure_candidate",
        "item_description_candidate",
        "additional_codes_candidate",
    ]

    quality["missing_candidate_fields"] = quality[
        candidate_columns
    ].isna().sum(axis=1)

    quality["review_reason"] = ""

    quality.loc[
        quality["solicitation_reference"].isna()
        | quality["nsn_candidate"].isna()
        | quality["pdf_filename_candidate"].isna(),
        "review_reason",
    ] = "Missing key candidate field"

    quality.loc[
        quality["quantity_candidate"].notna()
        & (quality["quantity_candidate"] <= 0),
        "review_reason",
    ] = "Quantity is zero or negative"

    quality["needs_review"] = (
        quality["missing_candidate_fields"] > 0
    ) | (quality["review_reason"] != "")

    summary = pd.DataFrame({
        "Metric": [
            "Total index records",
            "Distinct solicitation references",
            "Solicitation references repeated across records",
            "Records belonging to repeated references",
            "Distinct NSN candidates",
            "Repeated NSN candidates",
            "Records belonging to repeated NSNs",
            "Records flagged for candidate-field review",
        ],
        "Value": [
            len(df),
            df["solicitation_reference"].nunique(),
            len(repeated_refs),
            len(ref_audit),
            df["nsn_candidate"].nunique(),
            len(repeated_nsns),
            len(nsn_audit),
            int(quality["needs_review"].sum()),
        ],
    })

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Audit Summary", index=False)
        ref_audit.to_excel(
            writer, sheet_name="Repeated References", index=False
        )
        nsn_audit.to_excel(
            writer, sheet_name="Repeated NSNs", index=False
        )
        quality.to_excel(
            writer, sheet_name="Data Quality Review", index=False
        )

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for column_cells in ws.columns:
                max_length = max(
                    len(str(cell.value or "")) for cell in column_cells
                )
                ws.column_dimensions[
                    column_cells[0].column_letter
                ].width = min(max_length + 2, 40)

    print("\nDIBBS duplicate audit completed.")
    print(f"Records reviewed: {len(df)}")
    print(f"Repeated solicitation references: {len(repeated_refs)}")
    print(f"Repeated NSN candidates: {len(repeated_nsns)}")
    print(f"Records flagged for review: {int(quality['needs_review'].sum())}")
    print(f"Excel report saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
