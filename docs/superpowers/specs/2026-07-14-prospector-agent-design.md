# Prospector Agent — Design

- **Data:** 2026-07-14
- **Status:** aprovado (design); pendente plano de implementação
- **Runtime decidido:** B — núcleo determinístico em Python + `claude -p` só nas fases inteligentes
- **Referência:** `~/projetos/vendasite/prospector-de-sites` (plugin Claude Code atual; usado só como referência, não reaproveitado inteiro)

## 1. Contexto e motivação

O plugin atual (`prospector-de-sites`) roda o ciclo de prospecção e venda de sites como um **plugin interativo do Claude Code**: o usuário dispara cada comando (`/prospectar`, `/redesenhar`, `/publicar`, `/proposta`…), a busca no Maps é feita por **automação de navegador (Claude in Chrome)**, a publicação vai pra **HostGator via FTP** e a proposta vira **rascunho no Gmail**.

Objetivo do projeto novo: transformar isso numa **esteira semi-autônoma** operada por um **orquestrador + subagentes**, tirando a HostGator, publicando em **GitHub Pages**, enviando por **Resend** e sendo operada por um **bot de Telegram** (notificação + aprovação). Autonomia configurável: por padrão pausa e pede OK antes do envio; um flag no pedido deixa rodar sozinho.

### Goals
- Esteira completa: descobrir → qualificar → redesenhar → publicar → (portão) → enviar → acompanhar.
- Núcleo determinístico e testável; LLM só onde há julgamento/criação.
- Providers de descoberta plugáveis (browser agora; API oficial/terceiro depois).
- Portabilidade de topologia: local (A) → híbrido VPS (B) → tudo VPS (C), sem reescrever.
- Autonomia configurável (portão A+B) controlada por código.
- Operação e aprovação por Telegram.

### Non-goals (v1)
- Rodar o scraping de navegador headless numa VPS (captcha) — fica pra v2 com provider de API.
- Repo-por-cliente para todos os leads — só na conversão.
- Escala de e-mail em massa — volume baixo e aquecido, por entregabilidade/LGPD.

## 2. Princípios de design

1. **Controle determinístico em código; inteligência só onde precisa.** Máquina de estados, fila e portão são Python puro. O modelo (`claude -p`) entra em 2 pontos: *julgar site ruim* e *redesenhar*. `git push`, Resend e Telegram são chamadas diretas, sem gastar token.
2. **Providers plugáveis.** Descoberta é uma interface; troca de browser → API por config, sem reescrever o orquestrador.
3. **Portabilidade de topologia.** Mesmo código roda A → B → C; muda só onde roda e qual provider está ligado.
4. **Autonomia configurável (portão A+B).** Padrão: pausa e pede OK no Telegram antes do envio. Flag no pedido (`--auto`) pula o portão.
5. **Estado sobrevive a tudo.** Estado em SQLite; reinício retoma de onde parou. Idempotente por `slug`.

## 3. Arquitetura de alto nível

```
                    ┌─────────────── BOT TELEGRAM ───────────────┐
                    │  comandos: /prospectar, /status, /auto      │
                    │  portão: [Aprovar] [Rejeitar]  + alertas     │
                    └───────────────┬─────────────────────────────┘
                                    │
        ┌───────────────── ORQUESTRADOR (Python) ─────────────────┐
        │  scheduler (cron)  +  máquina de estados  +  fila         │
        └───┬──────┬──────────┬───────────┬─────────┬──────────────┘
            │      │          │           │         │
        descoberta qualif.  criação    publicação  envio      (estado: SQLite)
        (provider) (LLM)    (LLM)      (git→Pages) (Resend)     + dashboard local
```

Os "agentes" = os pontos **qualificação** e **criação** (invocações `claude -p` com skills distintas). O orquestrador é o maestro determinístico.

## 4. Componentes

Cada unidade tem propósito único, interface definida e dependências explícitas.

