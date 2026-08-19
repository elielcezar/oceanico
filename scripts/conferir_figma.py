#!/usr/bin/env python3
"""
Confere a pagina contra os frames do Figma, bloco a bloco.

    python scripts/conferir_figma.py              # 375 e 1280
    python scripts/conferir_figma.py 1280         # so o desktop
    python scripts/conferir_figma.py 375 bloco1   # so um bloco

Por que nao usar o scripts/compare.py: ele mede "extensao nao-branca" por
linha, o que so funciona em pagina de fundo claro. Esta landing e escura.

Como funciona:

1. abre index.html no Chromium na largura pedida e captura full-page;
2. pergunta ao DOM a caixa de cada elemento [data-bloco] - assim a conferencia
   nao depende da altura total bater, que muda de proposito quando o texto
   flui em vez de ficar com altura fixa;
3. recorta o bloco do render e compara com reference/blocos/<prefixo><slug>.png,
   que e a fatia do PNG exportado do Figma em resolucao nativa;
4. imprime altura, deslocamento e % de pixels divergentes, e grava um
   lado-a-lado em reference/cmp/ para inspecao visual.
"""

import pathlib
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "index.html"
BLOCOS = RAIZ / "reference" / "blocos"
COMPARACOES = RAIZ / "reference" / "cmp"
LIMIAR_PIXEL = 24  # diferenca por canal que conta como divergencia
SEPARADOR = 12

PREPARA = """
async () => {
  // elementos flutuantes (botao do WhatsApp) nao existem no frame do Figma e
  // apareceriam sobre um bloco qualquer da captura, sujando a comparacao
  document.querySelectorAll('[data-flutuante]').forEach(el => {
    el.style.display = 'none';
  });
  // videos: congelar no quadro 0, senao cada captura pega um quadro diferente
  await Promise.all(Array.from(document.querySelectorAll('video')).map(v => {
    v.pause();
    if (v.currentTime === 0) return Promise.resolve();
    return new Promise(r => {
      v.addEventListener('seeked', r, { once: true });
      setTimeout(r, 1000);
      v.currentTime = 0;
    });
  }));
  await Promise.all(Array.from(document.images).map(img =>
    (img.complete ? Promise.resolve()
                  : new Promise(r => { img.onload = img.onerror = r; }))
      .then(() => img.decode ? img.decode().catch(() => {}) : null)));
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  for (let i = 0; i < 3; i++) await new Promise(r => requestAnimationFrame(r));
}
"""

CAIXAS = """
() => Array.from(document.querySelectorAll('[data-bloco]')).map(el => {
  const r = el.getBoundingClientRect();
  return {
    slug: el.dataset.bloco,
    x: r.x + window.scrollX,
    y: r.y + window.scrollY,
    largura: r.width,
    altura: r.height,
  };
})
"""


