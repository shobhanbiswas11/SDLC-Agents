import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from app.parser import parse_logs
from app.cluster import cluster_logs
from app.analyzer import analyze_clusters
from app.llm import generate_summary

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    logs = content.decode("utf-8").splitlines()

    # Step 1: Parse
    parsed_logs = parse_logs(logs)

    # Persist parsed output (for debugging / inspection)
    output_dir = Path(__file__).resolve().parents[1] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "parser.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-----------------------------------\n")
        json.dump(parsed_logs, f, indent=2, ensure_ascii=False)
        f.write("\n-----------------------------------\n")

    # Step 2: Cluster
    clusters = cluster_logs(parsed_logs)

    output_file = output_dir / "cluster.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-----------------------------------\n")
        json.dump(clusters, f, indent=2, ensure_ascii=False)
        f.write("\n-----------------------------------\n")


    # Step 3: Analyze
    # stats, anomalies = analyze_clusters(clusters)
    stats, anomalies = analyze_clusters(clusters, parsed_logs)
    
    output_file = output_dir / "stats.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-----------------------------------\n")
        json.dump(stats, f, indent=2, ensure_ascii=False)
        f.write("\n-----------------------------------\n")

    output_file = output_dir / "anomalies.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-----------------------------------\n")
        json.dump(anomalies, f, indent=2, ensure_ascii=False)
        f.write("\n-----------------------------------\n")

    # Step 4: LLM Summary
    summary = generate_summary(anomalies, clusters, stats)

    output_file = output_dir / "summary.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-----------------------------------\n")
        # json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write(summary)
        f.write("\n-----------------------------------\n")    

    return {
        "anomalies": anomalies,
        "clusters": clusters[:10],  # top clusters
        "statistics": stats,
        "llm_summary": summary
    }
