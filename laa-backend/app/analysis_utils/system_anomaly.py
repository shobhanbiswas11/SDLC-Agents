from collections import defaultdict


def detect_system_anomalies(parsed_logs):
    time_service_errors = defaultdict(set)

    for log in parsed_logs:
        if log["level"] == "ERROR":
            time_key = log["timestamp"][:16]
            time_service_errors[time_key].add(log["service"])

    anomalies = []

    for t, services in time_service_errors.items():
        if len(services) >= 3:
            anomalies.append({
                "type": "system_wide_failure",
                "time": t,
                "affected_services": list(services)
            })

    return anomalies