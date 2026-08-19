#!/usr/bin/env python3
"""
Confere se uma página refatorada continua idêntica à versão de um commit.

    python scripts/conferir.py editorial.html
    python scripts/conferir.py editorial.html --larguras 402,1280 --ref HEAD~1
    python scripts/conferir.py categoria-*.html          # aceita várias

Reconstrói a página como estava no commit (via scripts/baseline.py), fotografa
as duas versões em cada largura e imprime quantos pixels diferem. Sai com
código 1 se alguma largura divergir, para dar pra usar em script.

As larguras padrão cobrem os três casos que importam nesta revista:
  402  — frame do Figma (em algumas páginas o scrollbar-gutter espreme p/ 387)
  417  — largura em que o frame recebe os 402px cheios mesmo com gutter
  1280 — desktop, com a barra lateral de navegação visível
"""

import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LARGURAS = (402, 417, 1280)

# Screenshot descartavel, tirado antes do de verdade.
#
# O menu horizontal rola ate o item ativo por script. O scrollLeft ja' vale o
# numero certo quando a captura comeca, mas o compositor so' publica a rolagem
# alguns quadros depois -- os requestAnimationFrame do PREPARA nao bastam, e
# esperar no relogio so' diminui a chance (em 500ms a falha ainda aparecia em
# ~30% das capturas de editorial.html). Um screenshot obriga o compositor a
# publicar um quadro; o segundo ja' sai com a rolagem aplicada.
#
# Sem isso a mesma pagina rende dois resultados na mesma rodada: 4.469 pixels
# de diferenca na faixa do menu, que nao existem.
def assenta(pg) -> None:
    pg.screenshot(clip={"x": 0, "y": 0, "width": 8, "height": 8})

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
  // Sem esperar por eles, a primeira captura (fontes frias) sai com o menu no
  // comeco e as seguintes saem centralizadas -- 4.400 pixels de diferenca que
  // nao existem.
  for (let i = 0; i < 3; i++) {
    await new Promise(r => requestAnimationFrame(r));
  }
}
"""


def dispara(pagina: str, ref: str) -> pathlib.Path:
    """Reconstrói a página no commit e devolve o caminho do HTML."""
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "baseline.py"), pagina,
         "tmp/_conferir_descarte.png", "1", "--ref", ref],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    alvo = RAIZ / "tmp" / "_baseline" / pathlib.Path(pagina).name
    if not alvo.exists():
        sys.exit(f"nao consegui reconstruir {pagina} em {ref}:\n{r.stdout}\n{r.stderr}")
    return alvo


# O conteudo de um <video> nao e reproduzivel entre capturas: o decodificador
# alterna de quadro mesmo com pause() e seek. brightness(0) pinta o quadro de
# preto sem mexer na caixa nem na borda, entao geometria continua sendo
# comparada e so o frame sai da conta.
#
# O background preto cobre o caso em que nao ha quadro nenhum: com preload
# "metadata"/"none" o video as vezes nao chega a pintar nada e a caixa fica
# transparente, deixando ver o que esta atras. Ai a mesma pagina rende dois
# resultados (em index/home isso dava 88.742 pixels). Com o fundo, a caixa e'
# preta tendo quadro ou nao.
NEUTRALIZA_VIDEO = (
    "video { background: #000 !important; filter: brightness(0) !important; }"
)


def captura(pg, url: str, largura: int) -> np.ndarray:
    pg.set_viewport_size({"width": largura, "height": 900})
    pg.goto(url, wait_until="load")
    pg.add_style_tag(content=NEUTRALIZA_VIDEO)
    try:
        pg.wait_for_load_state("networkidle", timeout=1500)
    except Exception:
        pass
    pg.evaluate(PREPARA)
    assenta(pg)
    destino = RAIZ / "tmp" / f"_cf_{largura}.png"
    pg.screenshot(path=str(destino), full_page=True, animations="disabled")
    return np.asarray(Image.open(destino).convert("RGB"), dtype=np.int16)


def main() -> None:
    argv = sys.argv[1:]
    ref = "HEAD"
    larguras = list(LARGURAS)
    for flag, conv in (("--ref", str), ("--larguras", None)):
        if flag in argv:
            i = argv.index(flag)
            valor = argv[i + 1]
            del argv[i:i + 2]
            if flag == "--ref":
                ref = valor
            else:
                larguras = [int(x) for x in valor.split(",")]

    if not argv:
        sys.exit("uso: conferir.py <pagina.html> [...] [--larguras 402,1280] [--ref COMMIT]")

    (RAIZ / "tmp").mkdir(exist_ok=True)
    falhou = False

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            # imageAnimationPolicy=2 congela GIFs no primeiro quadro;
            # sem isso cada captura pega um quadro diferente.
            args=["--blink-settings=imageAnimationPolicy=2"]
        )
        pg = navegador.new_page(device_scale_factor=1, reduced_motion="reduce")

        for pagina in argv:
            antes_html = dispara(pagina, ref)
            print(f"\n{pagina}  (contra {ref})")
            for largura in larguras:
                a = captura(pg, antes_html.as_uri(), largura)
                b = captura(pg, (RAIZ / pagina).as_uri(), largura)
                if a.shape != b.shape:
                    print(f"  {largura:>5}px  DIMENSOES DIFERENTES: "
                          f"{a.shape[1]}x{a.shape[0]} vs {b.shape[1]}x{b.shape[0]}")
                    falhou = True
                    continue
                n = int((np.abs(a - b) > 0).any(axis=2).sum())
                marca = "identico" if n == 0 else f"{n} pixels diferentes  <<<"
                print(f"  {largura:>5}px  {b.shape[1]}x{b.shape[0]}  {marca}")
                falhou = falhou or n > 0

        navegador.close()

    print("\n" + ("ALGUMA LARGURA DIVERGIU" if falhou else "TUDO IDENTICO"))
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
