
from pathlib import Path
import csv
import re

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "dibbs_index_preview.csv"


def parse_dibbs_reference(combined_reference):
    value = (combined_reference or "").strip().upper()

    if len(value) != 26:
        raise ValueError(
            f"Expected 26 characters, got {len(value)}: {value!r}"
        )

    solicitation_code = value[:13]
    material_candidate = value[13:]

    if not re.fullmatch(
        r"[A-Z0-9]{6}\d{2}[A-Z][A-Z0-9]{4}",
        solicitation_code,
    ):
        raise ValueError(
            f"Unrecognized solicitation code: {solicitation_code}"
        )

    solicitation_number = (
        f"{solicitation_code[:6]}-"
        f"{solicitation_code[6:8]}-"
        f"{solicitation_code[8]}-"
        f"{solicitation_code[9:]}"
    )

    return solicitation_number, material_candidate


if not CSV_FILE.exists():
    raise FileNotFoundError(f"CSV not found: {CSV_FILE}")

total = 0
parsed = 0
errors = []
nonnumeric_materials = []
solicitation_codes = set()

with CSV_FILE.open(
    "r", newline="", encoding="utf-8-sig"
) as file:
    reader = csv.DictReader(file)

    for row in reader:
        total += 1
        reference = row["solicitation_reference"].strip()

        try:
            solicitation, material = parse_dibbs_reference(reference)
            parsed += 1
            solicitation_codes.add(solicitation)

            if not material.isdigit():
                nonnumeric_materials.append(
                    (row["source_line"], reference, material)
                )

        except ValueError as exc:
            errors.append(
                (row["source_line"], reference, str(exc))
            )

print("\nDIBBS PARSER AUDIT")
print("-" * 45)
print(f"CSV records checked: {total}")
print(f"Records parsed: {parsed}")
print(f"Parsing errors: {len(errors)}")
print(f"Distinct parsed solicitation numbers: {len(solicitation_codes)}")
print(f"Nonnumeric material candidates: {len(nonnumeric_materials)}")

if errors:
    print("\nPARSING ERRORS (first 20)")
    for line, reference, error in errors[:20]:
        print(f"Line {line}: {reference} | {error}")

if nonnumeric_materials:
    print("\nNONNUMERIC MATERIAL CANDIDATES (first 20)")
    for line, reference, material in nonnumeric_materials[:20]:
        print(f"Line {line}: {reference} | Candidate: {material}")

print("\nAudit complete. No database changes were made.")
