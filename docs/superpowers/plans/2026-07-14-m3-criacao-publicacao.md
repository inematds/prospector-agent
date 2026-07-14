# Prospector Agent — M3 Criação + Publicação — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Steps usam checkbox (`- [ ]`).

**Goal:** `prospector redesenhar <slug>` gera a página premium em `sites/<slug>/` (index.html via LLM + `proposta.html` capa antes/depois) e move o lead p/ `redesenhado`; `prospector publicar <slug>` sobe a pasta no GitHub Pages e move p/ `publicado` gravando a `urlNova` — com o LLM e o `git push` **injetáveis** para o núcleo ser testável sem rede.

**Architecture:** `Criador` recebe por injeção um `gerar_index(lead, dest_dir)` (real = `claude -p` + skill de redesign; teste = escreve stub); a capa (`montar_capa`) é pura. `Publicador` recebe um `publicar_arquivos(local_dir, slug)` (real = git push no monorepo Pages; teste = fake que registra a chamada). Transições validadas pela máquina de estados do M1.

**Tech Stack:** Python 3.11+, stdlib + pytest. Herda M1 (Store, Estado, máquina) e M2 (Lead qualificado).

## Global Constraints

- Python 3.11+. Núcleo determinístico e testável; **LLM só na geração do index**.
- **Limites externos injetáveis** (LLM de redesign, `git push`); **nenhum teste faz rede/subprocess/git real**. Boundaries reais existem, sem cobertura.
- **Transições válidas:** `qualificado → redesenhado → publicado`, sempre via `maquina_estados.avancar`.
- Idempotência por slug (Store do M1). `publicar` grava `urlNova` no lead.
- Arquivos de saída em `sites/<slug>/` (git-ignored — já está no `.gitignore`).

## File Structure

- `prospector/criacao/__init__.py`
- `prospector/criacao/capa.py` — `montar_capa(lead) -> str` (HTML capa antes/depois, PURO).
- `prospector/criacao/criador.py` — `Criador(gerar_index, base_dir="sites")` + `redesenhar(lead, conn) -> str`.
- `prospector/criacao/boundaries.py` — `gerar_index_com_claude(lead, dest_dir)` (real `claude -p`, sem cobertura).
- `prospector/publicacao/__init__.py`
- `prospector/publicacao/github_pages.py` — `Publicador(publicar_arquivos, base_url)` + `publicar(lead, conn, local_dir) -> str`.
- `prospector/publicacao/boundaries.py` — `publicar_via_git(local_dir, slug, repo_dir)` (real git, sem cobertura).
- `prospector/cli.py` — subcomandos `redesenhar` e `publicar`.
- Testes: `tests/test_capa.py`, `tests/test_criador.py`, `tests/test_publicador.py`, `tests/test_cli_criar_publicar.py`.

---

### Task 1: Capa antes/depois (`montar_capa`) — pura

**Files:** Create `prospector/criacao/__init__.py`, `prospector/criacao/capa.py`; Test `tests/test_capa.py`.

**Interfaces — Produces:** `montar_capa(lead: Lead) -> str` — HTML self-contained com: nome do negócio, o `motivo` (por que o site é ruim), um `<iframe>` do `siteAntigo` ("antes"), um link/iframe pra `urlNova` ("depois", ou aviso "ainda não publicado" se `None`), e uma CTA. Escapa `<`,`>`,`&` nos campos de texto.

- [ ] **Step 1: Teste que falha** — `tests/test_capa.py`:
```python
from prospector.modelos import Lead
from prospector.criacao.capa import montar_capa


def test_capa_contem_dados_do_lead():
    lead = Lead(slug="c", nome="Clínica X", siteAntigo="http://old.com",
                urlNova="http://new.com", motivo="layout datado")
    html = montar_capa(lead)
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "Clínica X" in html
    assert "http://old.com" in html and "http://new.com" in html
    assert "layout datado" in html


def test_capa_sem_url_nova_avisa():
    html = montar_capa(Lead(slug="c", nome="Y", siteAntigo="http://o.com"))
    assert "http://o.com" in html
    assert "não publicad" in html.lower() or "nao publicad" in html.lower()
```

