from __future__ import annotations
import os
import subprocess
from prospector.modelos import Lead

_PROMPT = """Redesenhe o site do negócio '{nome}' (nicho {nicho}) como uma landing premium,
mantendo logo, cores e conteúdo reais do site atual ({site}). Motivo do redesign: {motivo}.
Escreva o HTML final (self-contained) no arquivo {dest}/index.html."""


def gerar_index_com_claude(lead: Lead, dest_dir: str, timeout: int = 600) -> None:
    prompt = _PROMPT.format(nome=lead.nome, nicho=lead.nicho or "?",
                            site=lead.siteAntigo or "?", motivo=lead.motivo or "?", dest=dest_dir)
    r = subprocess.run(["claude", "-p", prompt, "--add-dir", dest_dir],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p (redesign) falhou: {r.stderr[:400]}")
    if not os.path.exists(os.path.join(dest_dir, "index.html")):
        raise RuntimeError("claude -p não gerou index.html")