| Componente | O que faz | Interface | Depende de |
|---|---|---|---|
| **Orquestrador** | daemon: scheduler + fila + máquina de estados | `avancar(lead)` por estado | Store, Telegram, providers |
| **Store (SQLite)** | estado de cada lead + histórico | `salvar/ler/atualizar(lead)` | reusa schema do `prospector.db` |
| **Descoberta** (provider) | acha candidatos no Maps + filtros baratos (nota ≥ 4.7, ≥ 40 aval., tem site) | `descobrir(nicho, cidade, filtros) → [Candidato]` | v1: Playwright; v2: Places/SerpAPI |
| **Qualificador** (LLM) | julga "site ruim?" + motivo; extrai e-mail/WhatsApp; sem e-mail → descarta | `qualificar(Candidato) → Lead \| None` | `claude -p` + skill |
| **Criador** (LLM) | redesenha a página premium (mantém logo/cores/conteúdo reais) | `redesenhar(Lead) → arquivos em site/[slug]/` | `claude -p` + skill `redesign-premium` |
| **Publicador** | sobe o site + página-capa antes/depois | `publicar(slug) → URL pública HTTPS` | git + GitHub Pages |
| **Mailer** | manda a proposta; opt-out/supressão/bounce | `enviar(Lead) → message_id` | Resend API |
| **Bot Telegram** | comandos de entrada + portão + notificações | polling; callbacks de botão | python-telegram-bot |
| **Config/Secrets** | prefs (não-secreto) + tokens (git-ignored) | `config.json` + `.env` | — |
| **Dashboard** | CRM local (kanban/funil/financeiro) | reusa quase 100% do atual | Store |

### Contrato de descoberta (o ponto plugável)

```
Candidato = { nome, nota, avaliacoes, telefone, whatsapp?, site_url, fonte }
DiscoveryProvider.descobrir(nicho, cidade, filtros) -> list[Candidato]
```

- **Descoberta** = achar + filtros baratos (rating/reviews/tem-site), SEM LLM.
- **Qualificação** = julgar qualidade do site + extrair contatos, com LLM, **provider-agnóstica**.

Assim o browser (v1) e a API (v2) entregam o mesmo `Candidato`; o julgamento "site ruim" é uniforme, venha de onde vier.

## 5. Fluxo de dados (ciclo de vida do lead)

```
descoberto → qualificado → redesenhado → publicado → [PORTÃO] → enviado → respondido → fechado
     └────────── descartado (sem site / site bom / sem e-mail)     └─ erro (com motivo + alerta)
```

Cada seta é uma transição **idempotente**: se já foi feita, pula. O **[PORTÃO]** entre `publicado` e `enviado` é o único ponto de humano — e some quando o pedido veio com `--auto`.

Estados persistidos no Store: `descoberto, qualificado, redesenhado, publicado, aguardando_aprovacao, enviado, respondido, fechado, descartado, erro`.

## 6. Modelo de autonomia (portão A+B)

- **Default (A, semi-auto):** ao chegar em `publicado`, o orquestrador envia no Telegram: *"Lead X pronto — preview: <url>. Aprovar envio?"* com botões **[Aprovar] [Rejeitar]**. Só envia com o clique.
- **Override (B, full-auto):** `/prospectar nutri Bauru --auto` (ou `/auto on`) marca a run com `sem_portao = true` → aprova sozinho e só **notifica** o envio.
- Portão é **código puro** (`if lead.sem_portao or aprovado_no_telegram`), 100% sob controle e testável — não depende de callback de agente.

## 7. Publicação — GitHub Pages (substitui HostGator)

Casa com a regra do usuário "publicação = SEMPRE via git": o publicador faz `git push`, o Pages faz deploy pelo webhook. Fim do FTP em texto puro.

**Estratégia em 2 níveis:**
- **Preview (antes de fechar):** monorepo `usuario.github.io/prospector-sites/[slug]/`. Simples, HTTPS automático, 1 repo, 1 config. URL de subpasta serve pra preview de cold-email.
- **Na conversão (cliente comprou):** migra o site pra repo próprio + domínio custom (`cliente.com.br`), isolado e entregável, com HTTPS custom.

Não cria dezenas de repos pra leads que talvez nem respondam — só promove quem fecha.

## 8. E-mail — Resend (substitui rascunho Gmail)

