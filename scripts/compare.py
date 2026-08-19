#!/usr/bin/env python3
"""
Compara duas capturas da mesma pagina (original x refatorada).

    python scripts/compare.py reference/base.png reference/novo.png reference/cmp 800

Faz duas coisas:

1. Gera fatias lado a lado em <saida>/fatia_NNN.png (original a esquerda,
   render a direita) para inspecao visual.
2. Imprime medicoes: diferenca de altura, % de pixels divergentes por fatia e
   as faixas de linhas onde a extensao horizontal do conteudo nao-branco
   diverge — e isso que denuncia deslocamento para esquerda/direita.
"""

import pathlib
import sys

import numpy as np
from PIL import Image

LIMIAR_BRANCO = 244  # acima disso trata como fundo
LIMIAR_PIXEL = 12  # diferenca por canal que conta como divergencia
TOLERANCIA_EXTENSAO = 2  # px de folga na extensao horizontal
SEPARADOR = 16  # px de faixa entre as duas colunas da fatia


def carrega(caminho: str) -> np.ndarray:
    p = pathlib.Path(caminho)
    if not p.exists():
        sys.exit(f"erro: nao encontrei {p}")
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.int16)


def extensao_nao_branca(img: np.ndarray):
    """Para cada linha, devolve (primeira_coluna, ultima_coluna) nao-branca."""
    conteudo = (img < LIMIAR_BRANCO).any(axis=2)
    tem = conteudo.any(axis=1)
    primeira = np.where(tem, conteudo.argmax(axis=1), -1)
    ultima = np.where(tem, img.shape[1] - 1 - conteudo[:, ::-1].argmax(axis=1), -1)
    return primeira, ultima


def agrupa_faixas(linhas: np.ndarray, salto: int = 4):
    """Agrupa numeros de linha consecutivos em faixas (inicio, fim)."""
    if linhas.size == 0:
        return []
    faixas = []
    inicio = anterior = int(linhas[0])
    for n in linhas[1:]:
        n = int(n)
        if n - anterior > salto:
            faixas.append((inicio, anterior))
            inicio = n
        anterior = n
    faixas.append((inicio, anterior))
    return faixas


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit("uso: compare.py <original.png> <render.png> <dir_saida> [altura_fatia=800]")

    a_path, b_path, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    altura_fatia = int(sys.argv[4]) if len(sys.argv) > 4 else 800

    a, b = carrega(a_path), carrega(b_path)
    dir_saida = pathlib.Path(saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"original : {a.shape[1]}x{a.shape[0]}  {a_path}")
    print(f"render   : {b.shape[1]}x{b.shape[0]}  {b_path}")

    if a.shape[1] != b.shape[1]:
        print(f"\n!! larguras diferentes ({a.shape[1]} vs {b.shape[1]}) — capture as duas na mesma largura")

    delta_altura = b.shape[0] - a.shape[0]
    if delta_altura:
        print(f"\n!! ALTURA: render esta {abs(delta_altura)}px "
              f"{'MAIOR' if delta_altura > 0 else 'MENOR'} que o original")
    else:
        print("\nALTURA: identica")

    altura = min(a.shape[0], b.shape[0])
    largura = min(a.shape[1], b.shape[1])
    ac, bc = a[:altura, :largura], b[:altura, :largura]

    # --- divergencia por fatia -------------------------------------------
    difere = (np.abs(ac - bc) > LIMIAR_PIXEL).any(axis=2)
    total = 100.0 * difere.mean()
    print(f"pixels divergentes (area comum): {total:.2f}%\n")

    print("fatia  linhas            divergencia")
    for i, topo in enumerate(range(0, altura, altura_fatia)):
        base = min(topo + altura_fatia, altura)
        pct = 100.0 * difere[topo:base].mean()
        marca = "   <<<" if pct > 1.0 else ""
        print(f"{i:>4}   {topo:>6}-{base:<10} {pct:>6.2f}%{marca}")

    # --- deslocamento horizontal -----------------------------------------
    a_ini, a_fim = extensao_nao_branca(ac)
    b_ini, b_fim = extensao_nao_branca(bc)

    ambas = (a_ini >= 0) & (b_ini >= 0)
    desloca_esq = ambas & (np.abs(a_ini - b_ini) > TOLERANCIA_EXTENSAO)
    desloca_dir = ambas & (np.abs(a_fim - b_fim) > TOLERANCIA_EXTENSAO)

    for nome, mascara, orig, novo in (
        ("BORDA ESQUERDA", desloca_esq, a_ini, b_ini),
        ("BORDA DIREITA", desloca_dir, a_fim, b_fim),
    ):
        faixas = agrupa_faixas(np.where(mascara)[0])
        if not faixas:
            print(f"\n{nome}: alinhada em toda a pagina")
            continue
        print(f"\n{nome}: {len(faixas)} faixa(s) divergente(s)")
        for ini, fim in faixas[:25]:
            d = int(np.median(novo[ini:fim + 1] - orig[ini:fim + 1]))
            print(f"  linhas {ini:>6}-{fim:<6} desvio mediano {d:+d}px")
        if len(faixas) > 25:
            print(f"  … e mais {len(faixas) - 25} faixa(s)")

    # --- fatias lado a lado ----------------------------------------------
    for arquivo in dir_saida.glob("fatia_*.png"):
        arquivo.unlink()

    for i, topo in enumerate(range(0, altura, altura_fatia)):
        base = min(topo + altura_fatia, altura)
        h = base - topo
        tela = Image.new("RGB", (largura * 2 + SEPARADOR, h), (255, 0, 255))
        tela.paste(Image.fromarray(ac[topo:base].astype(np.uint8)), (0, 0))
        tela.paste(Image.fromarray(bc[topo:base].astype(np.uint8)), (largura + SEPARADOR, 0))
        tela.save(dir_saida / f"fatia_{i:03d}.png")

    print(f"\nfatias em {dir_saida}/ (esquerda = original, direita = render)")


if __name__ == "__main__":
    main()
