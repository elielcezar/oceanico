#!/usr/bin/env python3
"""
Puxa design context + screenshot de cada bloco da landing no Figma.

    python scripts/figma_lote.py

Grava em reference/figma/:
    ctx-<slug>.txt   codigo de referencia + medidas do bloco
    shot-<slug>.png  screenshot do bloco (teto de 1024px do servidor)

E resumivel: pula o que ja existe em disco, entao pode rodar de novo depois
de uma interrupcao sem refazer o que ja veio. get_design_context leva ~1-2min
por bloco, por isso o lote roda em background.
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figma_mcp

DESTINO = pathlib.Path("reference/figma")

DESKTOP = [
    ("134:6250", "d-logo"),
    ("134:6252", "d-bloco1"),
    ("134:6306", "d-bloco3"),
    ("134:6326", "d-bloco4"),
    ("134:6331", "d-bloco5"),
    ("134:6353", "d-bloco6"),
    ("134:6375", "d-bloco8"),
    ("134:6430", "d-bloco9"),
    ("134:6451", "d-bloco10"),
    ("134:6485", "d-bloco11"),
    ("134:6493", "d-bloco-final"),
    ("134:6524", "d-rodape"),
]

MOBILE = [
    ("176:1514", "m-logo"),
    ("176:1516", "m-bloco1"),
    ("176:1525", "m-bloco3"),
    ("176:1584", "m-bloco4"),
    ("176:1589", "m-lembrese"),
    ("185:1789", "m-bloco5"),
    ("185:1835", "m-bloco6"),
    ("176:1629", "m-bloco8"),
    ("176:1684", "m-bloco9"),
    ("176:1705", "m-bloco10"),
    ("176:1776", "m-bloco11"),
    ("189:2013", "m-bloco-final"),
]

COMUM = {
    "clientLanguages": "html,css,javascript",
    "clientFrameworks": "none",
}


def puxa(node_id, slug):
    ctx = DESTINO / ("ctx-" + slug + ".txt")
    shot = DESTINO / ("shot-" + slug + ".png")

    if not shot.exists():
        try:
            figma_mcp.chama("get_screenshot", {"nodeId": node_id}, str(shot))
        except SystemExit as erro:
            print("  !! screenshot " + slug + ": " + str(erro))

    if ctx.exists():
        print("  (ctx ja existe) " + slug)
        return
    inicio = time.time()
    argumentos = dict(COMUM)
    argumentos.update(
        {
            "nodeId": node_id,
            "artifactType": "WEB_PAGE_OR_APP_SCREEN",
            "taskType": "CREATE_ARTIFACT",
        }
    )
    try:
        figma_mcp.chama("get_design_context", argumentos, str(ctx))
    except SystemExit as erro:
        print("  !! context " + slug + ": " + str(erro))
    print("  %s em %.0fs" % (slug, time.time() - inicio))


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    alvos = DESKTOP + MOBILE
    if len(sys.argv) > 1 and sys.argv[1] == "mobile":
        alvos = MOBILE
    elif len(sys.argv) > 1 and sys.argv[1] == "desktop":
        alvos = DESKTOP
    for i, (node_id, slug) in enumerate(alvos, 1):
        print("[%d/%d] %s %s" % (i, len(alvos), slug, node_id), flush=True)
        puxa(node_id, slug)
    print("lote concluido")
