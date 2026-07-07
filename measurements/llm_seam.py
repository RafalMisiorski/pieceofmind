"""Bring-your-own-model seam for the measurement scripts (mirrors sealeval's judge_fn design).

Set PIECEOFMIND_LLM_CMD to any command that reads the prompt on STDIN and prints the model's
reply to STDOUT, e.g.:

    # OpenAI CLI-style tool, an Ollama call, or your own 5-line wrapper:
    set PIECEOFMIND_LLM_CMD=python my_model.py          (Windows)
    export PIECEOFMIND_LLM_CMD="python my_model.py"     (POSIX)

    # my_model.py -- example with the Anthropic SDK:
    #   import sys, anthropic
    #   r = anthropic.Anthropic().messages.create(model="claude-haiku-4-5-20251001",
    #       max_tokens=400, messages=[{"role":"user","content":sys.stdin.read()}])
    #   print(r.content[0].text)

Or import make_llm() and monkeypatch -- the scripts only need `llm(prompt) -> str`.
"""
from __future__ import annotations

import os
import shlex
import subprocess


def make_llm():
    cmd = os.environ.get("PIECEOFMIND_LLM_CMD", "").strip()
    if not cmd:
        raise SystemExit(
            "Set PIECEOFMIND_LLM_CMD to a command that reads the prompt on stdin and prints "
            "the model reply (see measurements/llm_seam.py header for a 5-line example)."
        )

    def llm(prompt: str) -> str:
        r = subprocess.run(shlex.split(cmd), input=prompt, capture_output=True,
                           text=True, encoding="utf-8", timeout=300)
        return r.stdout or ""

    return llm
