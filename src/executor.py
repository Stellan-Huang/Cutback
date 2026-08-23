"""Execution engine for Cutback."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from src.models import EditAction


def delete_range(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
) -> None:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if start_time < 0:
        raise ValueError(f"start_time must be >= 0, got {start_time}")
    if end_time <= start_time:
        raise ValueError(
            f"end_time must be > start_time, got start_time={start_time}, end_time={end_time}"
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        f"[0:v]trim=start=0:end={start_time},setpts=PTS-STARTPTS[v0];"
        f"[0:a]atrim=start=0:end={start_time},asetpts=PTS-STARTPTS[a0];"
        f"[0:v]trim=start={end_time},setpts=PTS-STARTPTS[v1];"
        f"[0:a]atrim=start={end_time},asetpts=PTS-STARTPTS[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed with exit code {result.returncode}:\n{result.stderr}"
        )


def execute_action(action: EditAction, input_path: str, output_path: str) -> None:
    if action.action == "DELETE_RANGE":
        delete_range(input_path, output_path, action.start_time, action.end_time)
        return
    raise ValueError(f"Unsupported action: {action.action}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    payload = json.loads((root / "action.json").read_text(encoding="utf-8"))
    action = EditAction.model_validate(payload)
    execute_action(
        action,
        str(root / "data" / "demo.mp4"),
        str(root / "outputs" / "python_delete_10_20.mp4"),
    )
    print("Wrote outputs/python_delete_10_20.mp4")
