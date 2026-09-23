from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT = Path("tests/fpga/benchmark/data/remote_task_benchmark.csv")
OUTPUT_DIR = Path("tests/fpga/benchmark/results")

EXPECTED_RUNS = 50

COLUMNS = [
    "task",
    "configuration",
    "need_ack",
    "need_checksum",
    "iteration",
    "remote_time_ns",
    "remote_time_us",
    "core_time_us",
    "overhead_us",
]

TASK_ORDER = [
    "fpga_power_on",
    "echo",
    "predict",
    "write_to_flash",
    "read_skeleton_id",
]

CONFIG_ORDER = [
    "none",
    "ack",
    "checksum",
    "ack+checksum",
]


def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT)

    missing_columns = [column for column in COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing columns in CSV: {', '.join(missing_columns)}"
        )

    numeric_columns = [
        "iteration",
        "remote_time_ns",
        "remote_time_us",
        "core_time_us",
        "overhead_us",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["task"] = pd.Categorical(
        df["task"],
        categories=TASK_ORDER,
        ordered=True,
    )

    df["configuration"] = pd.Categorical(
        df["configuration"],
        categories=CONFIG_ORDER,
        ordered=True,
    )

    # A measurement is valid for core/overhead analysis only if:
    # - core time is positive
    # - core time does not exceed remote time
    # - overhead is non-negative
    # - all relevant values are finite
    df["valid_measurement"] = (
        df["remote_time_us"].gt(0)
        & df["core_time_us"].gt(0)
        & df["core_time_us"].le(df["remote_time_us"])
        & df["overhead_us"].ge(0)
        & df[
            [
                "remote_time_us",
                "core_time_us",
                "overhead_us",
            ]
        ]
        .apply(lambda column: column.map(pd.api.types.is_number))
        .all(axis=1)
    )

    return df


def print_run_counts(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("RUN COUNTS")
    print("=" * 80)

    counts = (
        df.groupby(
            ["task", "configuration"],
            observed=True,
        )
        .agg(runs=("iteration", "count"))
        .reset_index()
    )

    counts["missing"] = EXPECTED_RUNS - counts["runs"]

    print(
        counts.to_string(
            index=False,
        )
    )

    incomplete = counts[counts["runs"] < EXPECTED_RUNS]

    print("\nIncomplete tests:")
    if incomplete.empty:
        print("None")
    else:
        print(
            incomplete[
                ["task", "configuration", "runs", "missing"]
            ].to_string(index=False)
        )

    total_expected = (
        len(TASK_ORDER)
        * len(CONFIG_ORDER)
        * EXPECTED_RUNS
    )

    total_actual = len(df)

    print(
        f"\nTotal measurements: {total_actual}/{total_expected}"
    )
    print(
        f"Missing measurements: {total_expected - total_actual}"
    )


def print_invalid_measurements(df: pd.DataFrame) -> None:
    invalid = df[~df["valid_measurement"]].copy()

    print("\n" + "=" * 80)
    print("INVALID MEASUREMENTS")
    print("=" * 80)

    if invalid.empty:
        print("None")
        return

    print(
        invalid[
            [
                "task",
                "configuration",
                "iteration",
                "remote_time_us",
                "core_time_us",
                "overhead_us",
            ]
        ].to_string(index=False)
    )

    print(f"\nInvalid measurements: {len(invalid)}")


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    valid = df[df["valid_measurement"]].copy()

    summary = (
        valid.groupby(
            ["task", "configuration"],
            observed=True,
        )
        .agg(
            valid_runs=("iteration", "count"),
            remote_mean_us=("remote_time_us", "mean"),
            remote_median_us=("remote_time_us", "median"),
            remote_std_us=("remote_time_us", "std"),
            remote_p95_us=(
                "remote_time_us",
                lambda x: x.quantile(0.95),
            ),
            core_mean_us=("core_time_us", "mean"),
            core_median_us=("core_time_us", "median"),
            core_std_us=("core_time_us", "std"),
            overhead_mean_us=("overhead_us", "mean"),
            overhead_median_us=("overhead_us", "median"),
            overhead_std_us=("overhead_us", "std"),
        )
        .reset_index()
    )

    summary["overhead_percentage"] = (
        summary["overhead_median_us"]
        / summary["remote_median_us"]
        * 100
    )

    summary["runs_missing"] = (
        EXPECTED_RUNS - summary["valid_runs"]
    )

    return summary


def make_label(row: pd.Series) -> str:
    return f"{row['task']}\n{row['configuration']}"


def add_labels(frame: pd.DataFrame) -> list[str]:
    return [
        make_label(row)
        for _, row in frame.iterrows()
    ]


def plot_remote_median(summary: pd.DataFrame) -> None:
    data = summary.sort_values(
        ["task", "configuration"]
    )

    labels = add_labels(data)

    plt.figure(figsize=(15, 7))

    plt.bar(
        labels,
        data["remote_median_us"],
    )

    # Logarithmic scale makes millisecond tasks and
    # multi-second flash operations simultaneously visible.
    plt.yscale("log")

    plt.ylabel("Median remote time [µs]")
    plt.xlabel("Task / configuration")
    plt.title("Median remote execution time")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "remote_execution_median_log.png",
        dpi=300,
    )
    plt.close()


def plot_core_vs_overhead(summary: pd.DataFrame) -> None:
    data = summary.sort_values(
        ["task", "configuration"]
    )

    labels = add_labels(data)
    x = range(len(data))

    width = 0.38

    plt.figure(figsize=(16, 7))

    plt.bar(
        [i - width / 2 for i in x],
        data["core_median_us"],
        width=width,
        label="Core execution",
    )

    plt.bar(
        [i + width / 2 for i in x],
        data["overhead_median_us"],
        width=width,
        label="Remote overhead",
    )

    plt.yscale("log")

    plt.ylabel("Median time [µs]")
    plt.xlabel("Task / configuration")
    plt.title("Core execution vs. remote overhead")
    plt.xticks(
        list(x),
        labels,
        rotation=45,
        ha="right",
    )
    plt.legend()

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "core_vs_overhead_median_log.png",
        dpi=300,
    )
    plt.close()