- [ ] **Step 2: Falhar** — `python3 -m pytest tests/test_capa.py -v` → FAIL.
- [ ] **Step 3: Implementar** — `prospector/criacao/__init__.py` vazio; `prospector/criacao/capa.py`:
```python
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
```

- [ ] **Step 4: Passa** — PASS. **Step 5: Commit** — `git commit -m "feat(m3): capa antes/depois (montar_capa)"`

---

### Task 2: `Criador` (gera index via LLM injetável + capa)

**Files:** Create `prospector/criacao/criador.py`; Test `tests/test_criador.py`.

**Interfaces — Consumes:** `Lead`, `Estado`, `montar_capa`, `maquina_estados`, `db`. **Produces:** `Criador(gerar_index: Callable[[Lead, str], None], base_dir: str = "sites")` + `redesenhar(lead: Lead, conn) -> str` que: cria `<base_dir>/<slug>/`, chama `gerar_index(lead, dest)` (deve escrever `index.html`), valida que `index.html` existe e não está vazio (senão `RuntimeError`), escreve `proposta.html` = `montar_capa(lead)`, valida a transição `Estado(lead.status) → REDESENHADO` e grava o novo status no Store; retorna o caminho `dest`.

- [ ] **Step 1: Teste que falha** — `tests/test_criador.py`:
```python
import os
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.criacao.criador import Criador


def _fake_gera(lead, dest):
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(f"<html>{lead.nome} novo</html>")


def test_redesenhar_gera_arquivos_e_muda_status(tmp_path):
    conn = db.conectar(":memory:")
    lead = Lead(slug="clinica-x", nome="Clínica X", status=Estado.QUALIFICADO.value,
                siteAntigo="http://old.com", motivo="datado")
    db.salvar_lead(conn, lead)
    criador = Criador(_fake_gera, base_dir=str(tmp_path))
    dest = criador.redesenhar(lead, conn)
    assert os.path.exists(os.path.join(dest, "index.html"))
    assert os.path.exists(os.path.join(dest, "proposta.html"))
    assert db.ler_lead(conn, "clinica-x").status == "redesenhado"


def test_redesenhar_falha_se_index_vazio(tmp_path):
    conn = db.conectar(":memory:")
    lead = Lead(slug="y", nome="Y", status=Estado.QUALIFICADO.value)
    db.salvar_lead(conn, lead)
    criador = Criador(lambda l, d: None, base_dir=str(tmp_path))  # não escreve index
    try:
        criador.redesenhar(lead, conn)
        assert False, "deveria ter falhado"
    except RuntimeError:
        pass
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — `prospector/criacao/criador.py`:
```python
from __future__ import annotations
import os
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector.criacao.capa import montar_capa
from prospector import maquina_estados as me
from prospector.estado import db


class Criador:
    def __init__(self, gerar_index: Callable[[Lead, str], None], base_dir: str = "sites"):
        self._gerar = gerar_index
        self._base = base_dir

    def redesenhar(self, lead: Lead, conn) -> str:
        dest = os.path.join(self._base, lead.slug)
        os.makedirs(dest, exist_ok=True)
        self._gerar(lead, dest)
        idx = os.path.join(dest, "index.html")
        if not os.path.exists(idx) or os.path.getsize(idx) == 0:
            raise RuntimeError(f"gerar_index não produziu index.html em {dest}")
        with open(os.path.join(dest, "proposta.html"), "w", encoding="utf-8") as f:
            f.write(montar_capa(lead))
        novo = me.avancar(Estado(lead.status), Estado.REDESENHADO)
        lead.status = novo.value
        db.atualizar_status(conn, lead.slug, novo.value)
        return dest
```

- [ ] **Step 4: Passa** — PASS (2 testes). **Step 5: Commit** — `git commit -m "feat(m3): Criador (index via LLM injetável + capa + transição)"`

---

### Task 3: `Publicador` (git injetável) + URL + estado

**Files:** Create `prospector/publicacao/__init__.py`, `prospector/publicacao/github_pages.py`; Test `tests/test_publicador.py`.

**Interfaces — Produces:** `Publicador(publicar_arquivos: Callable[[str, str], None], base_url: str)` + `publicar(lead: Lead, conn, local_dir: str) -> str` que: valida transição `Estado(lead.status) → PUBLICADO`, chama `publicar_arquivos(local_dir, lead.slug)`, calcula `url = base_url.rstrip("/") + "/" + slug + "/"`, grava no lead `urlNova=url` e `status=publicado` (via `db.salvar_lead`), retorna a url.

- [ ] **Step 1: Teste que falha** — `tests/test_publicador.py`:
```python
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.publicacao.github_pages import Publicador


