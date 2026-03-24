import numpy as np


def detect_cluster_anomalies(clusters):
    anomalies = []

    counts = [c["count"] for c in clusters]
    if not counts:
        return anomalies

    mean = np.mean(counts)
    std = np.std(counts)

    # SPIKE
    for c in clusters:
        if std > 0:
            z = (c["count"] - mean) / std
            if z > 2:
                anomalies.append({
                    "type": "spike",
                    "template": c["template"],
                    "count": c["count"],
                    "z_score": float(z)
                })

    # RARE
    for c in clusters:
        if c["count"] <= 2 and c["type"] != "noise":
            anomalies.append({
                "type": "rare_cluster",
                "template": c["template"],
                "count": c["count"]
            })

    return anomalies