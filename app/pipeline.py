"""Run the numbered pipeline scripts as functions, with per-step progress and captured logs."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STEPS = ["00_fetch", "01_inventory", "02_qa_parcels", "03_measure", "04_overlay", "05_maps",
         "06_terrain", "07_site_evaluation", "08_report"]
PDF_STEP = "09_pdf_atlas"
_lock = threading.Lock()   # the scripts read PROPERTY_CONFIG from the environment: one run at a time


def _load(step: str):
    spec = importlib.util.spec_from_file_location(f"step_{step}", SCRIPTS / f"{step}.py")
    mod = importlib.util.module_from_spec(spec)
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(mod)
    return mod


def run_step(step: str, config_path: Path, log) -> None:
    """Run one script's main() with PROPERTY_CONFIG set, streaming its stdout to `log(line)`."""
    buf = io.StringIO()

    class Tee(io.TextIOBase):
        def write(self, s):
            buf.write(s)
            for line in s.splitlines():
                if line.strip():
                    log(line)
            return len(s)

    old = os.environ.get("PROPERTY_CONFIG")
    os.environ["PROPERTY_CONFIG"] = str(config_path)
    try:
        with contextlib.redirect_stdout(Tee()), contextlib.redirect_stderr(Tee()):
            mod = _load(step)
            saved_argv = sys.argv
            sys.argv = [step]
            try:
                mod.main()
            finally:
                sys.argv = saved_argv
    finally:
        if old is None:
            os.environ.pop("PROPERTY_CONFIG", None)
        else:
            os.environ["PROPERTY_CONFIG"] = old


def run_listing(config_path: Path, progress, log, pdf: bool = False, steps=None) -> None:
    """progress(step_name, index, total) before each step; log(line) for output lines."""
    todo = list(steps or STEPS) + ([PDF_STEP] if pdf else [])
    with _lock:
        for i, step in enumerate(todo):
            progress(step, i, len(todo))
            run_step(step, config_path, log)
        progress("done", len(todo), len(todo))
