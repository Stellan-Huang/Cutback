"""Execution engine for Cutback."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from src.models import EditAction

def _get_duration(input_path: str) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        input_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    return float(data["format"]["duration"])

def move_range(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    destination_time: float,
) -> None:
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"输入视频不存在：{input_path}")

    if start_time < 0:
        raise ValueError("start_time 不能小于 0")

    if end_time <= start_time:
        raise ValueError("end_time 必须大于 start_time")

    if destination_time < 0:
        raise ValueError("destination_time 不能小于 0")

    duration = _get_duration(input_path)

    if end_time > duration:
        raise ValueError("end_time 超出视频时长")

    if destination_time > duration:
        raise ValueError("destination_time 超出视频时长")

    if start_time <= destination_time <= end_time:
        raise ValueError("目标位置不能位于被移动片段内部")

    # 根据移动方向重新排列原视频片段
    if destination_time < start_time:
        segments = [
            (0, destination_time),
            (start_time, end_time),
            (destination_time, start_time),
            (end_time, duration),
        ]
    else:
        segments = [
            (0, start_time),
            (end_time, destination_time),
            (start_time, end_time),
            (destination_time, duration),
        ]

    # 删除长度为 0 的片段，例如 destination_time = 0
    segments = [
        (start, end)
        for start, end in segments
        if end - start > 0.001
    ]

    filters = []
    concat_inputs = []

    for index, (start, end) in enumerate(segments):
        filters.append(
            f"[0:v]trim=start={start}:end={end},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )

        filters.append(
            f"[0:a]atrim=start={start}:end={end},"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )

        concat_inputs.append(f"[v{index}][a{index}]")

    filter_complex = (
        ";".join(filters)
        + ";"
        + "".join(concat_inputs)
        + f"concat=n={len(segments)}:v=1:a=1[v][a]"
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
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

    subprocess.run(
        command,
        check=True,
    )


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
    elif action.action == "MOVE_RANGE":
        move_range(
            input_path=input_path,
            output_path=output_path,
            start_time=action.start_time,
            end_time=action.end_time,
            destination_time=action.destination_time,
        )
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
