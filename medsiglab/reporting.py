from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config


CJK_PATTERN = re.compile(r"([\u3000-\u303f\uff00-\uffef\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+)")


def to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: to_builtin(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_builtin(item) for item in value]
    if isinstance(value, tuple):
        return [to_builtin(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_builtin(payload), handle, ensure_ascii=False, indent=2)


def save_table(
    df: pd.DataFrame,
    stem: str,
    index: bool = False,
    scale_to_width: bool = True,
    font_size: str = "footnotesize",
    tabcolsep_pt: int = 4,
    na_rep: str = "--",
) -> tuple[Path, Path]:
    csv_path = config.TABLES_DIR / f"{stem}.csv"
    tex_path = config.TABLES_DIR / f"{stem}.tex"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    export_df = df.copy()
    df.to_csv(csv_path, index=index, encoding="utf-8-sig", na_rep=na_rep)
    latex = export_df.to_latex(index=index, escape=False, na_rep=na_rep, float_format=lambda x: f"{x:.3f}")
    latex = apply_cjk_font(latex)
    if scale_to_width:
        latex = (
            r"\begingroup" "\n"
            r"\centering" "\n"
            rf"\{font_size}" "\n"
            rf"\setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}" "\n"
            r"\resizebox{\linewidth}{!}{%" "\n"
            f"{latex}"
            r"}" "\n"
            r"\endgroup" "\n"
        )
    tex_path.write_text(latex, encoding="utf-8")
    return csv_path, tex_path


def format_float(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def latex_escape(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def apply_cjk_font(text: str) -> str:
    return CJK_PATTERN.sub(r"{\\zhfont \1}", text)


def paragraph(text: str) -> str:
    return text.strip() + "\n\n"


def qa_block(title: str, items: list[tuple[str, str]]) -> str:
    lines = [rf"\subsubsection*{{{title}}}", r"\begin{enumerate}[leftmargin=2em]"]
    for question, answer in items:
        lines.append(rf"\item \textbf{{{latex_escape(question)}}}\par \hspace*{{2em}} {answer}")
    lines.append(r"\end{enumerate}")
    return "\n".join(lines) + "\n"


def figure_block(caption: str, path: str, width: str = "0.95\\linewidth", numbered: bool = True) -> str:
    caption_cmd = r"\caption" if numbered else r"\caption*"
    return (
        r"\begin{figure}[H]" "\n"
        r"\centering" "\n"
        rf"\includegraphics[width={width}]{{{path}}}" "\n"
        rf"{caption_cmd}{{{caption}}}" "\n"
        r"\end{figure}" "\n"
    )


def _pdf_page_count(path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"Unable to determine page count for {path}")


def extract_pdf_page(input_pdf: Path, page_number: int, output_pdf: Path) -> Path:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temp_pattern = output_pdf.with_name(f"{output_pdf.stem}-%d.pdf")
    subprocess.run(
        [
            "pdfseparate",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(input_pdf),
            str(temp_pattern),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    separated_pdf = output_pdf.with_name(f"{output_pdf.stem}-{page_number}.pdf")
    shutil.move(str(separated_pdf), str(output_pdf))
    return output_pdf


def compile_report() -> Path:
    config.REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    compile_cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        str(config.REPORT_MAIN_TEX),
    ]
    for _ in range(2):
        subprocess.run(compile_cmd, cwd=config.ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    generated_pdf = config.ROOT / "main.pdf"
    shutil.copyfile(generated_pdf, config.REPORT_PDF)
    generated_log = config.ROOT / "main.log"
    if generated_log.exists():
        shutil.copyfile(generated_log, config.REPORT_OUTPUT_DIR / "main.log")
    last_page = _pdf_page_count(config.REPORT_PDF)
    extract_pdf_page(config.REPORT_PDF, last_page, config.SUMMARY_PDF)
    return config.REPORT_PDF
