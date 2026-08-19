#!/usr/bin/env python3
"""
Extrai os textos de um design context, na ordem em que aparecem.

    python scripts/textos_ctx.py d-bloco4

Grava em reference/figma/textos-<slug>.txt (UTF-8; o console do Windows e
cp1252 e engasga com os acentos e com caracteres invisiveis).

Marca caracteres invisiveis que mudam a quebra de linha e que passariam
despercebidos ao copiar o texto para o HTML:

    <ZWSP>  U+200B espaco de largura zero  -> &#8203;
    <NBSP>  U+00A0 espaco inquebravel      -> &nbsp;
    <NL>    quebra de linha dentro do texto
"""

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

INVISIVEIS = {
    "​": "<ZWSP>",
    " ": "<NBSP>",
    " ": "<THINSP>",
    "﻿": "<BOM>",
}


def main():
    slug = sys.argv[1]
    origem = RAIZ / "reference" / "figma" / ("ctx-%s.txt" % slug)
    bruto = origem.read_text(encoding="utf-8").split("SUPER CRITICAL")[0]

    linhas = []
    for m in re.finditer(r"<(p|h[1-6]|span|li)[^>]*>(.*?)</\1>", bruto, re.S):
        texto = re.sub(r"\{`(.*?)`\}", r"\1", m.group(2), flags=re.S)
        texto = re.sub(r"<[^>]+>", "", texto)
        texto = texto.replace("{`", "").replace("`}", "").strip()
        if not texto:
            continue
        for caractere, rotulo in INVISIVEIS.items():
            texto = texto.replace(caractere, rotulo)
        texto = texto.replace("\n", " <NL> ")
        texto = re.sub(r"[ \t]+", " ", texto)
        linhas.append(texto)  # sem dedupe: linhas repetidas (ex.: espacadores) contam

    destino = RAIZ / "reference" / "figma" / ("textos-%s.txt" % slug)
    destino.write_text("\n\n".join(linhas) + "\n", encoding="utf-8")
    print("%d textos -> %s" % (len(linhas), destino))


if __name__ == "__main__":
    main()