def captura(largura, abrir=False):
    saida = RAIZ / "reference" / ("render-%d.png" % largura)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(
            viewport={"width": largura, "height": 900},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        pagina.goto(PAGINA.as_uri(), wait_until="load")
        if abrir:
            # o FAQ nasce fechado por decisao de projeto, mas no Figma ele esta
            # desenhado aberto: para conferir a fidelidade, abre tudo antes
            pagina.evaluate("() => document.querySelectorAll('details')"
                            ".forEach(d => d.open = true)")
        pagina.evaluate(PREPARA)
        pagina.screenshot(path=str(saida), full_page=True, animations="disabled")
        caixas = pagina.evaluate(CAIXAS)
        total = pagina.evaluate("() => document.documentElement.scrollHeight")
        navegador.close()
    return saida, caixas, total


def _diferenca(va, vb):
    return np.abs(va - vb).max(axis=2)


def divergencia(a, b, busca=2):
    """% de pixels divergentes, alinhada pelo topo, sem reescalar.

    Reescalar seria pior que inutil: um bloco 1px mais alto porque o texto
    fluiu borraria cada letra e inflaria o numero justamente onde nao ha erro.

    Alem da medida direta (dx=dy=0), procura o melhor deslocamento inteiro
    dentro de +-`busca` px. Se o design so esta 1px para o lado - o que
    acontece de proposito, porque os blocos mobile do Figma tem 377px e a
    pagina tem 375 - a medida no melhor offset revela que a forma casa.
    """
    largura = min(a.width, b.width)
    altura = min(a.height, b.height)
    va = np.asarray(a.convert("RGB").crop((0, 0, largura, altura)), dtype=np.int16)
    vb = np.asarray(b.convert("RGB").crop((0, 0, largura, altura)), dtype=np.int16)

    dif = _diferenca(va, vb)
    direto = 100.0 * float((dif > LIMIAR_PIXEL).mean())

    melhor, onde = direto, (0, 0)
    for dy in range(-busca, busca + 1):
        for dx in range(-busca, busca + 1):
            if dx == 0 and dy == 0:
                continue
            ra = va[max(0, dy):altura + min(0, dy), max(0, dx):largura + min(0, dx)]
            rb = vb[max(0, -dy):altura - max(0, dy), max(0, -dx):largura - max(0, dx)]
            if ra.size == 0:
                continue
            pct = 100.0 * float((_diferenca(ra, rb) > LIMIAR_PIXEL).mean())
            if pct < melhor:
                melhor, onde = pct, (dx, dy)
    return direto, melhor, onde, float(dif.mean())


def lado_a_lado(ref, render, destino):
    alt = max(ref.height, render.height)
    folha = Image.new("RGB", (ref.width + SEPARADOR + render.width, alt), (255, 0, 255))
    folha.paste(ref, (0, 0))
    folha.paste(render, (ref.width + SEPARADOR, 0))
    destino.parent.mkdir(parents=True, exist_ok=True)
    folha.save(destino)


def confere(largura, filtro=None, abrir=False):
    prefixo = "d-" if largura >= 768 else "m-"
    alvo = "desktop" if largura >= 768 else "mobile"
    esperado = {"desktop": 9468, "mobile": 14832}[alvo]

    print("=" * 78)
    caminho, caixas, total = captura(largura, abrir)
    print("%s @%dpx -> %s  (altura %dpx, frame do Figma %dpx, %+d)"
          % (alvo, largura, caminho.name, total, esperado, total - esperado))
    print("=" * 78)
    render = Image.open(caminho).convert("RGB")

    print("%-16s %-13s %-13s %8s %8s %-8s" % ("bloco", "altura r/nosso", "topo r/nosso", "difer.", "alinhado", "offset"))
    print("-" * 78)
    y_ref = 0
    piores = []
    for caixa in caixas:
        slug = caixa["slug"]
        if filtro and filtro not in slug:
            y_ref += 0
            continue
        arquivo = BLOCOS / (prefixo + slug + ".png")
        if not arquivo.exists():
            print("%-16s (sem referencia %s)" % (slug, arquivo.name))
            continue
        ref = Image.open(arquivo).convert("RGB")
        corte = render.crop((
            0,
            int(round(caixa["y"])),
            largura,
            min(int(round(caixa["y"] + caixa["altura"])), render.height),
        ))
        pct, melhor, (dx, dy), media = divergencia(ref, corte)
        piores.append((melhor, slug))
        print("%-16s %5d/%-5d%+4d %5d/%-5d%+4d %7.1f%% %7.1f%% %+d,%+d"
              % (slug, ref.height, corte.height, corte.height - ref.height,
                 y_ref, int(caixa["y"]), int(caixa["y"]) - y_ref, pct, melhor, dx, dy))
        lado_a_lado(ref, corte, COMPARACOES / ("%s%s.png" % (prefixo, slug)))
        y_ref += ref.height

    if piores:
        piores.sort(reverse=True)
        print("-" * 78)
        print("piores: " + ", ".join("%s %.1f%%" % (s, p) for p, s in piores[:5]))
    return piores


if __name__ == "__main__":
    larguras = [375, 1280]
    filtro = None
    abrir = "--abrir" in sys.argv
    if abrir:
        sys.argv.remove("--abrir")
    if len(sys.argv) > 1:
        larguras = [int(sys.argv[1])]
    if len(sys.argv) > 2:
        filtro = sys.argv[2]
    for l in larguras:
        confere(l, filtro, abrir)
