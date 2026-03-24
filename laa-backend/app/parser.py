import re
from datetime import datetime

# Regex to capture key=value pairs (handles quoted values as well)
KV_PATTERN = re.compile(r'(\w+)=(".*?"|\S+)')


def parse_kv_line(line: str) -> dict:
    """
    Parses a single log line with dynamic key=value pairs.
    Returns a dictionary of extracted fields.
    """
    matches = KV_PATTERN.findall(line)

    data = {}
    for key, value in matches:
        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        data[key] = value

    return data


def parse_logs(log_lines):
    parsed = []

    for line in log_lines:
        if not line or not line.strip():
            continue

        try:
            data = parse_kv_line(line)

            # Standard fields (fallback-safe)
            timestamp = data.get("ts", str(datetime.now()))
            level = data.get("level", "INFO")
            service = data.get("svc", data.get("app", "unknown"))
            message = data.get("msg", line)

            # Remove standard fields from metadata
            standard_keys = {"ts", "level", "msg", "svc", "app"}
            metadata = {k: v for k, v in data.items() if k not in standard_keys}

            parsed.append({
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "service": service,
                "metadata": metadata
            })

        except Exception as e:
            # Fallback for completely unstructured lines
            parsed.append({
                "timestamp": str(datetime.now()),
                "level": "INFO",
                "message": line,
                "service": "unknown",
                "metadata": {
                    "parse_error": str(e)
                }
            })

    return parsed