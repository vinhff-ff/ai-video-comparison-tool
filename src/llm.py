"""
llm.py - Phase 3

Thin wrapper around llama-cpp-python for running an instruct GGUF model
(Qwen2.5-7B-Instruct Q4_K_M by default) locally on Kaggle's free GPU.

The model is lazy-loaded on first use and cached for the rest of the run.
LLM replies are parsed tolerantly for JSON (strips markdown fences, finds the
first balanced {…} or […] block), so stray wording from the 7B model won't
break downstream parsing.
"""

import json
import re
from pathlib import Path
from urllib.request import urlopen

from huggingface_hub import hf_hub_download

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "Qwen/Qwen2.5-7B-Instruct-GGUF"
DEFAULT_FILE = None  # None → auto-discover the q4_k_m file(s) via the HF API
DEFAULT_MODEL_DIR = BASE_DIR / "models"

_MODEL = None  # cache the loaded Llama instance


def _repo_files(repo: str) -> list:
    with urlopen(f"https://huggingface.co/api/models/{repo}/tree/main", timeout=30) as r:
        return json.load(r)


def _pick_q4km(files: list) -> list:
    """Return the q4_k_m file path(s): a single-file quant, or all parts of a split."""
    q4 = [f for f in files if "q4_k_m" in f.get("path", "").lower()]
    if not q4:
        raise ValueError(f"No q4_k_m GGUF found in repo (files: {[f['path'] for f in files]})")
    singles = [f for f in q4 if "-of-" not in f["path"]]
    group = sorted(singles or q4, key=lambda f: f["path"])
    return [f["path"] for f in group]


def ensure_model(
    repo: str = DEFAULT_REPO,
    filename: str = None,
    local_dir=None,
) -> str:
    """Download the model (single q4_k_m, or every part of a split GGUF) if missing.

    Returns the path to pass to llama.cpp. For split GGUFs that's the first
    part (00001-of-00002); llama.cpp auto-joins the rest from the same folder.
    """
    local_dir = Path(local_dir or DEFAULT_MODEL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        files = [filename]
    else:
        print(f"[llm] Finding q4_k_m files in {repo} …")
        files = _pick_q4km(_repo_files(repo))

    target = None
    for name in files:
        local_file = local_dir / name
        if not local_file.exists():
            print(f"[llm] Downloading {repo}/{name} …")
            hf_hub_download(repo_id=repo, filename=name, local_dir=str(local_dir))
        target = local_file
    return str(target)


def get_model(model_path: str = None, n_ctx: int = 8192, n_gpu_layers: int = -1):
    """Lazy singleton: load the Llama model once, reuse for all calls."""
    global _MODEL
    if _MODEL is None:
        path = ensure_model() if not model_path else str(Path(model_path).resolve())
        from llama_cpp import Llama

        print(f"[llm] Loading model {path} …")
        _MODEL = Llama(
            model_path=path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,  # -1 = all layers on GPU (Kaggle T4/P100)
            verbose=False,
        )
    return _MODEL


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_ch:
                depth += 1
            elif text[i] == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    raise ValueError(f"Cannot parse JSON from LLM output:\n{text[:500]}")


def generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    model_path: str = None,
):
    """Chat completion that returns parsed JSON (tolerant parsing)."""
    llm = get_model(model_path)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    out = llm.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    reply = out["choices"][0]["message"]["content"]
    return _extract_json(reply)