def test_publicar_chama_boundary_grava_url_e_status():
    chamadas = []
    pub = Publicador(lambda local, slug: chamadas.append((local, slug)),
                     base_url="https://inematds.github.io/prospector-sites")
    conn = db.conectar(":memory:")
    lead = Lead(slug="clinica-x", nome="X", status=Estado.REDESENHADO.value)
    db.salvar_lead(conn, lead)
    url = pub.publicar(lead, conn, local_dir="sites/clinica-x")
    assert url == "https://inematds.github.io/prospector-sites/clinica-x/"
    assert chamadas == [("sites/clinica-x", "clinica-x")]
    lido = db.ler_lead(conn, "clinica-x")
    assert lido.status == "publicado" and lido.urlNova == url


def test_publicar_recusa_estado_invalido():
    pub = Publicador(lambda l, s: None, base_url="http://x")
    conn = db.conectar(":memory:")
    lead = Lead(slug="y", nome="Y", status=Estado.QUALIFICADO.value)  # não pode publicar
    db.salvar_lead(conn, lead)
    try:
        pub.publicar(lead, conn, "sites/y")
        assert False
    except Exception:
        pass
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — `prospector/publicacao/__init__.py` vazio; `prospector/publicacao/github_pages.py`:
```python
from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db


class Publicador:
    def __init__(self, publicar_arquivos: Callable[[str, str], None], base_url: str):
        self._pub = publicar_arquivos
        self._base_url = base_url.rstrip("/")

    def publicar(self, lead: Lead, conn, local_dir: str) -> str:
        novo = me.avancar(Estado(lead.status), Estado.PUBLICADO)  # valida transição
        self._pub(local_dir, lead.slug)
        url = f"{self._base_url}/{lead.slug}/"
        lead.urlNova = url
        lead.status = novo.value
        db.salvar_lead(conn, lead)
        return url
```

- [ ] **Step 4: Passa** — PASS. **Step 5: Commit** — `git commit -m "feat(m3): Publicador (git injetável, URL, transição publicado)"`

---

### Task 4: Boundaries reais (LLM redesign + git push) — sem cobertura

**Files:** Create `prospector/criacao/boundaries.py`, `prospector/publicacao/boundaries.py`.

> Boundaries externos — **não testar**. Latitude p/ o implementer nos detalhes (flag do `claude -p`, comandos git). Erros devem virar exceção clara.

- [ ] **Step 1: Implementar** — `prospector/criacao/boundaries.py`:
```python
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
```
`prospector/publicacao/boundaries.py`:
```python
from __future__ import annotations
import os
import shutil
import subprocess


def publicar_via_git(local_dir: str, slug: str, repo_dir: str) -> None:
    """Copia sites/<slug>/ para <repo_dir>/<slug>/ e faz commit+push (monorepo Pages)."""
    destino = os.path.join(repo_dir, slug)
    os.makedirs(destino, exist_ok=True)
    shutil.copytree(local_dir, destino, dirs_exist_ok=True)
    subprocess.run(["git", "-C", repo_dir, "add", slug], check=True)
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", f"publica {slug}"], check=True)
    subprocess.run(["git", "-C", repo_dir, "push"], check=True)
```

- [ ] **Step 2: Import smoke** — `python3 -c "import prospector.criacao.boundaries, prospector.publicacao.boundaries"` → sem erro.
- [ ] **Step 3: Commit** — `git commit -m "feat(m3): boundaries reais (LLM redesign + git push) sem cobertura"`

---

### Task 5: CLI `redesenhar` e `publicar`

**Files:** Modify `prospector/cli.py`; Test `tests/test_cli_criar_publicar.py`.

