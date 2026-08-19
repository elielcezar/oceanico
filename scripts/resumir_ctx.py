#!/usr/bin/env python3
"""
Condensa um design context do Figma no que interessa para escrever o CSS.

    python scripts/resumir_ctx.py d-bloco3
    python scripts/resumir_ctx.py m-bloco3 --texto

O get_design_context devolve JSX com Tailwind e um rodape de instrucoes que
se repete em todo bloco. Este resumo mostra a arvore com indentacao e, de
cada elemento, so as classes de posicao, tamanho e tipografia.

Cuidado que ja custou caro: `-translate-x-1/2` comeca com hifen. Quando ele
aparece, o `left-[N]` do elemento e o CENTRO, nao a borda esquerda.
"""

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INTERESSA = re.compile(
    r"^-?(translate|absolute|relative|fixed|left-|right-|top-|bottom-|inset|w-|h-|size-"
    r"|min-w|max-w|min-h|max-h|gap|px-|py-|pl-|pr-|pt-|pb-|p-|m[xytblr]?-|text-|font-"
    r"|leading-|tracking-|bg-|border|rounded|grid|flex|items-|justify-|self-|content-"
    r"|aspect-|uppercase|italic|mix-blend|whitespace|object-|overflow|opacity|order|shrink)"
)


def resumir(slug, mostrar_texto=False):
    caminho = RAIZ / "reference" / "figma" / ("ctx-%s.txt" % slug)
    bruto = caminho.read_text(encoding="utf-8").split("SUPER CRITICAL")[0]

    for linha in bruto.split("\n"):
        t = linha.strip()
        if t.startswith("const "):
            print(t[:130])
            continue
        if not t.startswith("<"):
            if mostrar_texto and t and t not in ("</div>", "</p>", "</span>", ");", "}"):
                print("        \" " + t[:110])
            continue

        classes = re.search(r'className="([^"]*)"', linha)
        nome = re.search(r'data-name="([^"]*)"', linha)
        nid = re.search(r'data-node-id="([^"]*)"', linha)
        estilo = re.search(r'style=\{\{ ([^}]*)', linha)
        tag = t.split()[0].lstrip("<")
        recuo = " " * (len(linha) - len(linha.lstrip()))

        uteis = []
        if classes:
            uteis = [c for c in classes.group(1).split() if INTERESSA.match(c)]
        rotulo = nome.group(1)[:16] if nome else (nid.group(1) if nid else "")
        print("%s%-5s %-16s %s" % (recuo, tag, rotulo, " ".join(uteis)[:160]))
        if estilo and "backgroundImage" not in estilo.group(1):
            print("%s      estilo: %s" % (recuo, estilo.group(1)[:140]))


if __name__ == "__main__":
    resumir(sys.argv[1], "--texto" in sys.argv)
