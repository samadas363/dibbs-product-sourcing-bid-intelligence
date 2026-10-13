
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

OUTPUT_FILE = PROJECT_DIR / "dibbs_search_results.xlsx"

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
    parsing_status,
    item_details_raw
FROM public.dibbs_index_records
ORDER BY source_line;
"""


def main():
    engine = None

    try:
        db_url = URL.create(
            drivername="postgresql+psycopg2",
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME"),
        )

        engine = create_engine(db_url)

        with engine.connect() as conn:
            df = pd.read_sql_query(text(SQL), conn)

    except Exception as exc:
        print(f"Database error: {exc}")
        return

    finally:
        if engine is not None:
            engine.dispose()

    if df.empty:
        print("No DIBBS records found.")
        return

    df["parsed_date"] = pd.to_datetime(
        df["date_candidate"],
        format="%m/%d/%y",
        errors="coerce",
    )

    print(f"\nRecords available: {len(df)}")
    print("\nSearch fields:")
    print("1. All fields")
    print("2. NSN")
    print("3. Solicitation reference")
    print("4. Item description")
    print("5. PDF filename")

    choice = input("\nChoose a field (1-5): ").strip()
    search_term = input(
        "Enter search text (leave blank for no text filter): "
    ).strip()

    search_columns = {
        "1": [
            "solicitation_reference",
            "nsn_candidate",
            "pdf_filename_candidate",
            "item_description_candidate",
            "additional_codes_candidate",
            "item_details_raw",
        ],
        "2": ["nsn_candidate"],
        "3": ["solicitation_reference"],
        "4": ["item_description_candidate"],
        "5": ["pdf_filename_candidate"],
    }

    if choice not in search_columns:
        print("Invalid choice.")
        return

    results = df.copy()

    if search_term:
        mask = pd.Series(False, index=results.index)

        for column in search_columns[choice]:
            mask |= results[column].fillna("").astype(str).str.contains(
                search_term,
                case=False,
                regex=False,
            )

        results = results[mask]

    start_date = input(
        "Start date MM/DD/YY (optional, press Enter to skip): "
    ).strip()

    end_date = input(
        "End date MM/DD/YY (optional, press Enter to skip): "
    ).strip()

    try:
        if start_date:
            start = pd.to_datetime(
                start_date, format="%m/%d/%y", errors="raise"
            )
            results = results[results["parsed_date"] >= start]

        if end_date:
            end = pd.to_datetime(
                end_date, format="%m/%d/%y", errors="raise"
            )
            results = results[results["parsed_date"] <= end]

        if start_date and end_date and start > end:
            print("Start date cannot be later than end date.")
            return

    except ValueError:
        print("Invalid date. Use MM/DD/YY, for example 10/15/26.")
        return

    results = results.drop(columns=["parsed_date"])

    print(f"\nMatching records: {len(results)}")

    if results.empty:
        print("No records matched your search.")
        return

    display_columns = [
        "solicitation_reference",
        "nsn_candidate",
        "date_candidate",
        "quantity_candidate",
        "unit_of_measure_candidate",
        "item_description_candidate",
        "pdf_filename_candidate",
    ]

    print("\nSearch results:")
    print(results[display_columns].head(25).to_string(index=False))

    try:
        results.to_excel(OUTPUT_FILE, index=False)
        print(f"\nExcel results saved to:\n{OUTPUT_FILE}")
    except Exception as exc:
        print(f"Could not save Excel file: {exc}")


if __name__ == "__main__":
    main()
