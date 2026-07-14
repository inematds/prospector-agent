from __future__ import annotations
import argparse
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db
from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery
from prospector.qualificacao.qualificador import Qualificador


def caminho_dry_run(lead: Lead) -> list[Estado]:
    """Sequência de estados que o lead percorreria, respeitando o portão."""
    caminho = [Estado.DESCOBERTO, Estado.QUALIFICADO,
               Estado.REDESENHADO, Estado.PUBLICADO]
    if lead.sem_portao:
        caminho.append(Estado.ENVIADO)          # rota --auto: pula o portão
    else:
        caminho.append(Estado.AGUARDANDO_APROVACAO)
    # valida que cada passo é uma transição legal
    for de, para in zip(caminho, caminho[1:]):
        me.avancar(de, para)
    return caminho


def _cmd_demo(args: argparse.Namespace) -> int:
    lead = Lead(slug="demo-lead", nome="Lead Demo", sem_portao=args.auto)
    caminho = caminho_dry_run(lead)
    modo = "DRY-RUN" if args.dry_run else "REAL"
    print(f"[{modo}] caminho do lead '{lead.slug}' (auto={args.auto}):")
    print(" -> ".join(e.value for e in caminho))
    if not args.dry_run:
        conn = db.conectar(args.db)
        db.salvar_lead(conn, lead)
        print(f"gravado em {args.db}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    db.conectar(args.db)
    print(f"DB inicializado em {args.db}")
    return 0


def prospectar(provider, qualificador, conn, nicho, cidade, meta):
    salvos = []
    for cand in provider.descobrir(nicho, cidade, meta):
        lead = qualificador.qualificar(cand)
        if lead is not None:
            db.salvar_lead(conn, lead)
            salvos.append(lead)
    return salvos


def _cmd_prospectar(args: argparse.Namespace) -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prospector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_demo = sub.add_parser("demo", help="roda a esteira fake")
    p_demo.add_argument("--dry-run", action="store_true")
    p_demo.add_argument("--auto", action="store_true", help="pula o portão")
    p_demo.add_argument("--db", default="prospector.db")
    p_demo.set_defaults(func=_cmd_demo)

    p_init = sub.add_parser("init", help="cria o DB vazio")
    p_init.add_argument("--db", default="prospector.db")
    p_init.set_defaults(func=_cmd_init)

    p_pros = sub.add_parser("prospectar", help="busca e qualifica leads")
    p_pros.add_argument("nicho")
    p_pros.add_argument("cidade")
    p_pros.add_argument("--provider", choices=["fake", "navegador"], default="fake")
    p_pros.add_argument("--meta", type=int, default=10)
    p_pros.add_argument("--db", default="prospector.db")
    p_pros.set_defaults(func=_cmd_prospectar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
