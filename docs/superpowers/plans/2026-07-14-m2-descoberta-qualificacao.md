# Prospector Agent — M2 Descoberta + Qualificação — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `prospector prospectar <nicho> <cidade>` acha candidatos (Maps), aplica filtros baratos, qualifica "site ruim?" + extrai e-mail/WhatsApp e salva os leads qualificados no Store — com todos os limites externos (browser, LLM, HTTP) **injetáveis** para o núcleo ser 100% testável sem rede/credenciais.

**Architecture:** Descoberta é uma interface (`DiscoveryProvider`) com dois providers: `FakeDiscovery` (dados canned, p/ testes e dry-run) e `BrowserDiscovery` (Playwright, real). Qualificação (`Qualificador`) recebe por injeção um `chamar_llm` e um `buscar_site`, então os testes usam mocks e a versão real chama `claude -p` e busca o HTML. O CLI costura provider → filtros → qualificador → Store.

**Tech Stack:** Python 3.11+, stdlib + `pytest`. `playwright` só é importado dentro de `navegador.py` (import tardio) para não virar dependência dos testes.

## Global Constraints

- **Linguagem:** Python 3.11+. Herda tudo do M1 (Store, `Lead`, `Estado`, máquina de estados).
- **Núcleo determinístico e testável; LLM só em *qualificar*.**
- **Limites externos injetáveis:** browser, `claude -p` e fetch HTTP entram por parâmetro/interface; **nenhum teste faz rede, subprocess ou abre browser.** Providers/boundaries reais existem mas ficam fora da cobertura de teste (documentado).
- **E-mail é obrigatório:** candidato sem e-mail público → descartado (não vira lead).
- **Filtros baratos (sem LLM):** nota ≥ 4.7 **e** avaliações ≥ 40 **e** tem `site_url`.
- **Idempotência por slug** (Store do M1). Lead qualificado entra com `status = 'qualificado'`.
- **Segredos** do ambiente; `ANTHROPIC_API_KEY` é o que `claude -p` usa.

## File Structure

- `prospector/descoberta/__init__.py`
- `prospector/descoberta/base.py` — `Candidato` (dataclass) + `DiscoveryProvider` (ABC) + `passa_filtros_basicos(...)` + `slugify(nome, cidade)`.
- `prospector/descoberta/fake.py` — `FakeDiscovery(candidatos)`.
- `prospector/descoberta/navegador.py` — `BrowserDiscovery` (Playwright, real, sem cobertura) + `_candidato_de_dados(d)` (helper puro, testado).
- `prospector/qualificacao/__init__.py`
- `prospector/qualificacao/qualificador.py` — `Qualificador(chamar_llm, buscar_site, nota_min=4.7, aval_min=40)` + `qualificar(cand) -> Lead | None`.
- `prospector/qualificacao/boundaries.py` — `chamar_claude(prompt) -> str` (subprocess `claude -p`) e `buscar_site(url) -> str` (urllib). Reais, sem cobertura.
- `prospector/cli.py` — subcomando `prospectar`.
- Testes: `tests/test_descoberta_base.py`, `tests/test_fake.py`, `tests/test_navegador_parse.py`, `tests/test_qualificador.py`, `tests/test_cli_prospectar.py`.

---

### Task 1: Contrato de descoberta — `Candidato`, filtros e slug

**Files:** Create `prospector/descoberta/__init__.py`, `prospector/descoberta/base.py`; Test `tests/test_descoberta_base.py`.

**Interfaces — Produces:**
- `@dataclass Candidato`: `nome: str`, `site_url: str | None = None`, `nota: float | None = None`, `avaliacoes: int | None = None`, `telefone: str | None = None`, `whatsapp: str | None = None`, `fonte: str = "?"`.
- `class DiscoveryProvider(ABC)` com `@abstractmethod def descobrir(self, nicho: str, cidade: str, meta: int) -> list[Candidato]`.
- `passa_filtros_basicos(c: Candidato, nota_min: float = 4.7, aval_min: int = 40) -> bool` — True só se `nota >= nota_min` e `avaliacoes >= aval_min` e `site_url` truthy.
- `slugify(nome: str, cidade: str | None = None) -> str` — minúsculo, sem acento, espaços/símbolos → `-`, sem duplos `-`.

