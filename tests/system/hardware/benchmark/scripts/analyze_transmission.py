from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = SCRIPT_DIR.parent
RESULTS_DIR = BENCHMARK_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT = BENCHMARK_DIR / "data" / "transmission_benchmark.csv"

CONFIG_ORDER = [
    "none",
    "ack",
    "checksum",
    "ack+checksum",
]

CONFIG_LABELS = {
    "none": "None",
    "ack": "ACK",
    "checksum": "Checksum",
    "ack+checksum": "ACK + checksum",
}


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

df = pd.read_csv(INPUT)

df["configuration"] = pd.Categorical(
    df["configuration"],
    categories=CONFIG_ORDER,
    ordered=True,
)

df["latency_ms"] = df["time_ns"] / 1e6

df["throughput_kib_s"] = df["payload_size"] / (df["time_ns"] / 1e9) / 1024


# ---------------------------------------------------------------------
# Latency summary
# ---------------------------------------------------------------------

latency_summary = (
    df.groupby(
        ["configuration", "payload_size"],
        observed=True,
    )["latency_ms"]
    .agg(
        mean="mean",
        median="median",
        std="std",
        p95=lambda x: x.quantile(0.95),
        p99=lambda x: x.quantile(0.99),
        min="min",
        max="max",
    )
    .reset_index()
)

print("\nLatency summary:")
print(latency_summary.to_string(index=False))

latency_summary.to_csv(
    RESULTS_DIR / "transmission_latency_summary.csv",
    index=False,
)


# ---------------------------------------------------------------------
# Latency plot
# ---------------------------------------------------------------------

plt.figure(figsize=(8, 5))

for configuration, group in latency_summary.groupby(
    "configuration",
    observed=True,
):
    plt.plot(
        group["payload_size"],
        group["median"],
        marker="o",
        label=CONFIG_LABELS[configuration],
    )

plt.xlabel("Payload size [bytes]")
plt.ylabel("Median latency [ms]")
plt.title("Transmission latency vs. payload size")
plt.xticks(sorted(df["payload_size"].unique()))
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "latency_vs_payload.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()


# ---------------------------------------------------------------------
# Throughput summary
# ---------------------------------------------------------------------

throughput_summary = (
    df.groupby(
        ["configuration", "payload_size"],
        observed=True,
    )["throughput_kib_s"]
    .agg(
        mean="mean",
        median="median",
        std="std",
        p95=lambda x: x.quantile(0.95),
        p99=lambda x: x.quantile(0.99),
        min="min",
        max="max",
    )
    .reset_index()
)

print("\nThroughput summary:")
print(throughput_summary.to_string(index=False))

throughput_summary.to_csv(
    RESULTS_DIR / "transmission_throughput_summary.csv",
    index=False,
)


# ---------------------------------------------------------------------
# Throughput plot
# ---------------------------------------------------------------------

plt.figure(figsize=(8, 5))

for configuration, group in throughput_summary.groupby(
    "configuration",
    observed=True,
):
    plt.plot(
        group["payload_size"],
        group["median"],
        marker="o",
        label=CONFIG_LABELS[configuration],
    )

plt.xlabel("Payload size [bytes]")
plt.ylabel("Median throughput [KiB/s]")
plt.title("Effective throughput vs. payload size")
plt.xticks(sorted(df["payload_size"].unique()))
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "throughput_vs_payload.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()
