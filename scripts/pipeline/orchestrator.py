from __future__ import annotations

import json

from medsiglab import config, io_utils, plotting, reporting
from scripts.pipeline import figures, part1, part2, report_builder, shared


def run_full_pipeline() -> tuple[dict, str]:
    io_utils.ensure_output_dirs()
    plotting.setup_style()

    dataset = io_utils.load_sub7a_dataset()
    data_summary, data_df = shared.build_data_summary(dataset)
    reporting.save_table(data_df, "data-summary")

    part1_metrics, part1_artifacts = part1.run_suite(dataset=dataset, experiment="all")
    part2_metrics, part2_artifacts = part2.run_suite(dataset=dataset, experiment="all")

    summary_figure = figures.build_clinical_summary_figure(
        exp1_artifacts=part1_artifacts["exp1"],
        exp2_artifacts=part1_artifacts["exp2"],
        exp4_artifacts=part1_artifacts["exp4"],
        exp23_artifacts=part2_artifacts["exp3"],
        exp1_metrics=part1_metrics["exp1"],
        exp2_metrics=part1_metrics["exp2"],
        exp4_metrics=part1_metrics["exp4"],
        exp23_metrics=part2_metrics["exp3"],
    )
    metrics = {
        "data": data_summary,
        "part1": part1_metrics,
        "part2": part2_metrics,
        "summary_figure": summary_figure,
    }
    shared.save_metrics_json(metrics)
    pdf_path = report_builder.write_report(metrics)
    return metrics, str(pdf_path)


def main() -> None:
    _, pdf_path = run_full_pipeline()
    print(
        json.dumps(
            {
                "report_pdf": pdf_path,
                "metrics_json": str(config.REPORT_OUTPUT_DIR / "metrics.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
