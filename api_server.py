"""
FastAPI wrapper around the optimizer.

Features
- Accepts layout as image/PDF (runs CV) or Excel/CSV (direct coordinates).
- Accepts companies as JSON list or uploaded Excel/CSV (first column).
- Returns optimizer JSON payload + stdout/stderr. Plot is base64 if produced.

Run locally:
  uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional

import pandas as pd
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Career Fair Optimizer API")


def parse_companies_from_file(upload: UploadFile) -> List[str]:
    data = upload.file.read()
    if not data:
        return []
    suffix = (upload.filename or "").lower()
    try:
        if suffix.endswith(".csv"):
            df = pd.read_csv(pd.io.common.BytesIO(data), header=0)
        else:
            df = pd.read_excel(pd.io.common.BytesIO(data), header=0)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read company file: {exc}")

    if df.empty:
        return []
    first_col = df.columns[0]
    names = []
    for val in df[first_col].tolist():
        if isinstance(val, str):
            val = val.strip()
        elif pd.isna(val):
            continue
        else:
            val = str(val)
        if val:
            names.append(val)
    return names


def write_temp_file(directory: Path, upload: UploadFile, name: Optional[str] = None) -> Path:
    target = directory / (name or upload.filename or "upload.bin")
    with target.open("wb") as f:
        f.write(upload.file.read())
    return target


async def run_command(cmd: List[str], cwd: Path) -> (int, str, str):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    return proc.returncode, stdout_b.decode(), stderr_b.decode()


def load_plot_base64(plot_path: Optional[Path]) -> Optional[str]:
    if not plot_path or not plot_path.exists():
        return None
    data = plot_path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/png;base64,{b64}"


@app.post("/optimize")
async def optimize(
    layout: UploadFile = File(...),
    companies: Optional[str] = Form(None, description="JSON list of companies"),
    companiesFile: Optional[UploadFile] = File(None, description="Excel/CSV with company names in first column"),
    max_companies: int = Form(200),
    invert: bool = Form(False),
    min_area: float = Form(400.0),
    max_area: float = Form(100000.0),
):
    # Parse companies list
    company_list: List[str] = []
    if companies:
        try:
            parsed = json.loads(companies)
            if not isinstance(parsed, list):
                raise ValueError("companies must be a JSON list")
            company_list = [str(x).strip() for x in parsed if str(x).strip()]
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid companies payload: {exc}")
    elif companiesFile:
        company_list = parse_companies_from_file(companiesFile)
    else:
        raise HTTPException(status_code=400, detail="Company list is required (JSON or file).")

    if not company_list:
        raise HTTPException(status_code=400, detail="No companies found in provided input.")

    # Prepare temp workspace
    temp_dir = Path(tempfile.mkdtemp(prefix="opt-api-"))
    plot_path = temp_dir / "plot.png"
    json_out = temp_dir / "result.json"

    try:
        layout_path = write_temp_file(temp_dir, layout)
        companies_json = temp_dir / "companies.json"
        companies_json.write_text(json.dumps(company_list), encoding="utf-8")

        is_spreadsheet = layout_path.suffix.lower() in [".xlsx", ".xls", ".csv"]
        cmd = (
            [
                "python3",
                "main.py",
                "--layout-file",
                str(layout_path),
                "--companies-json",
                str(companies_json),
                "--max-companies",
                str(max_companies),
                "--plot-file",
                str(plot_path),
                "--json-out",
                str(json_out),
            ]
            if is_spreadsheet
            else [
                "python3",
                "run_from_image.py",
                "--image",
                str(layout_path),
                "--companies-json",
                str(companies_json),
                "--max-companies",
                str(max_companies),
                "--plot-file",
                str(plot_path),
                "--json-out",
                str(json_out),
                "--min-area",
                str(min_area),
                "--max-area",
                str(max_area),
            ]
            + (["--invert"] if invert else [])
        )

        code, stdout, stderr = await run_command(cmd, ROOT)
        if code != 0:
            raise HTTPException(
                status_code=500,
                detail={"error": "Optimizer failed", "stdout": stdout, "stderr": stderr},
            )

        if not json_out.exists():
            raise HTTPException(status_code=500, detail="Optimizer did not produce JSON output.")

        payload = json.loads(json_out.read_text(encoding="utf-8"))
        plot_b64 = load_plot_base64(plot_path)
        payload["plot_b64"] = plot_b64

        return JSONResponse({"run": payload, "stdout": stdout, "stderr": stderr})
    finally:
        # Clean up temp files
        for item in temp_dir.glob("*"):
            try:
                item.unlink()
            except OSError:
                pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
