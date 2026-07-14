from __future__ import annotations
from prospector.descoberta.base import Candidato, DiscoveryProvider


def _num_br(v):
    if not v:
        return None
    return v.replace(".", "").replace(",", ".")


def _candidato_de_dados(d: dict) -> Candidato:
    nota = _num_br(d.get("nota"))
    aval = _num_br(d.get("avaliacoes"))
    return Candidato(
        nome=d.get("nome", "").strip(),
        site_url=d.get("site") or None,
        nota=float(nota) if nota else None,
        avaliacoes=int(float(aval)) if aval else None,
        telefone=d.get("telefone") or None,
        fonte="navegador",
    )


class BrowserDiscovery(DiscoveryProvider):
    """Real: dirige o Google Maps com Playwright. Sem cobertura de teste (rede/browser)."""

    def __init__(self, headless: bool = False):
        self.headless = headless

    def descobrir(self, nicho: str, cidade: str, meta: int) -> list[Candidato]:
        from playwright.sync_api import sync_playwright  # import tardio
        resultados: list[Candidato] = []
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=self.headless)
            pagina = navegador.new_page()
            pagina.goto("https://www.google.com/maps")
            pagina.fill("input#searchboxinput", f"{nicho} em {cidade}")
            pagina.keyboard.press("Enter")
            pagina.wait_for_timeout(4000)
            if "captcha" in pagina.url or pagina.query_selector("form#captcha-form"):
                navegador.close()
                raise RuntimeError("Google Maps pediu captcha — resolva no navegador e tente de novo.")
            # NOTE: implementer refina os seletores dos cards; extrai dicts crus e passa por _candidato_de_dados.
            cards = pagina.query_selector_all('div[role="feed"] > div')
            for card in cards:
                if len(resultados) >= meta:
                    break
                try:
                    nome = card.query_selector('div.fontHeadlineSmall')
                    if not nome:
                        continue
                    resultados.append(_candidato_de_dados({"nome": nome.inner_text()}))
                except Exception:
                    continue
            navegador.close()
        return resultados
