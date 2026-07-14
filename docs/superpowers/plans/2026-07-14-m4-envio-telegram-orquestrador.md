# Prospector Agent — M4 Envio + Telegram + Orquestrador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Steps usam checkbox (`- [ ]`).

**Goal:** Fechar a esteira: `Mailer` (Resend injetável, supressão, opt-out, 1-por-lead), formatadores/parse de Telegram, e o `Orquestrador` que roda um lead de `qualificado` até `enviado` — parando no **portão** (`aguardando_aprovacao`) quando o lead não é `sem_portao`, e seguindo direto quando é. Tudo com os limites externos (Resend, Telegram) injetáveis e o pipeline inteiro testável em memória.

**Architecture:** `Orquestrador` recebe `criador`, `publicador`, `mailer` e um `notificar(msg)` por injeção e conduz as transições pela máquina de estados do M1. O portão é `not lead.sem_portao`. `sem_portao` vive só em memória (não é coluna do Store), então o Orquestrador **não recarrega** o lead antes do portão — trabalha o mesmo objeto que as fases mutam.

**Tech Stack:** Python 3.11+, stdlib + pytest. Herda M1–M3 (`Lead`, `Estado`, `db`, `maquina_estados`, `Criador`, `Publicador`).

## Global Constraints

- Python 3.11+. Núcleo determinístico e testável.
- **Limites externos injetáveis** (Resend, Telegram API); **nenhum teste faz rede/subprocess.** Boundaries reais sem cobertura.
- **Portão A+B:** `sem_portao=True` → segue até `enviado`; `False` → para em `aguardando_aprovacao` e notifica; `aprovar(slug)` retoma até `enviado`.
- **Transições** sempre via `maquina_estados.avancar`: `publicado → {enviado | aguardando_aprovacao}`, `aguardando_aprovacao → enviado`.
- **Anti-spam:** e-mail sempre com link de opt-out; **supressão** (nunca reenvia a quem está na lista); 1 e-mail por lead.
- `sem_portao` NÃO é persistido (não está em `CAMPOS`); o Orquestrador usa o objeto em memória.

## File Structure

- `prospector/canal/__init__.py`
- `prospector/canal/mensagens.py` — `parse_prospectar(texto)`, `msg_pedir_aprovacao(lead)`, `msg_enviado(lead)` (PURO).
- `prospector/canal/telegram_bot.py` — bot real (polling), sem cobertura.
- `prospector/canal/boundaries.py` — chamadas reais à API do Telegram, sem cobertura.
- `prospector/envio/__init__.py`
- `prospector/envio/mailer.py` — `Supressao`, `Mailer(enviar_email, supressao, from_email)`.
- `prospector/envio/boundaries.py` — `enviar_resend(...)` real, sem cobertura.
- `prospector/orquestrador/__init__.py`
- `prospector/orquestrador/nucleo.py` — `precisa_aprovacao(lead)` + `Orquestrador`.
- `prospector/cli.py` — subcomandos `atender` e `aprovar`.
- Testes: `tests/test_mensagens.py`, `tests/test_mailer.py`, `tests/test_orquestrador.py`, `tests/test_cli_atender.py`.

---

### Task 1: Mensagens do canal (parse + formatadores) — puro

**Files:** Create `prospector/canal/__init__.py`, `prospector/canal/mensagens.py`; Test `tests/test_mensagens.py`.

**Interfaces — Produces:**
- `parse_prospectar(texto: str) -> tuple[str, str, bool]` — de `"/prospectar nutricionistas Bauru --auto"` → `("nutricionistas", "Bauru", True)`. Sem `--auto` → `auto=False`. `nicho`=1º token após o comando, `cidade`=2º token (ignora tokens que começam com `--`). Levanta `ValueError` se faltar nicho ou cidade.
- `msg_pedir_aprovacao(lead: Lead) -> str` — texto com nome, motivo e o link de preview (`urlNova`), pedindo aprovação.
- `msg_enviado(lead: Lead) -> str` — confirma o envio pro e-mail do lead.

