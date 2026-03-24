import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer


ANOMALY_KEYWORDS = {
    "error", "failed", "failure", "unexpected",
    "timeout", "denied", "exception", "critical"
}


def contains_anomaly_word(text):
    text = text.lower()
    return any(word in text for word in ANOMALY_KEYWORDS)


def run_dbscan(messages, logs):
    if not messages:
        return {}

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        token_pattern=r'\b\w+\b'
    )

    vectors = vectorizer.fit_transform(messages).toarray()

    clustering = DBSCAN(
        eps=0.5,
        min_samples=2,
        metric="cosine"
    ).fit(vectors)

    clusters = defaultdict(list)

    for log, label in zip(logs, clustering.labels_):
        clusters[label].append(log)

    return clusters


def cluster_logs(parsed_logs):
    if not parsed_logs:
        return []

    # Split logs into anomaly vs normal
    normal_logs = []
    anomaly_logs = []

    for log in parsed_logs:
        if contains_anomaly_word(log["message"]):
            anomaly_logs.append(log)
        else:
            normal_logs.append(log)

    # Run clustering separately
    normal_clusters = run_dbscan(
        [log["message"] for log in normal_logs],
        normal_logs
    )

    anomaly_clusters = run_dbscan(
        [log["message"] for log in anomaly_logs],
        anomaly_logs
    )

    # Merge results
    all_clusters = {**normal_clusters, **{
        f"a_{k}": v for k, v in anomaly_clusters.items()
    }}

    result = []

    for label, logs in all_clusters.items():
        if label == -1:
            result.append({
                "template": "NOISE / UNIQUE EVENTS",
                "count": len(logs),
                "examples": logs[:2],
                "type": "noise"
            })
        else:
            result.append({
                "template": logs[0]["message"],
                "count": len(logs),
                "examples": logs[:2],
                "type": "semantic_cluster"
            })

    result.sort(key=lambda x: x["count"], reverse=True)
    
    # for r in result:
    #     print(r["template"])

    return result