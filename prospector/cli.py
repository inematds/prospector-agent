from __future__ import annotations
import argparse
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db


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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
