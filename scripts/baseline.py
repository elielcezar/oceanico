#!/usr/bin/env python3
"""
Reconstrói uma página como ela estava em um commit e tira o screenshot dela.

    python scripts/baseline.py produto.html reference/produto_base.png
    python scripts/baseline.py produto.html reference/antes.png --ref HEAD~3

Serve para comparar o antes e o depois de uma refatoração. O ideal é capturar
a baseline ANTES de editar (aí basta o scripts/shot.py); este script existe
para quando a edição já começou — ou para reconferir uma página muito depois,
sem precisar guardar PNG nenhum no repositório.

Como funciona: extrai o HTML da página e a pasta css/ inteira do commit para
tmp/_baseline/, ajusta os caminhos relativos para apontarem de volta para os
assets/js/fonts da árvore de trabalho, e chama o shot.py.
"""

import pathlib
import re
import shutil
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "tmp" / "_baseline"


def git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",  # o padrão do Windows é cp1252 e quebra nos acentos
        errors="replace",
    )
    if r.returncode:
        sys.exit(f"erro no git: {' '.join(args)}\n{(r.stderr or '').strip()}")
    return r.stdout


def main() -> None:
    argv = [a for a in sys.argv[1:] if a != "--ref"]
    ref = "HEAD"
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
        argv = argv[:-1]

    if len(argv) < 2:
        sys.exit("uso: baseline.py <pagina.html> <saida.png> [largura=402] [--ref COMMIT]")

    pagina, saida = argv[0], argv[1]
    largura = argv[2] if len(argv) > 2 else "402"

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    (DESTINO / "css").mkdir(parents=True)

    # A página, com assets/js apontando para a árvore de trabalho.
    html = git("show", f"{ref}:{pagina}")
    # poster= também aponta para assets/. Sem incluí-lo aqui o vídeo do baseline
    # fica sem quadro de capa e a comparação acusa uma diferença que não existe.
    html = re.sub(r'((?:src|href|poster)=")(assets/|js/)', r"\1../../\2", html)
    (DESTINO / pathlib.Path(pagina).name).write_text(html, encoding="utf-8")

    # Todo o css/ do mesmo commit — a página costuma usar mais de um arquivo.
    for linha in git("ls-tree", "--name-only", f"{ref}:css").splitlines():
        if not linha.strip():
            continue
        css = git("show", f"{ref}:css/{linha.strip()}")
        # ../fonts/ passa a estar dois níveis mais fundo.
        css = re.sub(r'(url\(\s*["\']?)\.\./', r"\1../../../", css)
        (DESTINO / "css" / linha.strip()).write_text(css, encoding="utf-8")

    alvo = DESTINO / pathlib.Path(pagina).name
    print(f"{pagina} @ {ref} reconstruída em {alvo.relative_to(RAIZ)}")
    subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "shot.py"), str(alvo), saida, largura],
        cwd=RAIZ,
        check=True,
    )


if __name__ == "__main__":
    main()
