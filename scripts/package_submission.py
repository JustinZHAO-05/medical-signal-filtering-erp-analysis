from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from medsiglab import config


STUDENT_NAME = "赵彦喆"
STUDENT_ID = "3023006059"
PACKAGE_STEM = f"{STUDENT_NAME}-{STUDENT_ID}"


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_submission_bundle() -> tuple[Path, Path]:
    bundle_root = config.SUBMISSION_DIR / PACKAGE_STEM
    code_root = bundle_root / "code"
    zip_path = config.SUBMISSION_DIR / f"{PACKAGE_STEM}.zip"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    if zip_path.exists():
        zip_path.unlink()

    bundle_root.mkdir(parents=True, exist_ok=True)

    _copy_file(config.REPORT_PDF, bundle_root / "medical_signal_filter_report.pdf")
    _copy_file(config.SUMMARY_PDF, bundle_root / "summary.pdf")
    _copy_file(config.ROOT / "requirements.txt", code_root / "requirements.txt")

    for source in sorted((config.ROOT / "scripts").rglob("*.py")):
        _copy_file(source, code_root / source.relative_to(config.ROOT))
    for source in sorted((config.ROOT / "medsiglab").rglob("*.py")):
        _copy_file(source, code_root / source.relative_to(config.ROOT))

    shutil.make_archive(str(config.SUBMISSION_DIR / PACKAGE_STEM), "zip", root_dir=config.SUBMISSION_DIR, base_dir=PACKAGE_STEM)
    return bundle_root, zip_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Package the final submission bundle.")
    parser.parse_args(argv)
    bundle_root, zip_path = build_submission_bundle()
    print(
        json.dumps(
            {
                "submission_dir": str(bundle_root),
                "submission_zip": str(zip_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
