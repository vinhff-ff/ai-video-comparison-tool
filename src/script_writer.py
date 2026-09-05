"""
script_writer.py - Phase 3 (step 2)

Takes the research brief from researcher.py and uses the LLM to write a
6-line Vietnamese script — funny, sarcastic, trait-driven — that becomes the
video's narration. Returns a list of exactly 6 strings.
"""

import asyncio
from pathlib import Path

from llm import generate_json

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PROMPT = (BASE_DIR / "prompts" / "script_writer.txt").read_text(encoding="utf-8")


def write_script(brief: dict, style: str = "hài hước, châm biếm", model_path: str = None) -> list:
    """Generate 6 TikTok-style Vietnamese lines for the A-vs-B video."""
    user = (
        f"PHONG CÁCH: {style}\n"
        f"TOPIC_A = {brief['topic_a']}\n"
        f"TOPIC_B = {brief['topic_b']}"
    )
    lines = generate_json(SCRIPT_PROMPT, user, temperature=0.8, max_tokens=1024,
                          model_path=model_path)
    if not isinstance(lines, list) or len(lines) != 6:
        # Tolerant retry: split on newlines if the model ignored the JSON shape
        if isinstance(lines, str):
            lines = [ln.strip() for ln in lines.splitlines() if ln.strip()]
        if len(lines) != 6:
            raise ValueError(f"Script writer returned {len(lines)} lines, expected 6")
    script = []
    for i, ln in enumerate(lines):
        script.append(str(ln).strip().strip('"'))
    return script


async def write_script_async(brief: dict, style: str = "hài hước, châm biếm",
                             model_path: str = None) -> list:
    return await asyncio.to_thread(write_script, brief, style, model_path)