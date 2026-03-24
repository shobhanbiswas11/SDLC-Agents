import numpy as np


def compute_stats(clusters, parsed_logs):
    counts = [c["count"] for c in clusters]

    total_logs = len(parsed_logs)
    total_clusters = len(clusters)

    mean = float(np.mean(counts)) if counts else 0
    std = float(np.std(counts)) if counts else 0

    return {
        "total_logs": total_logs,
        "total_clusters": total_clusters,
        "mean_cluster_size": mean,
        "std_cluster_size": std,
        "max_cluster_size": max(counts) if counts else 0,
        "min_cluster_size": min(counts) if counts else 0,
    }