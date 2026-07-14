# Prospector Agent

Esteira **semi-autônoma** de prospecção e venda de sites: descobre negócios bem avaliados com site ruim, redesenha a página, publica e envia a proposta — operada por um **bot de Telegram**, com um **orquestrador** determinístico e **subagentes** de IA só onde há julgamento/criação.

> **Status:** fase de design. Nada implementado ainda.
> Design completo: [`docs/superpowers/specs/2026-07-14-prospector-agent-design.md`](docs/superpowers/specs/2026-07-14-prospector-agent-design.md)

## A esteira

```
descoberto → qualificado → redesenhado → publicado → [PORTÃO] → enviado → respondido → fechado
```

| Fase | O que faz | Como |
|---|---|---|
| **Descoberta** | acha candidatos no Google Maps (nota ≥ 4.7, com site) | provider plugável (browser → API) |
| **Qualificação** | julga "site ruim?" + extrai e-mail/WhatsApp | `claude -p` + skill |
| **Criação** | redesenha a página premium (logo/cores/conteúdo reais) | `claude -p` + skill `redesign-premium` |
| **Publicação** | sobe o site + página-capa antes/depois | `git push` → GitHub Pages |
| **Portão** | pede aprovação antes de enviar (ou pula com `--auto`) | Telegram |
| **Envio** | manda a proposta (anti-spam, opt-out) | Resend |
| **Acompanhamento** | respostas, follow-up, dashboard | Store local (SQLite) |

## Princípios

- **Controle determinístico em código; IA só onde precisa.** Fila, máquina de estados e portão são Python; o modelo entra só em *qualificar* e *redesenhar*.
- **Providers plugáveis** — browser agora, Places API / terceiros depois, sem reescrever.
- **Portável** — roda local (A) → híbrido VPS (B) → tudo VPS (C) só trocando config.
- **Autonomia configurável** — padrão com portão de aprovação; flag deixa rodar sozinho.

## Roadmap

| Versão | Onde roda | Descoberta |
|---|---|---|
| **v1** | local | browser (você resolve captcha) |
| **v1.x** | híbrido VPS | browser local → VPS |
| **v2** | tudo VPS | Places API / terceiro |

## Referência

Baseado no plugin Claude Code `prospector-de-sites` (em `../vendasite`), usado só como referência.

---

_README inicial — será enriquecido (instalação, configuração, uso) quando a implementação começar._