- [ ] **Step 1: Teste que falha** — `tests/test_descoberta_base.py`:
```python
from prospector.descoberta.base import Candidato, passa_filtros_basicos, slugify


def test_filtros_reprova_nota_baixa_poucas_aval_ou_sem_site():
    assert passa_filtros_basicos(Candidato("A", "http://a.com", 4.8, 120))
    assert not passa_filtros_basicos(Candidato("B", "http://b.com", 4.5, 120))  # nota
    assert not passa_filtros_basicos(Candidato("C", "http://c.com", 4.9, 10))   # aval
    assert not passa_filtros_basicos(Candidato("D", None, 4.9, 120))            # sem site


def test_slugify():
    assert slugify("Clínica São José", "Bauru") == "clinica-sao-jose-bauru"
    assert slugify("Dr. Ana  Paula") == "dr-ana-paula"
```

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_descoberta_base.py -v` → FAIL (módulo inexistente).

- [ ] **Step 3: Implementar** — `prospector/descoberta/__init__.py` vazio; `prospector/descoberta/base.py`:
```python
from __future__ import annotations
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Candidato:
    nome: str
    site_url: str | None = None
    nota: float | None = None
    avaliacoes: int | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    fonte: str = "?"


class DiscoveryProvider(ABC):
    @abstractmethod
    def descobrir(self, nicho: str, cidade: str, meta: int) -> list["Candidato"]:
        ...


def passa_filtros_basicos(c: Candidato, nota_min: float = 4.7, aval_min: int = 40) -> bool:
    return bool(c.site_url) and (c.nota or 0) >= nota_min and (c.avaliacoes or 0) >= aval_min


def slugify(nome: str, cidade: str | None = None) -> str:
    base = f"{nome} {cidade}" if cidade else nome
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return re.sub(r"-+", "-", base)
```

- [ ] **Step 4: Passa** — `python3 -m pytest tests/test_descoberta_base.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add prospector/descoberta tests/test_descoberta_base.py && git commit -m "feat(m2): contrato de descoberta (Candidato, filtros, slug)"`

---

### Task 2: `FakeDiscovery` (provider para testes e dry-run)

**Files:** Create `prospector/descoberta/fake.py`; Test `tests/test_fake.py`.

**Interfaces — Consumes:** `Candidato`, `DiscoveryProvider`. **Produces:** `FakeDiscovery(candidatos: list[Candidato])` cujo `descobrir(nicho, cidade, meta)` retorna até `meta` candidatos da lista injetada (marca `fonte="fake"`).

- [ ] **Step 1: Teste que falha** — `tests/test_fake.py`:
```python
from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery


def test_fake_retorna_ate_meta_com_fonte():
    cands = [Candidato(f"N{i}", f"http://n{i}.com", 4.8, 50) for i in range(5)]
    prov = FakeDiscovery(cands)
    r = prov.descobrir("nutri", "Bauru", meta=3)
    assert len(r) == 3
    assert all(c.fonte == "fake" for c in r)
```

- [ ] **Step 2: Falhar** — `python3 -m pytest tests/test_fake.py -v` → FAIL.
- [ ] **Step 3: Implementar** — `prospector/descoberta/fake.py`:
```python
from __future__ import annotations
from dataclasses import replace
from prospector.descoberta.base import Candidato, DiscoveryProvider


class FakeDiscovery(DiscoveryProvider):
    def __init__(self, candidatos: list[Candidato]):
        self._candidatos = candidatos

    def descobrir(self, nicho: str, cidade: str, meta: int) -> list[Candidato]:
        return [replace(c, fonte="fake") for c in self._candidatos[:meta]]
