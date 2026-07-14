from __future__ import annotations
import json
import re
from typing import Callable
from prospector.descoberta.base import Candidato, passa_filtros_basicos, slugify
from prospector.modelos import Lead, Estado

PROMPT = """Você avalia se o site de um negócio é RUIM (candidato a redesign).
Negócio: {nome}. Site: {url}.
HTML do site (pode estar truncado):
---
{html}
---
Responda SOMENTE um JSON: {{"site_ruim": true/false, "motivo": "<motivo objetivo>",
"email": "<email publico ou null>", "whatsapp": "<numero 55DDD... ou null>"}}"""


def _extrai_json(txt: str) -> dict:
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


class Qualificador:
    def __init__(self, chamar_llm: Callable[[str], str], buscar_site: Callable[[str], str],
                 nota_min: float = 4.7, aval_min: int = 40):
        self._llm = chamar_llm
        self._site = buscar_site
        self._nota_min = nota_min
        self._aval_min = aval_min

    def qualificar(self, c: Candidato) -> Lead | None:
        if not passa_filtros_basicos(c, self._nota_min, self._aval_min):
            return None
        html = (self._site(c.site_url) or "")[:6000]
        veredito = _extrai_json(self._llm(PROMPT.format(nome=c.nome, url=c.site_url, html=html)))
        email = veredito.get("email")
        if not veredito.get("site_ruim") or not email:
            return None
        return Lead(
            slug=slugify(c.nome), nome=c.nome, nota=c.nota, avaliacoes=c.avaliacoes,
            email=email, telefone=c.telefone, whatsapp=veredito.get("whatsapp") or c.whatsapp,
            siteAntigo=c.site_url, motivo=veredito.get("motivo"),
            status=Estado.QUALIFICADO.value,
        )