**Interfaces — Produces:** subcomandos `redesenhar <slug> [--db]` e `publicar <slug> [--db] [--base-url] [--repo-dir]`. Cada um lê o lead do Store, roda `Criador`/`Publicador` com os boundaries reais e imprime o resultado. A LÓGICA já está nas classes (testadas); aqui só é a fiação — o teste chama `_cmd_redesenhar` com um lead no db e um criador de fake via monkeypatch da boundary NÃO é necessário: teste apenas o parsing do subcomando + erro de slug inexistente.

- [ ] **Step 1: Teste que falha** — `tests/test_cli_criar_publicar.py`:
```python
import pytest
from prospector import cli


def test_redesenhar_slug_inexistente_retorna_erro(tmp_path, capsys):
    rc = cli.main(["redesenhar", "nao-existe", "--db", str(tmp_path / "x.db")])
    assert rc == 1
    assert "não encontrado" in capsys.readouterr().out.lower() or \
           "nao encontrado" in capsys.readouterr().out.lower()


def test_subcomandos_registrados():
    parser_ok = cli.main  # smoke: main existe
    with pytest.raises(SystemExit):
        cli.main(["publicar"])  # falta o slug obrigatório -> argparse SystemExit
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — em `prospector/cli.py` adicione:
```python
def _lead_ou_erro(conn, slug):
    lead = db.ler_lead(conn, slug)
    if lead is None:
        print(f"Lead '{slug}' não encontrado.")
    return lead


def _cmd_redesenhar(args):
    from prospector.criacao.criador import Criador
    from prospector.criacao.boundaries import gerar_index_com_claude
    conn = db.conectar(args.db)
    lead = _lead_ou_erro(conn, args.slug)
    if lead is None:
        return 1
    dest = Criador(gerar_index_com_claude).redesenhar(lead, conn)
    print(f"redesenhado em {dest} (status: {lead.status})")
    return 0


def _cmd_publicar(args):
    from prospector.publicacao.github_pages import Publicador
    from prospector.publicacao.boundaries import publicar_via_git
    conn = db.conectar(args.db)
    lead = _lead_ou_erro(conn, args.slug)
    if lead is None:
        return 1
    pub = Publicador(lambda local, slug: publicar_via_git(local, slug, args.repo_dir), args.base_url)
    url = pub.publicar(lead, conn, local_dir=f"sites/{args.slug}")
    print(f"publicado: {url}")
    return 0
```
E registre em `main()`:
```python
    p_red = sub.add_parser("redesenhar", help="gera a página premium do lead")
    p_red.add_argument("slug")
    p_red.add_argument("--db", default="prospector.db")
    p_red.set_defaults(func=_cmd_redesenhar)

    p_pub = sub.add_parser("publicar", help="sobe o site no GitHub Pages")
    p_pub.add_argument("slug")
    p_pub.add_argument("--db", default="prospector.db")
    p_pub.add_argument("--base-url", default="https://inematds.github.io/prospector-sites")
    p_pub.add_argument("--repo-dir", default="../prospector-sites")
    p_pub.set_defaults(func=_cmd_publicar)
```

- [ ] **Step 4: Passa** — PASS. **Step 5: Suíte inteira** — `python3 -m pytest -q` (M1+M2+M3 verdes). **Step 6: Commit** — `git commit -m "feat(m3): CLI redesenhar e publicar"`

---

## Self-Review

- Capa antes/depois pura → Task 1 ✓; Criador com LLM injetável + transição → Task 2 ✓; Publicador git injetável + URL + estado → Task 3 ✓; boundaries reais isolados → Task 4 ✓; CLI → Task 5 ✓.
- Transições sempre por `maquina_estados.avancar` (qualificado→redesenhado→publicado) ✓.
- Nenhum teste toca LLM/git/rede ✓.
- **Não verificável no sandbox (precisa do usuário):** `claude -p` de redesign real e `git push` real no repo Pages. Documentar no relatório.

**Type consistency:** `Criador.redesenhar(lead, conn)->str` e `Publicador.publicar(lead, conn, local_dir)->str`; `montar_capa(lead)->str`; usa `Lead`/`Estado`/`db`/`maquina_estados` do M1.
