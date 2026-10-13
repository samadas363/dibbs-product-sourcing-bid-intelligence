
from pathlib import Path
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OUTPUT_FILE = BASE_DIR / "dibbs_intelligence_report.xlsx"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

query = """
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
    parsing_status,
    item_details_raw,
    raw_record
FROM public.dibbs_index_records
ORDER BY source_line;
"""

try:
    with psycopg2.connect(**DB_CONFIG) as conn:
        df = pd.read_sql_query(query, conn)

except Exception as exc:
    raise SystemExit(f"Database read failed: {exc}")

if df.empty:
    raise SystemExit("No DIBBS index records found.")

# Preserve source values and add a readable date candidate.
df["date_candidate"] = pd.to_datetime(
    df["date_candidate"],
    format="%m/%d/%y",
    errors="coerce"
)

# Summary metrics
summary = pd.DataFrame([
    ["Report", "DIBBS Index Intelligence Report"],
    ["Records imported", len(df)],
    ["Distinct solicitation references",
     df["solicitation_reference"].nunique()],
    ["Distinct NSN candidates", df["nsn_candidate"].nunique()],
    ["Records needing parsing review",
     int((df["parsing_status"] != "CANDIDATE_PARSED").sum())],
    ["Earliest indexed date",
     df["date_candidate"].min().strftime("%Y-%m-%d")
     if df["date_candidate"].notna().any() else "Unavailable"],
    ["Latest indexed date",
     df["date_candidate"].max().strftime("%Y-%m-%d")
     if df["date_candidate"].notna().any() else "Unavailable"],
    ["Data note",
     "Index records only; open status and field definitions not verified."],
], columns=["Metric", "Value"])

unit_summary = (
    df.groupby("unit_of_measure_candidate", dropna=False)
      .size()
      .reset_index(name="Record Count")
      .rename(columns={"unit_of_measure_candidate": "Unit Candidate"})
      .sort_values("Record Count", ascending=False)
)

try:
    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl",
        datetime_format="yyyy-mm-dd"
    ) as writer:
        summary.to_excel(
            writer, sheet_name="Executive Summary", index=False
        )
        unit_summary.to_excel(
            writer, sheet_name="Unit Summary", index=False
        )
        df.to_excel(
            writer, sheet_name="DIBBS Records", index=False
        )

        workbook = writer.book

        for ws in workbook.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:
                cell.font = Font(
                    bold=True, color="FFFFFF"
                )
                cell.fill = PatternFill(
                    "solid", fgColor="1F4E78"
                )
                cell.alignment = Alignment(
                    vertical="center", wrap_text=True
                )

            ws.row_dimensions[1].height = 30

            for column_cells in ws.columns:
                max_length = max(
                    len(str(cell.value or ""))
                    for cell in column_cells[:200]
                )
                width = min(max(max_length + 2, 12), 45)
                ws.column_dimensions[
                    get_column_letter(column_cells[0].column)
                ].width = width

        # Create a filterable Excel table for the full records.
        ws = workbook["DIBBS Records"]
        table = Table(
            displayName="DIBBSRecords",
            ref=ws.dimensions
        )
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

    print("DIBBS Excel report created successfully.")
    print(f"Records exported: {len(df)}")
    print(f"Output file: {OUTPUT_FILE}")

except PermissionError:
    print("Permission denied. Close the Excel report if it is open.")
    raise
