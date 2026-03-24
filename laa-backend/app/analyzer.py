from app.analysis_utils.cluster_anomaly import detect_cluster_anomalies
from app.analysis_utils.log_anomaly import (
    detect_latency_anomalies,
    detect_error_burst,
    detect_level_mismatch,
)
from app.analysis_utils.user_anomaly import detect_user_anomalies
from app.analysis_utils.sequence_anomaly import detect_sequence_anomalies
from app.analysis_utils.system_anomaly import detect_system_anomalies
from app.analysis_utils.stats import compute_stats


def analyze_clusters(clusters, parsed_logs):
    # ---------- STATS ----------
    stats = compute_stats(clusters, parsed_logs)

    # ---------- CLUSTER LEVEL ----------
    cluster_anomalies = detect_cluster_anomalies(clusters)

    # ---------- LOG LEVEL ----------
    latency_anomalies = detect_latency_anomalies(parsed_logs)
    error_burst = detect_error_burst(parsed_logs)
    mismatch = detect_level_mismatch(parsed_logs)

    # ---------- USER LEVEL ----------
    user_anomalies = detect_user_anomalies(parsed_logs)

    # ---------- SEQUENCE ----------
    sequence_anomalies = detect_sequence_anomalies(parsed_logs)

    # ---------- SYSTEM ----------
    system_anomalies = detect_system_anomalies(parsed_logs)

    anomalies = {
        "cluster_level": cluster_anomalies,
        "log_level": latency_anomalies + error_burst + mismatch,
        "user_level": user_anomalies,
        "sequence_level": sequence_anomalies,
        "system_level": system_anomalies,
    }

    return stats, anomalies