"""
tts.py - Phase 2

Turns each scene's text into a Vietnamese voice clip using edge-tts
(free, no API key, no local GPU - calls Microsoft Edge's neural TTS
service over the internet; Kaggle's "Internet: On" setting covers this).

Per spec: the LLM never estimates spoken duration. Each scene's audio is
generated first, its REAL duration is measured with ffprobe, and that
measured value overwrites the scene's "duration" field - audio is the
single source of truth for timing.
"""

import subprocess
from pathlib import Path

import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_AUDIO_DIR = BASE_DIR / "generated" / "audio"

# Free Vietnamese neural voices available via edge-tts:
#   vi-VN-HoaiMyNeural  (female)
#   vi-VN-NamMinhNeural (male)
DEFAULT_VOICE = "vi-VN-HoaiMyNeural"


def get_audio_duration(path: Path) -> float:
    """Exact duration in seconds via ffprobe (never estimated)."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def synthesize_scene_audio(text: str, out_path: Path, voice: str = DEFAULT_VOICE) -> float:
    """Generate one TTS mp3 for a scene's text, return its real duration (seconds)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    return get_audio_duration(out_path)


async def synthesize_all_scenes(scene_json: dict, run_id: str, voice: str = DEFAULT_VOICE) -> dict:
    """
    Generates one mp3 per scene (in generated/audio/<run_id>/scene_NN.mp3),
    overwrites each scene's 'duration' with the real measured value, and
    returns the updated scene_json plus the ordered list of audio paths.
    """
    run_audio_dir = GENERATED_AUDIO_DIR / run_id
    audio_paths = []

    for i, scene in enumerate(scene_json["scenes"]):
        out_path = run_audio_dir / f"scene_{i:02d}.mp3"
        duration = await synthesize_scene_audio(scene["text"], out_path, voice)
        scene["duration"] = round(duration, 3)
        audio_paths.append(out_path)

    return {"scene_json": scene_json, "audio_paths": audio_paths}


def concat_audio(audio_paths: list, run_id: str) -> Path:
    """Concatenate per-scene mp3s (in scene order) into one narration track."""
    run_audio_dir = GENERATED_AUDIO_DIR / run_id
    concat_list_path = run_audio_dir / "concat_list.txt"
    concat_list_path.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in audio_paths),
        encoding="utf-8",
    )
    final_audio_path = run_audio_dir / "narration.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list_path),
            "-c", "copy",
            str(final_audio_path),
        ],
        check=True, capture_output=True,
    )
    return final_audio_path