def plot_relative_overhead(summary: pd.DataFrame) -> None:
    data = summary.sort_values(
        ["task", "configuration"]
    )

    labels = add_labels(data)

    plt.figure(figsize=(15, 7))

    plt.bar(
        labels,
        data["overhead_percentage"],
    )

    plt.ylabel("Overhead [% of remote time]")
    plt.xlabel("Task / configuration")
    plt.title("Relative remote overhead")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "relative_overhead.png",
        dpi=300,
    )
    plt.close()


def plot_remote_distribution(df: pd.DataFrame) -> None:
    valid = df[df["valid_measurement"]].copy()

    groups = []

    for task in TASK_ORDER:
        for config in CONFIG_ORDER:
            group = valid[
                (valid["task"] == task)
                & (valid["configuration"] == config)
            ]

            if not group.empty:
                groups.append(
                    (
                        f"{task}\n{config}",
                        group["remote_time_us"],
                    )
                )

    labels = [group[0] for group in groups]
    values = [group[1] for group in groups]

    positions = range(1, len(values) + 1)

    plt.figure(figsize=(16, 8))

    plt.boxplot(
        values,
        positions=list(positions),
        tick_labels=labels,
        showfliers=True,
    )

    plt.yscale("log")

    plt.ylabel("Remote time [µs]")
    plt.xlabel("Task / configuration")
    plt.title("Distribution of remote execution times")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "remote_execution_distribution_log.png",
        dpi=300,
    )
    plt.close()


def save_summary(summary: pd.DataFrame) -> None:
    summary.to_csv(
        OUTPUT_DIR / "summary.csv",
        index=False,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_data()

    print_run_counts(df)
    print_invalid_measurements(df)

    summary = build_summary(df)

    print("\n" + "=" * 80)
    print("SUMMARY — VALID MEASUREMENTS")
    print("=" * 80)

    display_columns = [
        "task",
        "configuration",
        "valid_runs",
        "runs_missing",
        "remote_median_us",
        "remote_mean_us",
        "remote_p95_us",
        "core_median_us",
        "overhead_median_us",
        "overhead_percentage",
    ]

    print(
        summary[display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:,.2f}",
        )
    )

    save_summary(summary)

    plot_remote_median(summary)
    plot_core_vs_overhead(summary)
    plot_relative_overhead(summary)
    plot_remote_distribution(df)

    print("\nResults written to:")
    print(OUTPUT_DIR.resolve())


if __name__ == "__main__":
    main()