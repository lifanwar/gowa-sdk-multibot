from datetime import datetime

def parse_timestamp(raw_timestamp: str | None) -> dict:
    data = {
        "raw": raw_timestamp,
        "date": None,
        "time": None,
    }

    if not raw_timestamp:
        return data

    raw_timestamp = raw_timestamp.strip()
    data["raw"] = raw_timestamp

    try:
        parsed_datetime = datetime.fromisoformat(
            raw_timestamp.replace("Z", "+00:00")
        )

        data["date"] = parsed_datetime.date().isoformat()
        data["time"] = parsed_datetime.time().replace(microsecond=0).isoformat()

    except ValueError:
        if "T" in raw_timestamp:
            date_part, time_part = raw_timestamp.split("T", 1)

            data["date"] = date_part
            data["time"] = (
                time_part
                .replace("Z", "")
                .split("+")[0]
                .split(".")[0]
            )

    return data