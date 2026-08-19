#!/usr/bin/env python3
"""
Screenshot full-page de um HTML local (ou URL) numa largura exata.

    python scripts/shot.py principal.html reference/principal_base.png 402

A captura e' deterministica de proposito:

- roda com `prefers-reduced-motion: reduce`, que nas paginas desta revista
  coloca todo elemento animado no estado final (opacity 1, rotacao final) e
  desliga o parallax de js/animista-parallax.js;
- espera fontes (@font-face de fonts/) e todas as imagens carregarem;
- pausa videos no frame 0.

Sem isso, dois screenshots da mesma pagina saem diferentes e a comparacao
visual vira ruido.
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ESPERA_REDE_MS = 1500


PREPARA = """
async () => {
  // Videos: tirar do autoplay, pausar e esperar o seek ate o quadro 0 concluir.
  await Promise.all(Array.from(document.querySelectorAll('video')).map(v => {
    v.autoplay = false;
    v.pause();
    const pronto = v.readyState >= 2
      ? Promise.resolve()
      : new Promise(r => { v.addEventListener('loadeddata', r, {once:true}); setTimeout(r, 2000); });
    return pronto.then(() => {
      if (v.currentTime === 0) return;
      return new Promise(r => { v.addEventListener('seeked', r, {once:true}); setTimeout(r, 1000); v.currentTime = 0; });
    });
  }));

  // Esperar o load nao basta em <img decoding="async">: complete fica true
  // enquanto a decodificacao ainda roda, e a imagem sai em branco no
  // screenshot. img.decode() espera o quadro pronto de verdade.
  await Promise.all(Array.from(document.images).map(img =>
    (img.complete ? Promise.resolve()
                  : new Promise(r => { img.onload = img.onerror = r; }))
      .then(() => img.decode ? img.decode().catch(() => {}) : null)));

  if (document.fonts && document.fonts.ready) await document.fonts.ready;

  // js/revista-73-menu.js centraliza o item ativo do menu horizontal dentro de
  // dois requestAnimationFrame encadeados, e reagenda isso em document.fonts.ready.
  // Sem esperar por eles, a captura com fontes frias sai com o menu no comeco e
  // a seguinte sai centralizada.
  for (let i = 0; i < 3; i++) {
    await new Promise(r => requestAnimationFrame(r));
  }
}
"""


def para_url(alvo: str) -> str:
    if alvo.startswith(("http://", "https://", "file://")):
        return alvo
    caminho = pathlib.Path(alvo).resolve()
    if not caminho.exists():
        sys.exit(f"erro: nao encontrei {caminho}")
    return caminho.as_uri()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(
            "uso: shot.py <html|url> <saida.png> [largura=402] [altura_viewport=900]"
        )

    alvo, saida = sys.argv[1], sys.argv[2]
    largura = int(sys.argv[3]) if len(sys.argv) > 3 else 402
    altura = int(sys.argv[4]) if len(sys.argv) > 4 else 900

    destino = pathlib.Path(saida)
    destino.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            # imageAnimationPolicy=2 congela GIFs no primeiro quadro;
            # sem isso cada captura pega um quadro diferente.
            args=["--blink-settings=imageAnimationPolicy=2"]
        )
        pagina = navegador.new_page(
            viewport={"width": largura, "height": altura},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        pagina.goto(para_url(alvo), wait_until="load")
        try:
            pagina.wait_for_load_state("networkidle", timeout=ESPERA_REDE_MS)
        except Exception:
            pass  # video pesado pode nunca ficar idle; seguimos assim mesmo
        pagina.evaluate(PREPARA)
        # Descartavel: obriga o compositor a publicar a rolagem do menu antes
        # da captura de verdade. Ver o comentario em scripts/conferir.py.
        pagina.screenshot(clip={"x": 0, "y": 0, "width": 8, "height": 8})
        pagina.screenshot(path=str(destino), full_page=True, animations="disabled")

        dims = pagina.evaluate(
            "() => [document.documentElement.scrollWidth,"
            " document.documentElement.scrollHeight]"
        )
        navegador.close()

    print(f"{destino}  {dims[0]}x{dims[1]}px  (viewport {largura}px)")


if __name__ == "__main__":
    main()
