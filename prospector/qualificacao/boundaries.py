from __future__ import annotations
import subprocess
import urllib.request


def chamar_claude(prompt: str, timeout: int = 120) -> str:
    r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p falhou: {r.stderr[:400]}")
    return r.stdout


def buscar_site(url: str, timeout: int = 20) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 prospector"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception:
        return ""