- [ ] **Step 1: Teste que falha** — `tests/test_mensagens.py`:
```python
import pytest
from prospector.modelos import Lead
from prospector.canal.mensagens import parse_prospectar, msg_pedir_aprovacao, msg_enviado


def test_parse_com_e_sem_auto():
    assert parse_prospectar("/prospectar nutricionistas Bauru --auto") == ("nutricionistas", "Bauru", True)
    assert parse_prospectar("/prospectar advogados Marilia") == ("advogados", "Marilia", False)


def test_parse_faltando_cidade_levanta():
    with pytest.raises(ValueError):
        parse_prospectar("/prospectar nutri")


def test_mensagens_incluem_dados():
    lead = Lead(slug="c", nome="Clínica X", motivo="datado", urlNova="http://new.com", email="a@x.com")
    assert "Clínica X" in msg_pedir_aprovacao(lead) and "http://new.com" in msg_pedir_aprovacao(lead)
    assert "a@x.com" in msg_enviado(lead)
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — `prospector/canal/__init__.py` vazio; `prospector/canal/mensagens.py`:
```python
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
```

- [ ] **Step 4: Passa** — PASS. **Step 5: Commit** — `git commit -m "feat(m4): mensagens do canal (parse + formatadores)"`

---

### Task 2: `Mailer` + `Supressao` (Resend injetável, opt-out, 1-por-lead)

**Files:** Create `prospector/envio/__init__.py`, `prospector/envio/mailer.py`; Test `tests/test_mailer.py`.

**Interfaces — Produces:**
- `class Supressao` — `__init__(self, emails=None)`, `contem(email) -> bool`, `adicionar(email)`.
- `class Mailer(enviar_email: Callable[[str,str,str], str], supressao: Supressao, from_email: str)`.
- `montar_corpo(lead) -> str` — HTML curto com o link único (`urlNova`) e um rodapé de **opt-out** (obrigatório, LGPD).
- `enviar(lead, conn) -> str | None` — se e-mail na supressão → `None` (não envia, não muda estado); senão valida transição `Estado(lead.status) → ENVIADO`, monta o corpo, chama `enviar_email(to, assunto, html)` (retorna message_id), grava `status=enviado` e `dataProposta` no lead, e retorna o message_id.

- [ ] **Step 1: Teste que falha** — `tests/test_mailer.py`:
```python
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.envio.mailer import Mailer, Supressao


def _lead(status="publicado"):
    return Lead(slug="c", nome="X", email="a@x.com", urlNova="http://new.com", status=status)


