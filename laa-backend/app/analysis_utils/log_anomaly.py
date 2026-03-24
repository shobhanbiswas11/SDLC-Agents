from datetime import datetime
import numpy as np
from collections import defaultdict


def detect_latency_anomalies(parsed_logs):
    latencies = []

    for log in parsed_logs:
        val = log.get("metadata", {}).get("latency")
        if val:
            try:
                latencies.append(float(val))
            except:
                pass

    anomalies = []

    if not latencies:
        return anomalies

    mean = np.mean(latencies)
    std = np.std(latencies)

    for log in parsed_logs:
        val = log.get("metadata", {}).get("latency")
        if val:
            try:
                val = float(val)
                if std > 0 and val > mean + 3 * std:
                    anomalies.append({
                        "type": "high_latency",
                        "value": val,
                        "message": log["message"],
                        "service": log["service"]
                    })
            except:
                pass

    return anomalies


def detect_error_burst(parsed_logs):
    time_buckets = defaultdict(int)

    for log in parsed_logs:
        if log["level"] == "ERROR":
            ts = log["timestamp"][:16]  # minute bucket
            time_buckets[ts] += 1

    anomalies = []

    if not time_buckets:
        return anomalies

    values = list(time_buckets.values())
    mean = np.mean(values)
    std = np.std(values)

    for t, count in time_buckets.items():
        if std > 0 and count > mean + 2 * std:
            anomalies.append({
                "type": "error_burst",
                "time_window": t,
                "count": count
            })

    return anomalies


def detect_level_mismatch(parsed_logs):
    anomalies = []

    for log in parsed_logs:
        msg = log["message"].lower()
        level = log["level"]

        if "success" in msg and level == "ERROR":
            anomalies.append({
                "type": "level_mismatch",
                "message": log["message"],
                "level": level
            })

        if "fail" in msg and level == "INFO":
            anomalies.append({
                "type": "level_mismatch",
                "message": log["message"],
                "level": level
            })

    return anomalies