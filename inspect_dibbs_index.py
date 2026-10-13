
from pathlib import Path
import csv
import re

folder = Path(__file__).resolve().parent
source_file = folder / "dibbs_index_samole.txt"
output_file = folder / "dibbs_index_preview.csv"

with source_file.open(
    "r", encoding="utf-8-sig", errors="replace"
) as file:
    records = [line.rstrip("\r\n") for line in file if line.strip()]

rows = []

for line_number, line in enumerate(records, start=1):
    if len(line) != 140:
        print(f"Skipping line {line_number}: length={len(line)}")
        continue

    solicitation_reference = line[0:26].strip()
    nsn = line[62:72].strip()
    date_text = line[72:80].strip()
    pdf_filename = line[80:97].strip()
    # The remaining section appears to contain quantity,
    # unit of measure, description, and other codes.
    item_details = line[97:140].strip()

    rows.append({
        "source_line": line_number,
        "solicitation_reference": solicitation_reference,
        "nsn_candidate": nsn,
        "date_candidate": date_text,
        "pdf_filename_candidate": pdf_filename,
        "item_details_raw": item_details,
        "field_positions_verified": False,
    })

with output_file.open(
    "w", newline="", encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Records read: {len(records)}")
print(f"Preview rows exported: {len(rows)}")
print(f"CSV saved to: {output_file}")

print("\nFirst 3 preview records:")
for row in rows[:3]:
    print(row)
