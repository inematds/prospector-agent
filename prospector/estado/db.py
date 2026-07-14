from __future__ import annotations
import sqlite3
from prospector.modelos import Lead, CAMPOS

_COLS_SQL = """
  slug TEXT PRIMARY KEY, nome TEXT, nicho TEXT, cidade TEXT, nota REAL,
  avaliacoes INTEGER, email TEXT, telefone TEXT, whatsapp TEXT, siteAntigo TEXT,
  motivo TEXT, status TEXT DEFAULT 'descoberto', urlNova TEXT, dataProposta TEXT,
  valor REAL, obs TEXT, contratoStatus TEXT, contratoEm TEXT, manutencao REAL,
  pago INTEGER, docCliente TEXT, endCliente TEXT,
  atualizado TEXT DEFAULT (datetime('now','localtime'))
"""


def conectar(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(f"CREATE TABLE IF NOT EXISTS leads({_COLS_SQL})")
    conn.commit()
    return conn


def salvar_lead(conn: sqlite3.Connection, lead: Lead) -> None:
    d = lead.para_dict()
    valores = [d.get(c) for c in CAMPOS]
    placeholders = ",".join("?" * len(CAMPOS))
    updates = ",".join(f"{c}=excluded.{c}" for c in CAMPOS if c != "slug")
    conn.execute(
        f"INSERT INTO leads ({','.join(CAMPOS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(slug) DO UPDATE SET {updates}, "
        f"atualizado=datetime('now','localtime')",
        valores,
    )
    conn.commit()


def ler_lead(conn: sqlite3.Connection, slug: str) -> Lead | None:
    row = conn.execute("SELECT * FROM leads WHERE slug=?", (slug,)).fetchone()
    return Lead.de_dict(dict(row)) if row else None


def atualizar_status(conn: sqlite3.Connection, slug: str, status: str) -> None:
    conn.execute(
        "UPDATE leads SET status=?, atualizado=datetime('now','localtime') "
        "WHERE slug=?",
        (status, slug),
    )
    conn.commit()


def listar_por_status(conn: sqlite3.Connection, status: str) -> list[Lead]:
    rows = conn.execute("SELECT * FROM leads WHERE status=?", (status,)).fetchall()
    return [Lead.de_dict(dict(r)) for r in rows]
