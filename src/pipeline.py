"""
pipeline.py - Phase 1 MVP

Scene JSON (hand-written, no AI yet) -> render_html -> record_html -> ffmpeg -> final.mp4

Run from the project root in a Kaggle notebook cell:

    import sys
    sys.path.insert(0, "src")
    from pipeline import generate_video_phase1
    import asyncio

    assets = {
        "background": "assets/background.png",
        "character": "assets/character.png",
        "image_a": "assets/A.jpg",
        "image_b": "assets/B.jpg",
    }
    result = await generate_video_phase1(
        scene_json_path="generated/scripts/example_scene.json",
        assets=assets,
        run_id="test_run_001",
    )
    print("DONE:", result)

(Use `await generate_video_phase1(...)` directly in a notebook cell -
Jupyter/Kaggle cells support top-level await. Only use asyncio.run(...)
when running this file as a plain `python pipeline.py` script, not inside
a notebook.)
"""

import json
import subprocess
from pathlib import Path

from renderer import render_html
from recorder import record_html

BASE_DIR = Path(__file__).resolve().parent.parent


def load_scene_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def convert_to_mp4(webm_path: Path, run_id: str) -> Path:
    mp4_path = webm_path.with_suffix(".mp4")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(webm_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(mp4_path),
        ],
        check=True,
        capture_output=True,
    )
    return mp4_path


async def generate_video_phase1(scene_json_path: str, assets: dict, run_id: str) -> Path:
    scene_json = load_scene_json(scene_json_path)

    html_path = render_html(scene_json, assets, run_id)
    print(f"[pipeline] HTML rendered: {html_path}")

    webm_path = await record_html(html_path, run_id)
    print(f"[pipeline] Video recorded: {webm_path}")

    mp4_path = convert_to_mp4(webm_path, run_id)
    print(f"[pipeline] Final MP4: {mp4_path}")

    return mp4_path


if __name__ == "__main__":
    import asyncio

    assets = {
        "background": str(BASE_DIR / "assets" / "background.png"),
        "character": str(BASE_DIR / "assets" / "character.png"),
        "image_a": str(BASE_DIR / "assets" / "A.jpg"),
        "image_b": str(BASE_DIR / "assets" / "B.jpg"),
    }
    result = asyncio.run(
        generate_video_phase1(
            scene_json_path=str(BASE_DIR / "generated" / "scripts" / "example_scene.json"),
            assets=assets,
            run_id="test_run_001",
        )
    )
    print("DONE:", result)