O portão do Telegram **substitui** o "humano manda o rascunho" que o Gmail fazia. Guardrails (cold outbound é campo minado):
- **Domínio dedicado** só pro cold (nunca o principal) + SPF/DKIM/DMARC.
- **Throttle** (volume/dia baixo, aquecimento) e **1 e-mail por lead** (nunca repete).
- **Opt-out/descadastro** no rodapé (LGPD) + **lista de supressão** (nunca reenvia a quem saiu ou deu bounce).
- **Webhooks de bounce/reclamação** → atualiza estado + supressão.
- CTA único = link da página-capa (mantém o padrão anti-spam atual).

## 9. Erros e resiliência

- **Idempotência** por `slug`: cada fase checa "já fiz?" antes de refazer.
- **Retry com backoff** em rede/API (Resend, GitHub, descoberta).
- **Estado `erro`** com motivo → alerta no Telegram → comando manual `/retry <slug>`.
- **Captcha (modo browser):** pausa o lead → *"resolve o captcha e manda /continuar"*. É a razão de A rodar na máquina do usuário (Firefox logado).
- **Crash recovery:** estado no SQLite → o daemon retoma do último estado ao reiniciar.
- **Rate-limit:** throttle na descoberta (evita ban do Maps) e no envio (entregabilidade).

## 10. Segurança e segredos

- Tokens (`ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) em `.env` git-ignored — nunca em log, nunca no chat.
- `GITHUB_TOKEN` com escopo mínimo (repo/pages).
- Preferências não-secretas em `config.json` versionável.
- **Modo dry-run** (§11) pra nunca enviar e-mail real por acidente.

## 11. Testes

- **Núcleo determinístico é unit-testável:** máquina de estados (transições), portão (lógica A+B), publicador (contra repo git temporário), mailer (Resend sandbox/mock + supressão), config, providers atrás de fakes.
- **Dry-run mode:** roda a esteira inteira sem publicar nem enviar (loga o que faria) — essencial num sistema que dispara e-mail real.
- **Smoke do criador:** valida que sai HTML válido (output de LLM não dá pra golden-test).

## 12. Estrutura do projeto

```
prospector-agent/
  pyproject.toml
  .env.example        config.example.json        README.md
  orquestrador/   maquina_estados.py  fila.py  orquestrador.py
  descoberta/     base.py  navegador.py  (places_api.py = stub v2)
  qualificacao/   qualificador.py
  criacao/        criador.py
  publicacao/     github_pages.py
  envio/          resend_mailer.py
  canal/          telegram_bot.py
  estado/         db.py
  dashboard/      (reusa o dashboard atual)
  skills/         redesign-premium/ …  (SKILL.md, adaptadas da referência)
  .claude/        settings (p/ o claude -p achar as skills)
  tests/          test_maquina_estados.py  test_publicacao.py  test_envio.py …
  docs/superpowers/specs/2026-07-14-prospector-agent-design.md  (este doc)
```

## 13. Roadmap

| Versão | Topologia | Descoberta | Entrega |
|---|---|---|---|
| **v1** | A (local) | browser (usuário resolve captcha) | esteira completa + portão + dashboard |
| **v1.x** | B (híbrido) | browser local → empurra pra VPS | orquestrador/bot/publish/mail na VPS |
| **v2** | C (tudo VPS) | Places API / terceiro (plugável) | zero browser, repo-por-cliente na conversão |

## 14. Decisões e defaults

- **Nome/local:** `~/projetos/prospector-agent` (repo novo, irmão do `vendasite`).
- **Publicação:** monorepo pra preview, repo-próprio na conversão (§7).
- **Telegram:** long-polling (funciona local e VPS, sem webhook público).
- **Descoberta v1:** Playwright (reusa a lógica da skill atual).
- **Reuso:** dashboard e skill de redesign vêm da referência, adaptadas.
- **Linguagem:** Python (casa com scripts atuais e libs de Resend/Telegram/Playwright/GitHub).

## 15. Questões em aberto (resolver no plano de implementação)

- Flags exatos do `claude -p` para rodar headless com auto-aprovação e enxergar as skills do projeto.
- Mecanismo de push do Publicador: `git` CLI num clone local do monorepo vs. GitHub API (contents).
- Como o modo B sincroniza os leads do scanner local com a VPS (fila remota vs. push HTTP).
- Domínio de envio do Resend e processo de aquecimento.
- Reaproveitamento exato do schema/`dashboard.html` da referência.
