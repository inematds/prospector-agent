# Prospector Agent

Esteira **semi-autônoma** de prospecção e venda de sites: descobre negócios bem avaliados com site ruim, redesenha a página, publica e envia a proposta — operada por um **bot de Telegram**, com um **orquestrador** determinístico e **IA (`claude -p`) só onde há julgamento/criação**.

> **Status:** **v1 (núcleo determinístico) construído e testado — 47 testes verdes.**
> As integrações externas (Google Maps, `claude -p`, Resend, Telegram, deploy GitHub Pages) estão implementadas atrás de interfaces, mas **rodar ao vivo depende das suas credenciais** (ver "O que falta").
> Design: [`docs/superpowers/specs/2026-07-14-prospector-agent-design.md`](docs/superpowers/specs/2026-07-14-prospector-agent-design.md) · Planos: [`docs/superpowers/plans/`](docs/superpowers/plans/)

## A esteira

```
descoberto → qualificado → redesenhado → publicado → [PORTÃO] → enviado → respondido → fechado
```

| Fase | O que faz | Como | Milestone |
|---|---|---|---|
| **Descoberta** | acha candidatos no Maps (nota ≥ 4.7, com site) | provider plugável (`fake` / `navegador` Playwright) | M2 |
| **Qualificação** | julga "site ruim?" + extrai e-mail/WhatsApp | `claude -p` injetável | M2 |
| **Criação** | redesenha a página premium + capa antes/depois | `claude -p` injetável | M3 |
| **Publicação** | sobe o site + calcula a URL | `git push` → GitHub Pages | M3 |
| **Portão** | pede aprovação antes de enviar (ou pula com `--auto`) | Telegram | M4 |
| **Envio** | manda a proposta (opt-out, supressão, 1-por-lead) | Resend injetável | M4 |
| **Orquestrador** | conduz o lead pela máquina de estados, aplica o portão | núcleo determinístico | M4 |

## Como rodar (v1)

Requer Python 3.11+ e `pytest`.

```bash
# 1. suíte completa (núcleo determinístico, sem rede)
python3 -m pytest -q                       # 47 passed

# 2. esteira fake ponta a ponta (dry-run, não toca disco/rede)
python3 -m prospector demo --dry-run --auto        # → ... → enviado
python3 -m prospector demo --dry-run               # → ... → aguardando_aprovacao

# 3. prospecção com provider fake (sem credenciais)
python3 -m prospector prospectar nutricionistas Bauru --provider fake --db /tmp/pa.db
```

Comandos que dependem de credenciais reais (ver abaixo): `prospectar --provider navegador`, `redesenhar <slug>`, `publicar <slug>`, `aprovar <slug>`, `atender`.

## O que falta (ligar as credenciais)

O núcleo está testado; as **pontas externas** precisam do seu ambiente para rodar ao vivo:

- **`ANTHROPIC_API_KEY`** — `claude -p` (qualificar + redesenhar). Requer o Claude Code CLI instalado.
- **Google Maps** — `--provider navegador` usa Playwright (`pip install playwright && playwright install chromium`); captcha exige você por perto (v1 local).
- **`RESEND_API_KEY`** + domínio de envio dedicado (SPF/DKIM) — envio da proposta.
- **`TELEGRAM_BOT_TOKEN`** + **`TELEGRAM_CHAT_ID`** — bot do portão/notificações.
- **Repo Pages** (monorepo `prospector-sites`) + **`GITHUB_TOKEN`** — publicação.

Copie `.env.example` → `.env` e preencha. Nada disso vai para o git (`.gitignore`).

## Princípios

- **Controle determinístico em código; IA só onde precisa.** Fila, máquina de estados e portão são Python testável; o modelo entra só em *qualificar* e *redesenhar*.
- **Limites externos injetáveis** — browser, `claude -p`, Resend, Telegram e `git push` entram por interface, então o núcleo é 100% testável sem rede/credenciais.
- **Providers plugáveis** — descoberta troca de browser para API sem reescrever.
- **Portável** — roda local (A) → híbrido VPS (B) → tudo VPS (C) só trocando config.
- **Autonomia configurável** — padrão com portão de aprovação; `--auto` deixa rodar sozinho.

## Roadmap

| Versão | Onde roda | Descoberta | Status |
|---|---|---|---|
| **v1** | local | browser (você resolve captcha) | núcleo ✅ · integrações dependem de credenciais |
| **v1.x** | híbrido VPS | browser local → VPS | planejado |
| **v2** | tudo VPS | Places API / terceiro | planejado |

## Referência

Baseado no plugin Claude Code `prospector-de-sites` (em `../vendasite`), usado só como referência.

---

_Guia landing: https://inematds.github.io/prospector-agent/guia/_