```

- [ ] **Step 4: Passa** — PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(m2): FakeDiscovery provider"`

---

### Task 3: `Qualificador` (LLM injetável) — o coração do M2

**Files:** Create `prospector/qualificacao/__init__.py`, `prospector/qualificacao/qualificador.py`; Test `tests/test_qualificador.py`.

**Interfaces — Consumes:** `Candidato`, `slugify`, `Lead`, `Estado`. **Produces:**
- `Qualificador(chamar_llm: Callable[[str], str], buscar_site: Callable[[str], str], nota_min=4.7, aval_min=40)`.
- `qualificar(c: Candidato) -> Lead | None`: reprova nos filtros básicos → `None`; senão busca o HTML, monta prompt, chama o LLM (que retorna JSON `{"site_ruim": bool, "motivo": str, "email": str|null, "whatsapp": str|null}`), e: se `site_ruim` for False **ou** não houver e-mail → `None` (descartado); senão retorna `Lead(slug=slugify(nome,?), nome, nota, avaliacoes, email, telefone, whatsapp, siteAntigo=site_url, motivo, status='qualificado')`.
- Deve extrair o JSON mesmo se o LLM cercar com texto (regex do primeiro `{...}`).

- [ ] **Step 1: Teste que falha** — `tests/test_qualificador.py`:
```python
import json
from prospector.descoberta.base import Candidato
from prospector.qualificacao.qualificador import Qualificador


def _llm(resp): return lambda prompt: resp
def _site(html="<html>site</html>"): return lambda url: html
BOM = Candidato("Boa Clínica", "http://boa.com", 4.9, 200)


def test_site_ruim_com_email_vira_lead():
    veredito = json.dumps({"site_ruim": True, "motivo": "layout datado, sem CTA",
                           "email": "contato@boa.com", "whatsapp": "5514999990000"})
    q = Qualificador(_llm("veredito: " + veredito), _site())
    lead = q.qualificar(BOM)
    assert lead is not None
    assert lead.status == "qualificado"
    assert lead.email == "contato@boa.com"
    assert lead.motivo and lead.siteAntigo == "http://boa.com"
    assert lead.slug == "boa-clinica"


def test_site_bom_descarta():
    q = Qualificador(_llm(json.dumps({"site_ruim": False, "motivo": "", "email": "x@y.com"})), _site())
    assert q.qualificar(BOM) is None


def test_sem_email_descarta():
    q = Qualificador(_llm(json.dumps({"site_ruim": True, "motivo": "ruim", "email": None})), _site())
    assert q.qualificar(BOM) is None


def test_reprova_filtro_nao_chama_llm():
    chamado = []
    q = Qualificador(lambda p: chamado.append(1) or "{}", _site())
    assert q.qualificar(Candidato("X", "http://x.com", 4.0, 5)) is None
    assert chamado == []   # nem buscou site nem LLM
```

- [ ] **Step 2: Falhar** — FAIL.
- [ ] **Step 3: Implementar** — `prospector/qualificacao/__init__.py` vazio; `prospector/qualificacao/qualificador.py`:
```python
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
```

- [ ] **Step 4: Passa** — `python3 -m pytest tests/test_qualificador.py -v` → PASS (4 testes).
- [ ] **Step 5: Commit** — `git commit -m "feat(m2): Qualificador com LLM e fetch injetáveis"`

---

### Task 4: Boundaries reais (`claude -p` + fetch) — sem cobertura de teste

**Files:** Create `prospector/qualificacao/boundaries.py`.

**Interfaces — Produces:** `chamar_claude(prompt: str) -> str` (roda `claude -p <prompt>` via subprocess, retorna stdout) e `buscar_site(url: str) -> str` (GET via urllib, retorna HTML; erro → `""`).

