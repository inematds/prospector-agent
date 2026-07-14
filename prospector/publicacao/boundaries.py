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
