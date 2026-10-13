
from pathlib import Path
import csv
import os
import re

import psycopg2
from dotenv import load_dotenv


# ==================================================
# 1. PROJECT PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

CSV_FILE = BASE_DIR / "dibbs_index_preview.csv"
TXT_FILE = BASE_DIR / "dibbs_index_samole.txt"
ENV_FILE = BASE_DIR / ".env"


# ==================================================
# 2. LOAD DATABASE CONFIGURATION
# ==================================================

load_dotenv(ENV_FILE)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

missing_settings = [
    key
    for key in ("host", "dbname", "user", "password")
    if not DB_CONFIG[key]
]

if missing_settings:
    raise ValueError(
        f"Missing database settings in .env: {missing_settings}"
    )


# ==================================================
# 3. VALIDATE REQUIRED FILES
# ==================================================

for path in (CSV_FILE, TXT_FILE):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


# ==================================================
# 4. PARSE DIBBS COMBINED REFERENCE
# ==================================================

def parse_dibbs_reference(combined_reference):
    """
    Split a 26-character combined reference into:
      - 13-character solicitation-code candidate
      - 13-character material-number candidate

    This is a parsing rule inferred from the current index.
    It does not independently verify official identifiers.
    """

    value = (combined_reference or "").strip().upper()

    if len(value) != 26:
        raise ValueError(
            f"Expected 26 characters, got {len(value)}: {value!r}"
        )

    solicitation_code = value[:13]
    material_candidate = value[13:]

    pattern = r"[A-Z0-9]{6}\d{2}[A-Z][A-Z0-9]{4}"

    if not re.fullmatch(pattern, solicitation_code):
        raise ValueError(
            f"Unrecognized solicitation-code format: "
            f"{solicitation_code!r}"
        )

    # Format the candidate using the structure observed in the index.
    solicitation_candidate = (
        f"{solicitation_code[:6]}-"
        f"{solicitation_code[6:8]}-"
        f"{solicitation_code[8]}-"
        f"{solicitation_code[9:]}"
    )

    return solicitation_candidate, material_candidate


# ==================================================
# 5. LOAD ORIGINAL FIXED-WIDTH RECORDS
# ==================================================

with TXT_FILE.open(
    "r",
    encoding="utf-8-sig",
    errors="replace",
) as file:
    raw_records = [
        line.rstrip("\r\n")
        for line in file
        if line.strip()
    ]


# ==================================================
# 6. SQL UPSERT
# IMPORTANT:
# This SQL belongs in Python, not directly in pgAdmin.
# ==================================================

upsert_sql = """
    INSERT INTO public.dibbs_index_records (
        source_line,
        solicitation_reference,
        nsn_candidate,
        date_candidate,
        pdf_filename_candidate,
        item_details_raw,
        raw_record,
        parsed_solicitation_number,
        material_number_candidate,
        parser_status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

    ON CONFLICT (source_line)
    DO UPDATE SET
        solicitation_reference = EXCLUDED.solicitation_reference,
        nsn_candidate = EXCLUDED.nsn_candidate,
        date_candidate = EXCLUDED.date_candidate,
        pdf_filename_candidate = EXCLUDED.pdf_filename_candidate,
        item_details_raw = EXCLUDED.item_details_raw,
        raw_record = EXCLUDED.raw_record,
        parsed_solicitation_number =
            EXCLUDED.parsed_solicitation_number,
        material_number_candidate =
            EXCLUDED.material_number_candidate,
        parser_status = EXCLUDED.parser_status
"""


# ==================================================
# 7. IMPORT COUNTERS
# ==================================================

inserted = 0
updated = 0
review_required = 0
numeric_candidates = 0
processed = 0
errors = []


# ==================================================
# 8. IMPORT CSV RECORDS INTO POSTGRESQL
# ==================================================

try:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            with CSV_FILE.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                reader = csv.DictReader(file)

                required_columns = {
                    "source_line",
                    "solicitation_reference",
                    "nsn_candidate",
                    "date_candidate",
                    "pdf_filename_candidate",
                    "item_details_raw",
                }

                available_columns = set(reader.fieldnames or [])
                missing_columns = required_columns - available_columns

                if missing_columns:
                    raise ValueError(
                        "CSV is missing required columns: "
                        f"{sorted(missing_columns)}"
                    )

                for row in reader:
                    source_line = int(row["source_line"])

                    if not 1 <= source_line <= len(raw_records):
                        raise ValueError(
                            f"Invalid source line: {source_line}"
                        )

                    raw_record = raw_records[source_line - 1]

                    if len(raw_record) != 140:
                        raise ValueError(
                            f"Unexpected record length on source line "
                            f"{source_line}: {len(raw_record)}"
                        )

                    combined_reference = (
                        row["solicitation_reference"].strip()
                    )

                    # Parse the reference without changing the original.
                    try:
                        (
                            solicitation_candidate,
                            material_candidate,
                        ) = parse_dibbs_reference(combined_reference)

                    except ValueError as exc:
                        # Fail the transaction instead of saving a
                        # malformed record with misleading identifiers.
                        raise ValueError(
                            f"Source line {source_line}: {exc}"
                        ) from exc

                    purchase_request_number = (
                        row["nsn_candidate"].strip()
                    )

                    if material_candidate.isdigit():
                        parser_status = "parsed_candidate"
                        numeric_candidates += 1
                    else:
                        parser_status = "review_required"
                        review_required += 1

                    # Check whether this source line already exists.
                    cur.execute(
                        """
                        SELECT 1
                        FROM public.dibbs_index_records
                        WHERE source_line = %s
                        """,
                        (source_line,),
                    )

                    existed_before = cur.fetchone() is not None

                    # Execute the SQL template with parameters.
                    cur.execute(
                        upsert_sql,
                        (
                            source_line,
                            combined_reference,
                            purchase_request_number,
                            row["date_candidate"].strip(),
                            row["pdf_filename_candidate"].strip(),
                            row["item_details_raw"].strip(),
                            raw_record,
                            solicitation_candidate,
                            material_candidate,
                            parser_status,
                        ),
                    )

                    processed += 1

                    if existed_before:
                        updated += 1
                    else:
                        inserted += 1

    # Successful completion commits the transaction automatically.

    print("\nDIBBS INDEX IMPORT COMPLETE")
    print("=" * 45)
    print(f"CSV records processed: {processed}")
    print(f"New records inserted: {inserted}")
    print(f"Existing records refreshed: {updated}")
    print(f"Numeric material candidates: {numeric_candidates}")
    print(f"Nonnumeric candidates needing review: {review_required}")
    print(f"Total processed: {inserted + updated}")

except Exception as exc:
    print("\nIMPORT FAILED")
    print(f"Reason: {exc}")
    print("The database transaction was rolled back.")
    raise

print("\nNext: verify the parser status in pgAdmin.")