> Boundary externo: **não escreva teste** (usa subprocess/rede). O implementer confirma o flag exato do CLI (`claude -p "<prompt>"` capturando stdout; se precisar, `--output-format text`). Timeout defensivo e captura de erro obrigatórios.

- [ ] **Step 1: Implementar** — `prospector/qualificacao/boundaries.py`:
```python
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
```

- [ ] **Step 2: Import smoke** — `python3 -c "import prospector.qualificacao.boundaries"` → sem erro.
- [ ] **Step 3: Commit** — `git commit -m "feat(m2): boundaries reais claude -p + fetch (sem cobertura)"`

---

### Task 5: `BrowserDiscovery` (Playwright, real) + helper puro testado

**Files:** Create `prospector/descoberta/navegador.py`; Test `tests/test_navegador_parse.py`.

**Interfaces — Produces:** `BrowserDiscovery(headless=False)` (implementa `descobrir`, real, sem cobertura) + `_candidato_de_dados(d: dict) -> Candidato` (helper PURO — converte um dict cru de card do Maps em `Candidato`; ESTE é testado).

> `playwright` é importado **dentro** de `descobrir` (import tardio), não no topo — assim os testes não exigem o pacote. O implementer escreve a navegação real (abrir maps, buscar `[nicho] em [cidade]`, ler cards); se o Maps pedir captcha/login, levantar exceção clara. A lógica de scrape NÃO é testada aqui.

- [ ] **Step 1: Teste que falha** (só o helper puro) — `tests/test_navegador_parse.py`:
```python
from prospector.descoberta.navegador import _candidato_de_dados


def test_parse_card_extrai_campos():
    c = _candidato_de_dados({"nome": "Clínica X", "site": "http://x.com",
                             "nota": "4,8", "avaliacoes": "1.234", "telefone": "(14) 99999-0000"})
    assert c.nome == "Clínica X"
    assert c.nota == 4.8            # vírgula decimal BR -> float
    assert c.avaliacoes == 1234     # milhar BR removido
    assert c.site_url == "http://x.com"
    assert c.fonte == "navegador"


def test_parse_card_campos_ausentes():
    c = _candidato_de_dados({"nome": "Só Nome"})
    assert c.nome == "Só Nome" and c.nota is None and c.site_url is None
```

- [ ] **Step 2: Falhar** — FAIL.
- [ ] **Step 3: Implementar** — `prospector/descoberta/navegador.py` (helper puro + navegação real):
```python
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
```

- [ ] **Step 4: Passa (helper)** — `python3 -m pytest tests/test_navegador_parse.py -v` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(m2): BrowserDiscovery (Playwright) + parser de card testado"`

---

### Task 6: CLI `prospectar` (costura provider → filtros → qualificador → Store)

**Files:** Modify `prospector/cli.py`; Test `tests/test_cli_prospectar.py`.

**Interfaces — Produces:**
- `prospectar(provider, qualificador, conn, nicho, cidade, meta) -> list[Lead]` — itera `provider.descobrir(...)`, qualifica cada um, salva os leads (não-None) no Store, retorna a lista salva.
- Subcomando CLI `prospectar <nicho> <cidade> [--provider fake|navegador] [--meta N] [--db P]`. Com `--provider fake` usa `FakeDiscovery` com 1 candidato canned e um LLM/fetch reais só se `navegador`; **no teste, a função `prospectar` é chamada direto com mocks** (o subcomando real monta os boundaries de verdade).

- [ ] **Step 1: Teste que falha** — `tests/test_cli_prospectar.py`:
```python
import json
from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery
from prospector.qualificacao.qualificador import Qualificador
from prospector.estado import db
from prospector.cli import prospectar


def test_prospectar_salva_so_qualificados():
    cands = [Candidato("Boa", "http://boa.com", 4.9, 100),
             Candidato("Ruim nota", "http://r.com", 4.0, 100)]  # reprova filtro
    prov = FakeDiscovery(cands)
    veredito = json.dumps({"site_ruim": True, "motivo": "datado", "email": "a@boa.com"})
    q = Qualificador(lambda p: veredito, lambda u: "<html/>")
    conn = db.conectar(":memory:")
    salvos = prospectar(prov, q, conn, "nutri", "Bauru", meta=10)
    assert [l.slug for l in salvos] == ["boa"]
    assert db.ler_lead(conn, "boa").status == "qualificado"
```

