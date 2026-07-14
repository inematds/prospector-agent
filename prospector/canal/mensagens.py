from __future__ import annotations
from prospector.modelos import Lead


def parse_prospectar(texto: str) -> tuple[str, str, bool]:
    toks = texto.split()
    if toks and toks[0].startswith("/"):
        toks = toks[1:]
    auto = "--auto" in toks
    positionais = [t for t in toks if not t.startswith("--")]
    if len(positionais) < 2:
        raise ValueError("uso: /prospectar <nicho> <cidade> [--auto]")
    return positionais[0], positionais[1], auto


def msg_pedir_aprovacao(lead: Lead) -> str:
    return (f"🔎 Lead pronto: *{lead.nome}*\n"
            f"Motivo: {lead.motivo or '-'}\n"
            f"Preview: {lead.urlNova or '(sem url)'}\n"
            f"Aprovar o envio da proposta?")


def msg_enviado(lead: Lead) -> str:
    return f"✅ Proposta enviada para {lead.email} ({lead.nome})."
