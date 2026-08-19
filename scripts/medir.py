#!/usr/bin/env python3
"""
Mede as caixas reais dos elementos da pagina, na largura pedida.

    python scripts/medir.py 375 ".hero, .hero__texto, .hero__foto"
    python scripts/medir.py 1280 ".hero *"

Imprime x, y (absolutos na pagina), largura e altura de cada elemento que
casar com o seletor. Serve para achar o pixel que sobra sem ficar no chute.
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent

MEDE = """
(seletor) => Array.from(document.querySelectorAll(seletor)).map(el => {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return {
    tag: el.tagName.toLowerCase(),
    classe: (el.className || '').toString().slice(0, 42),
    x: +r.x.toFixed(2), y: +(r.y + window.scrollY).toFixed(2),
    largura: +r.width.toFixed(2), altura: +r.height.toFixed(2),
    fonte: cs.fontSize + '/' + cs.lineHeight,
    cor: cs.color,
  };
})
"""


def main():
    largura = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
    seletor = sys.argv[2] if len(sys.argv) > 2 else "[data-bloco]"
    pagina_html = RAIZ / (sys.argv[3] if len(sys.argv) > 3 else "index.html")

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": largura, "height": 900})
        pagina.goto(pagina_html.as_uri(), wait_until="load")
        pagina.wait_for_timeout(300)
        caixas = pagina.evaluate(MEDE, seletor)
        navegador.close()

    print("%-6s %-44s %8s %8s %9s %9s  %s" % ("tag", "classe", "x", "y", "largura", "altura", "fonte"))
    for c in caixas:
        print("%-6s %-44s %8.2f %8.2f %9.2f %9.2f  %s %s"
              % (c["tag"], c["classe"], c["x"], c["y"], c["largura"], c["altura"], c["fonte"], c["cor"]))


if __name__ == "__main__":
    main()