- [ ] **Step 2: Falhar** — FAIL (`prospectar` inexistente).
- [ ] **Step 3: Implementar** — em `prospector/cli.py` adicione:
```python
# imports no topo:
from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery
from prospector.qualificacao.qualificador import Qualificador


def prospectar(provider, qualificador, conn, nicho, cidade, meta):
    salvos = []
    for cand in provider.descobrir(nicho, cidade, meta):
        lead = qualificador.qualificar(cand)
        if lead is not None:
            db.salvar_lead(conn, lead)
            salvos.append(lead)
    return salvos


def _cmd_prospectar(args):
    if args.provider == "fake":
        provider = FakeDiscovery([Candidato("Clínica Demo", "http://demo.com", 4.9, 120)])
        chamar_llm = lambda p: '{"site_ruim": true, "motivo": "demo", "email": "demo@demo.com"}'
        buscar_site = lambda u: "<html>demo</html>"
    else:
        from prospector.descoberta.navegador import BrowserDiscovery
        from prospector.qualificacao.boundaries import chamar_claude, buscar_site as _bs
        provider, chamar_llm, buscar_site = BrowserDiscovery(), chamar_claude, _bs
    q = Qualificador(chamar_llm, buscar_site)
    conn = db.conectar(args.db)
    salvos = prospectar(provider, q, conn, args.nicho, args.cidade, args.meta)
    print(f"{len(salvos)} lead(s) qualificado(s):")
    for l in salvos:
        print(f"  - {l.slug} ({l.email}) — {l.motivo}")
    return 0
```
E registre o subcomando em `main()` (ao lado de `demo`/`init`):
```python
    p_pros = sub.add_parser("prospectar", help="busca e qualifica leads")
    p_pros.add_argument("nicho")
    p_pros.add_argument("cidade")
    p_pros.add_argument("--provider", choices=["fake", "navegador"], default="fake")
    p_pros.add_argument("--meta", type=int, default=10)
    p_pros.add_argument("--db", default="prospector.db")
    p_pros.set_defaults(func=_cmd_prospectar)
```

- [ ] **Step 4: Passa** — `python3 -m pytest tests/test_cli_prospectar.py -v` → PASS.
- [ ] **Step 5: Suíte inteira + smoke** — `python3 -m pytest -q` (todos M1+M2 verdes) e `python3 -m prospector prospectar nutri Bauru --provider fake --db /tmp/pa_m2.db` → imprime 1 lead `clinica-demo`. Apague `/tmp/pa_m2.db` depois.
- [ ] **Step 6: Commit** — `git commit -m "feat(m2): CLI prospectar (descoberta -> qualificação -> Store)"`

---

## Self-Review

- Descoberta plugável (contrato + fake + browser) → Tasks 1,2,5 ✓
- Qualificação com LLM/fetch injetáveis, e-mail obrigatório, filtros → Task 3 ✓
- Boundaries reais isolados sem cobertura → Task 4 ✓
- CLI prospectar salvando no Store → Task 6 ✓
- Limites externos nunca tocados por teste (fake provider + mocks) ✓
- **Não verificável no sandbox (precisa do usuário):** scrape real do Maps (`--provider navegador`) e `claude -p` real. Documentar no relatório.

**Type consistency:** `Candidato`/`DiscoveryProvider` de `base` usados igual em fake/navegador/qualificador; `Qualificador.qualificar -> Lead|None` consumido pela `prospectar`; `Lead`/`Estado` do M1.
