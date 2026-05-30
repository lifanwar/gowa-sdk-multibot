def parse_number(value: str) -> int:
    """
    Mengubah string angka menjadi integer.

    Contoh:
    "1000000" -> 1000000
    "1.000.000" -> 1000000
    "1,000,000" -> 1000000
    "Rp 1.000.000" -> 1000000
    """

    cleaned = (
        value
        .replace("Rp", "")
        .replace("rp", "")
        .replace("IDR", "")
        .replace("idr", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
    )

    if not cleaned.isdigit():
        raise ValueError(f"Invalid number format: {value}")

    return int(cleaned)