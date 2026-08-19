#!/usr/bin/env python3
"""
Aponta ONDE um bloco diverge do Figma, em faixas de linhas.

    python scripts/faixas.py m-bloco3
    python scripts/faixas.py d-bloco8 --limite 20

Le o lado-a-lado que o scripts/conferir_figma.py gravou em reference/cmp/,
separa as duas metades e lista as faixas de y com divergencia acima do limite,
junto da extensao horizontal onde ela se concentra. E o passo entre "o bloco
tem 12% de diferenca" e "o problema esta nesta linha, nesta coluna".
"""

import pathlib
import sys

import numpy as np
from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SEPARADOR = 12
LIMIAR_PIXEL = 24


def carrega(slug):
    ref = Image.open(RAIZ / "reference" / "blocos" / (slug + ".png")).convert("RGB")
    par = Image.open(RAIZ / "reference" / "cmp" / (slug + ".png")).convert("RGB")
    nosso = par.crop((ref.width + SEPARADOR, 0, par.width, ref.height))
    altura = min(ref.height, nosso.height)
    a = np.asarray(ref, dtype=np.int16)[:altura]
    b = np.asarray(nosso, dtype=np.int16)[:altura]
    return a, b


def main():
    slug = sys.argv[1]
    limite = float(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 12.0

    a, b = carrega(slug)
    dif = np.abs(a - b).max(axis=2)
    por_linha = (dif > LIMIAR_PIXEL).mean(axis=1) * 100

    print("%s: %.1f%% divergente no total (limite de faixa: %.0f%%)"
          % (slug, (dif > LIMIAR_PIXEL).mean() * 100, limite))

    ruins = np.where(por_linha > limite)[0]
    if not ruins.size:
        print("  nenhuma faixa acima do limite")
        return

    faixas, inicio, anterior = [], None, None
    for y in ruins:
        if inicio is None:
            inicio = anterior = y
        elif y - anterior > 8:
            faixas.append((inicio, anterior))
            inicio = y
        anterior = y
    faixas.append((inicio, anterior))

    print("  %-14s %7s  %s" % ("faixa y", "media", "colunas afetadas"))
    for i0, i1 in faixas:
        colunas = np.where((dif[i0:i1 + 1] > LIMIAR_PIXEL).mean(axis=0) > 0.10)[0]
        onde = "x %d..%d" % (colunas.min(), colunas.max()) if colunas.size else "espalhado"
        print("  %5d..%-7d %6.1f%%  %s" % (i0, i1, por_linha[i0:i1 + 1].mean(), onde))


if __name__ == "__main__":
    main()
