from __future__ import annotations
from html import escape
from prospector.modelos import Lead


def montar_capa(lead: Lead) -> str:
    nome = escape(lead.nome or "")
    motivo = escape(lead.motivo or "")
    antigo = escape(lead.siteAntigo or "")
    if lead.urlNova:
        depois = f'<a href="{escape(lead.urlNova)}">Ver a nova versão ↗</a>'
    else:
        depois = "<em>Nova versão ainda não publicada.</em>"
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Proposta — {nome}</title></head>
<body style="font-family:sans-serif;max-width:900px;margin:auto;padding:24px">
  <h1>{nome}</h1>
  <p><strong>O que notamos:</strong> {motivo}</p>
  <div style="display:flex;gap:16px;flex-wrap:wrap">
    <div style="flex:1;min-width:280px">
      <h3>Antes</h3>
      <iframe src="{antigo}" style="width:100%;height:420px;border:1px solid #ccc"></iframe>
      <p>{antigo}</p>
    </div>
    <div style="flex:1;min-width:280px">
      <h3>Depois</h3>
      {depois}
    </div>
  </div>
</body></html>"""
