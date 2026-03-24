from collections import defaultdict


def detect_user_anomalies(parsed_logs):
    user_activity = defaultdict(int)
    user_failures = defaultdict(int)

    for log in parsed_logs:
        user = log.get("metadata", {}).get("user")
        if not user:
            continue

        user_activity[user] += 1

        if "fail" in log["message"].lower() or log["level"] == "ERROR":
            user_failures[user] += 1

    anomalies = []

    for user, count in user_activity.items():
        if count > 20:
            anomalies.append({
                "type": "high_user_activity",
                "user": user,
                "count": count
            })

    for user, count in user_failures.items():
        if count > 5:
            anomalies.append({
                "type": "repeated_failures",
                "user": user,
                "failures": count
            })

    return anomalies