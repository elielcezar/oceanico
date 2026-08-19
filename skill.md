---
name: figma-pixel-perfect-html
description: >-
  Implementa um design do Figma em HTML + CSS + JavaScript puro com fidelidade
  pixel perfect, usando arquitetura flow-first (texto/imagens no fluxo, apenas
  decorações em position:absolute) e um loop de screenshot → comparação
  programática → correção. Use quando o usuário pedir para implementar,
  converter ou "codar" um design do Figma (ou passar uma URL figma.com) em
  HTML/CSS/JS e esperar resultado fiel/pixel perfect.
---
# Implementar design do Figma em HTML/CSS/JS (pixel perfect)

## Stack

HTML + CSS + JavaScript **puro** (sem framework), a menos que o usuário peça outra coisa.

## Fluxo de trabalho (loop até ficar fiel)

Trate como um loop de feedback. Não pare no passo 3.

1. **Analisar specs do Figma.** Pegue design context, metadata e um **screenshot em resolução nativa** (peça `maxDimension` alto — o padrão costuma vir pequeno, ex. ~130px de largura). Anote larguras, alturas, `top`/`left`, cores, fontes e line-heights reais.
2. **Baixar assets** e **verificar o formato real** de cada um (veja "Armadilhas"). Salve em `assets/`.
3. **Escrever HTML/CSS semântico** seguindo a arquitetura flow-first (abaixo).
4. **Renderizar** a página num screenshot **no mesmo tamanho do original** (`scripts/shot.py`).
5. **Comparar de forma programática** (`scripts/compare.py`): fatias lado a lado + medições em px. Não confie só no olho.
6. **Listar os erros** encontrados e **corrigir**.
7. **Repetir 4–6** até estar 100% fiel.

## Arquitetura: flow-first + backdrop

O objetivo é fidelidade **com HTML semântico**, não um mar de `position: absolute`.

**Conteúdo no fluxo normal (padrão):**
- Blocos de texto que têm largura de 100% vão em **fluxo normal** dentro de um `<div>` semântico (`h1`/`h2`/`h3`/`p`/`ul`/`figure`), empilhados com `margin`/`padding` pequenos e naturais.
- Fotos de largura cheia são blocos (`<figure>`) **na posição lógica do HTML**, entre os textos. A altura real da foto ocupa o espaço.

## Alerta de ERRO ##

- 🚩`margin-top` de 300–500px entre blocos quase sempre significa que uma imagem deveria estar no fluxo naquele ponto.
- 🚩`multiplos position: absolute`: se o CSS tiver mais de 20 itens assim, algo pode estar errado, revise anecessidade de uso.


**Só isto vai em `position: absolute` (camada "backdrop"):**
- Elementos que **de fato sangram/giram/sobrepõem** (ex.: uma ilustração do hero que vaza sobre o topo).

## Boas práticas de HTML

- Hierarquia correta de `h1`/`h2`/`h3`.
- `<p>` para parágrafos, `<ul>`/`<li>` para listas, `<figure>` para imagens de conteúdo.
- Agrupe elementos visualmente conectados (título + texto) em containers lógicos (`section`, `article`, `div`).
- Evite tags vazias sem função.

## Boas práticas de CSS

- Prefira **Flexbox** e **Grid** para arranjo de conteúdo.
- Use `margin`/`padding` à vontade para o ritmo vertical.
- `float` e `position: absolute`: só quando estritamente necessário (sobreposições reais). Não use `absolute` para posicionar blocos de texto ou imagens que poderiam fluir.
- Blocos de texto como listas e parágrafos não devem ter a altura especificada no CSS, nem mínima, nem máxima (a altura desses elementos deve fluir naturalmente de acordo com a quantidade de texto ).
- Ao aplicar os blocos de texto fluído a página poderá ficar mais longa que o original. Isso não é um problema, essas pequenas diferenças de design serão toleradas nesse caso específico.
- Sempre inclua um reset mínimo: `*{box-sizing:border-box} img{display:block} figure{margin:0}`.

## Scripts utilitários

Requisitos: `pip install playwright pillow numpy` e `playwright install chromium`.

- **`scripts/shot.py`** — screenshot full-page de um HTML local (ou URL) numa largura exata:
  ```bash
  python scripts/shot.py index.html reference/render.png 402
  ```
- **`scripts/compare.py`** — monta fatias lado a lado (original × render) e imprime a extensão horizontal não-branca por linha (detecta deslocamentos esquerda/direita):
  ```bash
  python scripts/compare.py reference/original_native.png reference/render.png reference/cmp 800
  ```
  Depois **leia as fatias** geradas em `reference/cmp/` e as medições impressas para localizar divergências.
