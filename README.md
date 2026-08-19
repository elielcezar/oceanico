# Conteúdo Oceânico — Manu Leão

Landing page do curso Conteúdo Oceânico, implementada a partir do Figma com
fidelidade pixel perfect aos dois frames desenhados.

**HTML, CSS e JavaScript puro.** Sem build, sem npm, sem framework e sem
dependência externa — nem para as fontes, que são auto-hospedadas. É só abrir o
`index.html` ou servir a pasta.

## Origem

Arquivo do Figma *Conteúdo Oceânico — Manu Leão*, página **Landing Page**, com
dois frames: `desktop` (1280×9468) e `Mobile` (375×14832). As outras páginas do
arquivo — Hotmart, Instagram, moodboard — estão fora do escopo.

Os PNGs em `prints/` são a exportação nativa desses dois frames e servem de
referência para a conferência. Foram exportados à mão porque o servidor MCP do
Figma limita screenshot a 1024px no lado maior.

## Estrutura

| Pasta | O que tem |
|---|---|
| `index.html` | a página inteira: 10 `<section>`, um `h1`, hierarquia de títulos correta |
| `css/base.css` | reset, tokens do Figma, escala fluida, container, botões, animação de entrada |
| `css/secoes.css` | um bloco por seção, na ordem da página |
| `css/fontes.css` | `@font-face` das duas famílias |
| `js/` | três comportamentos, um arquivo cada (ver abaixo) |
| `assets/` | imagens, SVGs e o vídeo |
| `fonts/` | Instrument Sans e Instrument Serif em woff2 |
| `prints/` | os dois frames exportados do Figma |
| `reference/` | material de trabalho: contextos do Figma, fatias por bloco, comparações |
| `scripts/` | coleta do Figma e conferência (ver abaixo) |

## Como o layout funciona

O design tem **duas âncoras**: mobile em 375px e desktop em 1280px. Entre elas o
layout é fluido, com a quebra estrutural em **768px**. Toda medida que muda
entre as duas usa a fórmula documentada no topo do `base.css`:

```
clamp(MIN, calc(MIN + DELTA * (100vw - 375px) / 905), MAX)
```

Todo o conteúdo vive dentro de `.container`, com **850px de largura máxima**.
Ficam de fora, por natureza: fundos e degradês das seções, as decorações que
sangram (mergulhador, marca d'água, barras do FAQ) e o carrossel de aulas, que
precisa cortar na borda da tela.

Cada seção carrega `data-bloco="…"`, que é como a conferência sabe onde cada
bloco começa e termina.

## Comportamentos

| Arquivo | O que faz |
|---|---|
| `js/carrossel.js` | arrasto com o mouse no carrossel de aulas, com inércia e encaixe suave no cartão. Só age sobre ponteiro do tipo mouse — sequestrar o toque quebraria a rolagem nativa do celular |
| `js/animacoes.js` | entrada dos blocos conforme a rolagem, uma vez por elemento. Marcação por `data-anima` e `data-anima="lista"`; o movimento está todo no CSS |
| `js/video.js` | o vídeo do bloco 3 só baixa e toca quando entra na tela, pausa ao sair e respeita a pausa manual |

Três coisas são de responsabilidade do CSS e não do JS: a rolagem suave das
âncoras (`scroll-behavior`), a abertura do FAQ (`<details>` + `::details-content`)
e a flutuação do mergulhador (`@keyframes`).

**Tudo respeita `prefers-reduced-motion`** e nada é escondido sem JavaScript: o
estado inicial das animações só existe quando há a classe `js` no `<html>` *e* o
sistema não pede menos movimento. É isso que mantém a página legível em qualquer
cenário — e, de quebra, o que deixa a conferência funcionar.

## Conferência contra o Figma

```bash
python scripts/conferir_figma.py            # 375 e 1280
python scripts/conferir_figma.py 1280       # só desktop
python scripts/conferir_figma.py --abrir    # abre o FAQ antes de comparar
python scripts/faixas.py d-bloco8           # onde o bloco diverge
python scripts/medir.py 1280 ".hero__foto"  # caixas reais no navegador
```

Requer `pip install playwright pillow numpy` e `playwright install chromium`.

O script captura a página, pergunta ao DOM a caixa de cada `[data-bloco]`,
recorta e compara com a fatia correspondente do print. Compara **bloco a bloco**
de propósito: a altura total muda quando o texto flui em vez de ter altura fixa,
e isso não é erro.

**Como ler o percentual:** ele conta pixels que diferem em qualquer canal. Um
piso de 3–7% no desktop e 6–12% no mobile é só antialiasing — o Chromium desenha
texto mais encorpado que o rasterizador do Figma, na mesma posição e com a mesma
largura. O que denuncia erro de verdade é **altura do bloco e deslocamento**, não
o percentual.

Para coletar de novo do Figma (precisa do Figma Desktop aberto com o servidor MCP
ligado): `scripts/figma_mcp.py`, `figma_lote.py`, `resumir_ctx.py` e
`textos_ctx.py`. Os `compare.py`, `shot.py`, `baseline.py` e `conferir.py` vieram
da skill original e medem fundo claro — não servem nesta landing escura.

## Divergências deliberadas

A página se afastou do Figma em alguns pontos, todos por decisão de projeto. O
comparador vai continuar acusando, e está certo:

- **FAQ nasce fechado**, embora o arquivo o mostre todo aberto.
- **Bloco 8** não tem mais a faixa de luz que esmaecia a borda direita do
  carrossel (removida a pedido) — daí a divergência alta ali.
- **Bloco 3** tem o vídeo de verdade no lugar da capa estática.
- **Bloco 10** teve fonte do título, botão e espaçamentos alterados.
- **Hero e cabeçalho** não animam na entrada: já estão visíveis no carregamento.

## Notas

- `assets/video.mp4` tem 7,8 MB (87s, 540×960) — mais que todo o resto somado.
  Por isso o carregamento é adiado. Reencodar em 360×640 cortaria perto da
  metade sem perda visível no card, que exibe em 324×453.
- Os CTAs laranja levam por âncora ao bloco da oferta (`#oferta`). O único link
  externo de compra é o botão dentro do cartão de preço.
