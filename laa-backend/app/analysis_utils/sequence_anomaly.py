def detect_sequence_anomalies(parsed_logs):
    anomalies = []

    for log in parsed_logs:
        msg = log["message"].lower()

        if "unexpected" in msg:
            anomalies.append({
                "type": "sequence_violation",
                "message": log["message"],
                "service": log["service"]
            })

    return anomalies