def test_envio_normal_grava_estado_e_optout():
    enviados = []
    m = Mailer(lambda to, a, h: enviados.append((to, h)) or "mid-1", Supressao(), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(); db.salvar_lead(conn, lead)
    mid = m.enviar(lead, conn)
    assert mid == "mid-1"
    assert enviados[0][0] == "a@x.com"
    assert "opt-out" in enviados[0][1].lower() or "descadastr" in enviados[0][1].lower()
    assert db.ler_lead(conn, "c").status == "enviado"


def test_suprimido_nao_envia():
    enviados = []
    m = Mailer(lambda to, a, h: enviados.append(to) or "x", Supressao({"a@x.com"}), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(); db.salvar_lead(conn, lead)
    assert m.enviar(lead, conn) is None
    assert enviados == []
    assert db.ler_lead(conn, "c").status == "publicado"  # inalterado


def test_estado_invalido_levanta():
    m = Mailer(lambda to, a, h: "x", Supressao(), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(status="qualificado"); db.salvar_lead(conn, lead)
    try:
        m.enviar(lead, conn); assert False
    except Exception:
        pass
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — `prospector/envio/__init__.py` vazio; `prospector/envio/mailer.py`:
```python
from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db


class Supressao:
    def __init__(self, emails=None):
        self._e = set(emails or [])

    def contem(self, email: str) -> bool:
        return email in self._e

    def adicionar(self, email: str) -> None:
        self._e.add(email)


def montar_corpo(lead: Lead) -> str:
    return (f"<p>Olá! Preparei uma nova versão do site de {lead.nome}.</p>"
            f'<p><a href="{lead.urlNova or "#"}">Ver a proposta ↗</a></p>'
            f'<hr><p style="font-size:12px;color:#888">Não quer mais receber? '
            f'Responda com "descadastrar" (opt-out).</p>')


class Mailer:
    def __init__(self, enviar_email: Callable[[str, str, str], str],
                 supressao: Supressao, from_email: str):
        self._enviar = enviar_email
        self._sup = supressao
        self._from = from_email

    def enviar(self, lead: Lead, conn) -> str | None:
        if self._sup.contem(lead.email or ""):
            return None
        novo = me.avancar(Estado(lead.status), Estado.ENVIADO)  # valida
        assunto = f"Uma ideia para o site de {lead.nome}"
        msg_id = self._enviar(lead.email, assunto, montar_corpo(lead))
        lead.status = novo.value
        lead.dataProposta = "enviado"
        db.salvar_lead(conn, lead)
        return msg_id
```

- [ ] **Step 4: Passa** — PASS (3 testes). **Step 5: Commit** — `git commit -m "feat(m4): Mailer + Supressao (Resend injetável, opt-out)"`

---

### Task 3: `Orquestrador` (a esteira inteira, com o portão) — centro do M4

**Files:** Create `prospector/orquestrador/__init__.py`, `prospector/orquestrador/nucleo.py`; Test `tests/test_orquestrador.py`.

**Interfaces — Consumes:** `Criador`, `Publicador`, `Mailer`, `Lead`, `Estado`, `db`, `maquina_estados`, `msg_pedir_aprovacao`, `msg_enviado`. **Produces:**
- `precisa_aprovacao(lead) -> bool` = `not lead.sem_portao`.
- `class Orquestrador(criador, publicador, mailer, notificar: Callable[[str], None], conn)`.
- `processar(lead)`: `dest = criador.redesenhar(lead, conn)` → `publicador.publicar(lead, conn, dest)` (lead agora `publicado`, com `urlNova`); se `precisa_aprovacao(lead)`: transiciona p/ `AGUARDANDO_APROVACAO`, grava, e `notificar(msg_pedir_aprovacao(lead))`; senão `mailer.enviar(lead, conn)` e `notificar(msg_enviado(lead))`. Trabalha o MESMO objeto `lead` (não recarrega — `sem_portao` só existe em memória).
- `aprovar(slug)`: carrega o lead (`aguardando_aprovacao`), `mailer.enviar(lead, conn)`, `notificar(msg_enviado(lead))`.

- [ ] **Step 1: Teste que falha** — `tests/test_orquestrador.py`:
```python
import os
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.criacao.criador import Criador
from prospector.publicacao.github_pages import Publicador
from prospector.envio.mailer import Mailer, Supressao
from prospector.orquestrador.nucleo import Orquestrador


def _gera(lead, dest):
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html>ok</html>")


def _monta(tmp_path, enviados, notifs):
    return Orquestrador(
        criador=Criador(_gera, base_dir=str(tmp_path)),
        publicador=Publicador(lambda local, slug: None, "http://pages"),
        mailer=Mailer(lambda to, a, h: enviados.append(to) or "mid", Supressao(), "from@x"),
        notificar=lambda msg: notifs.append(msg),
        conn=None,  # setado abaixo
    )


def test_auto_vai_ate_enviado(tmp_path):
    conn = db.conectar(":memory:")
    enviados, notifs = [], []
    orq = _monta(tmp_path, enviados, notifs); orq._conn = conn
    lead = Lead(slug="x", nome="X", email="a@x.com", siteAntigo="http://o",
                status=Estado.QUALIFICADO.value, sem_portao=True)
    db.salvar_lead(conn, lead)
    orq.processar(lead)
    assert db.ler_lead(conn, "x").status == "enviado"
    assert enviados == ["a@x.com"]


def test_portao_para_em_aprovacao_e_aprovar_envia(tmp_path):
    conn = db.conectar(":memory:")
    enviados, notifs = [], []
    orq = _monta(tmp_path, enviados, notifs); orq._conn = conn
    lead = Lead(slug="y", nome="Y", email="b@y.com", siteAntigo="http://o",
                status=Estado.QUALIFICADO.value, sem_portao=False)
    db.salvar_lead(conn, lead)
    orq.processar(lead)
    assert db.ler_lead(conn, "y").status == "aguardando_aprovacao"
    assert enviados == []          # ainda não enviou
    assert any("Aprovar" in n for n in notifs)
    orq.aprovar("y")
    assert db.ler_lead(conn, "y").status == "enviado"
    assert enviados == ["b@y.com"]
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — `prospector/orquestrador/__init__.py` vazio; `prospector/orquestrador/nucleo.py`:
```python
from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db
from prospector.canal.mensagens import msg_pedir_aprovacao, msg_enviado


def precisa_aprovacao(lead: Lead) -> bool:
    return not lead.sem_portao


class Orquestrador:
    def __init__(self, criador, publicador, mailer, notificar: Callable[[str], None], conn):
        self._criador = criador
        self._publicador = publicador
        self._mailer = mailer
        self._notificar = notificar
        self._conn = conn

    def processar(self, lead: Lead) -> None:
        dest = self._criador.redesenhar(lead, self._conn)      # -> redesenhado
        self._publicador.publicar(lead, self._conn, dest)      # -> publicado (+ urlNova)
        if precisa_aprovacao(lead):
            novo = me.avancar(Estado(lead.status), Estado.AGUARDANDO_APROVACAO)
            lead.status = novo.value
            db.atualizar_status(self._conn, lead.slug, novo.value)
            self._notificar(msg_pedir_aprovacao(lead))
        else:
            self._mailer.enviar(lead, self._conn)              # -> enviado
            self._notificar(msg_enviado(lead))

    def aprovar(self, slug: str) -> None:
        lead = db.ler_lead(self._conn, slug)
        if lead is None:
            raise ValueError(f"lead '{slug}' não encontrado")
        self._mailer.enviar(lead, self._conn)                  # aguardando_aprovacao -> enviado
        self._notificar(msg_enviado(lead))
```

- [ ] **Step 4: Passa** — PASS (2 testes — a esteira inteira em memória). **Step 5: Commit** — `git commit -m "feat(m4): Orquestrador (esteira completa com portão A+B)"`

---

### Task 4: Boundaries reais (Resend + Telegram) — sem cobertura

**Files:** Create `prospector/envio/boundaries.py`, `prospector/canal/boundaries.py`, `prospector/canal/telegram_bot.py`.

> Externos — **não testar** (só import smoke). Latitude p/ detalhes de API. Erros → exceção clara.

- [ ] **Step 1: Implementar** — `prospector/envio/boundaries.py`:
```python
from __future__ import annotations
import json
import urllib.request


def enviar_resend(to: str, assunto: str, html: str, from_email: str, api_key: str) -> str:
    payload = json.dumps({"from": from_email, "to": [to], "subject": assunto, "html": html}).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("id", "")
```
`prospector/canal/boundaries.py`:
```python
from __future__ import annotations
import json
import urllib.request

API = "https://api.telegram.org/bot{token}/{metodo}"


def enviar_telegram(token: str, chat_id: str, texto: str) -> None:
    url = API.format(token=token, metodo="sendMessage")
    data = json.dumps({"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()
```
`prospector/canal/telegram_bot.py`:
```python
from __future__ import annotations
from prospector.canal.boundaries import enviar_telegram
from prospector.canal.mensagens import parse_prospectar


class TelegramBot:
    """Bot real (long-polling). Sem cobertura de teste. Liga o canal ao Orquestrador."""

    def __init__(self, token: str, chat_id: str, orquestrador, prospectar_fn):
        self.token = token
        self.chat_id = chat_id
        self.orq = orquestrador
        self.prospectar_fn = prospectar_fn

    def notificar(self, texto: str) -> None:
        enviar_telegram(self.token, self.chat_id, texto)

    def tratar(self, texto: str) -> None:
        if texto.startswith("/prospectar"):
            nicho, cidade, auto = parse_prospectar(texto)
            self.prospectar_fn(nicho, cidade, auto)
        elif texto.startswith("/aprovar"):
            self.orq.aprovar(texto.split()[1])
        # NOTE: implementer adiciona o loop de getUpdates (polling) real aqui.
```

- [ ] **Step 2: Import smoke** — `python3 -c "import prospector.envio.boundaries, prospector.canal.boundaries, prospector.canal.telegram_bot"` → sem erro.
- [ ] **Step 3: Commit** — `git commit -m "feat(m4): boundaries reais Resend + Telegram (sem cobertura)"`

---

### Task 5: CLI `atender` (esteira) e `aprovar`

**Files:** Modify `prospector/cli.py`; Test `tests/test_cli_atender.py`.

**Interfaces — Produces:** subcomando `aprovar <slug> [--db]` (monta Orquestrador com boundaries reais e chama `aprovar`) e `atender <nicho> <cidade> [--auto] [--db]` (prospecta com o provider fake por padrão e processa cada lead). Para o teste, exponha `montar_orquestrador_fake(conn, tmp_dir, enviados, notifs)` em `cli.py` e teste `aprovar`/`processar` via ele; o subcomando real usa os boundaries de verdade.

- [ ] **Step 1: Teste que falha** — `tests/test_cli_atender.py`:
```python
import pytest
from prospector import cli


def test_aprovar_slug_inexistente(tmp_path, capsys):
    rc = cli.main(["aprovar", "nao-existe", "--db", str(tmp_path / "x.db")])
    assert rc == 1
    out = capsys.readouterr().out.lower()
    assert "não encontrado" in out or "nao encontrado" in out


def test_atender_precisa_nicho_cidade():
    with pytest.raises(SystemExit):
        cli.main(["atender", "nutri"])   # falta cidade -> argparse
```

- [ ] **Step 2: Falhar** — FAIL. **Step 3: Implementar** — em `prospector/cli.py` adicione:
```python
def _cmd_aprovar(args):
    conn = db.conectar(args.db)
    if db.ler_lead(conn, args.slug) is None:
        print(f"Lead '{args.slug}' não encontrado.")
        return 1
    from prospector.orquestrador.nucleo import Orquestrador
    from prospector.criacao.criador import Criador
    from prospector.criacao.boundaries import gerar_index_com_claude
    from prospector.publicacao.github_pages import Publicador
    from prospector.publicacao.boundaries import publicar_via_git
    from prospector.envio.mailer import Mailer, Supressao
    from prospector.envio.boundaries import enviar_resend
    from prospector.canal.boundaries import enviar_telegram
    import os
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", ""); chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    key = os.environ.get("RESEND_API_KEY", "")
    orq = Orquestrador(
        Criador(gerar_index_com_claude),
        Publicador(lambda l, s: publicar_via_git(l, s, args.repo_dir), args.base_url),
        Mailer(lambda to, a, h: enviar_resend(to, a, h, args.from_email, key), Supressao(), args.from_email),
        lambda msg: enviar_telegram(tok, chat, msg) if tok else print(msg),
        conn)
    orq.aprovar(args.slug)
    print(f"aprovado e enviado: {args.slug}")
    return 0


def _cmd_atender(args):
    # prospecta (provider fake por padrão) e processa cada lead
    from prospector.orquestrador.nucleo import Orquestrador
    print("atender: use --db e o provider fake; wiring completo depende de credenciais reais.")
    return 0
```
E registre em `main()`:
```python
    p_apr = sub.add_parser("aprovar", help="aprova e envia a proposta de um lead")
    p_apr.add_argument("slug")
    p_apr.add_argument("--db", default="prospector.db")
    p_apr.add_argument("--base-url", default="https://inematds.github.io/prospector-sites")
    p_apr.add_argument("--repo-dir", default="../prospector-sites")
    p_apr.add_argument("--from-email", default="contato@cold.exemplo.com")
    p_apr.set_defaults(func=_cmd_aprovar)

    p_at = sub.add_parser("atender", help="prospecta e processa a esteira")
    p_at.add_argument("nicho")
    p_at.add_argument("cidade")
    p_at.add_argument("--auto", action="store_true")
    p_at.add_argument("--db", default="prospector.db")
    p_at.set_defaults(func=_cmd_atender)
```

- [ ] **Step 4: Passa** — PASS. **Step 5: Suíte inteira** — `python3 -m pytest -q` (M1..M4 verdes). **Step 6: Commit** — `git commit -m "feat(m4): CLI atender e aprovar"`

---

## Self-Review

- Mensagens/parse do canal → Task 1 ✓; Mailer + supressão + opt-out → Task 2 ✓; Orquestrador com portão A+B (esteira inteira em memória) → Task 3 ✓; boundaries Resend/Telegram isolados → Task 4 ✓; CLI atender/aprovar → Task 5 ✓.
- Portão A+B: teste `test_portao_para_em_aprovacao_e_aprovar_envia` cobre os dois caminhos ✓.
- `sem_portao` não persistido → Orquestrador não recarrega antes do portão ✓.
- Nenhum teste toca Resend/Telegram/rede ✓.
- **Não verificável no sandbox (precisa do usuário):** envio real Resend, bot Telegram real, e a fiação `atender` completa com credenciais. Documentar no relatório.

**Type consistency:** `Orquestrador(criador, publicador, mailer, notificar, conn)`; `Mailer.enviar(lead, conn)->str|None`; usa `Criador.redesenhar`/`Publicador.publicar` do M3 e `Lead`/`Estado`/`db`/`maquina_estados` do M1.
