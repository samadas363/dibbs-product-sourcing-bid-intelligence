def parse_dibbs_reference(combined_reference):
    value = (combined_reference or "").strip().upper()

    if len(value) != 26:
        raise ValueError(
            f"Expected 26 characters: {value!r}, "
            f"length={len(value)}"
        )

    solicitation_code = value[:13]
    material_candidate = value[13:]

    if not re.fullmatch(
        r"[A-Z0-9]{6}\d{2}[A-Z][A-Z0-9]{4}",
        solicitation_code,
    ):
        raise ValueError(
            f"Unrecognized solicitation format: "
            f"{solicitation_code!r}"
        )

    solicitation_number = (
        f"{solicitation_code[:6]}-"
        f"{solicitation_code[6:8]}-"
        f"{solicitation_code[8]}-"
        f"{solicitation_code[9:]}"
    )

    return solicitation_number, material_candidate