/*
 * Arrastar com o mouse para rolar o carrossel, com inercia ao soltar.
 *
 * A rolagem por dedo e por trackpad e nativa e continua funcionando sozinha -
 * este script so cuida do mouse, que nao tem gesto de arrasto proprio. Por isso
 * ele ignora ponteiros que nao sejam mouse: sequestrar o toque quebraria o
 * scroll-snap e a inercia que o proprio celular ja faz.
 */
(function () {
  "use strict";

  var LIMIAR_CLIQUE = 5; // px de movimento a partir dos quais o arrasto nao e clique
  var JANELA_VELOCIDADE = 90; // ms considerados para medir a velocidade de saida
  var ATRITO = 0.9; // quanto da velocidade sobrevive a cada quadro de 60fps
  var VELOCIDADE_MINIMA = 0.02; // px/ms abaixo dos quais a inercia para

  document.querySelectorAll("[data-arrasta]").forEach(function (carrossel) {
    var arrastando = false;
    var xInicial = 0;
    var rolagemInicial = 0;
    var percorrido = 0;
    var amostras = []; // {x, t} recentes, para calcular a velocidade de saida
    var quadro = null;

    function pararInercia() {
      if (quadro !== null) {
        cancelAnimationFrame(quadro);
        quadro = null;
      }
    }

    /* Ao fim do deslize o scroll-snap encaixaria o cartao mais proximo num
       salto seco, as vezes puxando mais de 100px para tras. Aqui o encaixe e
       feito antes, com rolagem suave, e so depois o snap volta a valer. */
    function assentar() {
      var itens = carrossel.querySelectorAll("[data-arrasta] > * > *");
      if (!itens.length) {
        carrossel.classList.remove("esta-arrastando");
        return;
      }

      // o recuo vem do padding da trilha, e nao de scroll-padding-left: este
      // ultimo esta escrito com max()/calc() e nao volta resolvido em px
      var trilho = carrossel.firstElementChild;
      var recuo = trilho ? parseFloat(getComputedStyle(trilho).paddingLeft) || 0 : 0;
      var bordaCarrossel = carrossel.getBoundingClientRect().left;
      var atual = carrossel.scrollLeft;
      var alvo = null;

      itens.forEach(function (item) {
        // pela posicao na tela, e nao por offsetLeft: este ultimo e relativo ao
        // ancestral posicionado, que nem sempre e o conteudo rolavel
        var destino = atual + (item.getBoundingClientRect().left - bordaCarrossel) - recuo;
        if (alvo === null || Math.abs(destino - atual) < Math.abs(alvo - atual)) {
          alvo = destino;
        }
      });

      if (Math.abs(alvo - carrossel.scrollLeft) > 1) {
        carrossel.scrollTo({ left: alvo, behavior: "smooth" });
      }
      // o snap so pode voltar depois que a rolagem suave terminar
      setTimeout(function () {
        carrossel.classList.remove("esta-arrastando");
      }, 400);
    }

    function deslizar(velocidade) {
      var anterior = performance.now();

      function passo(agora) {
        var dt = agora - anterior;
        anterior = agora;

        carrossel.scrollLeft -= velocidade * dt;
        // o atrito e aplicado por tempo, nao por quadro: assim a desaceleracao
        // e a mesma em 60Hz e em 120Hz
        velocidade *= Math.pow(ATRITO, dt / 16.67);

        var noFim =
          carrossel.scrollLeft <= 0 ||
          carrossel.scrollLeft >= carrossel.scrollWidth - carrossel.clientWidth - 1;

        if (Math.abs(velocidade) > VELOCIDADE_MINIMA && !noFim) {
          quadro = requestAnimationFrame(passo);
        } else {
          quadro = null;
          assentar();
        }
      }

      quadro = requestAnimationFrame(passo);
    }

    carrossel.addEventListener("pointerdown", function (evento) {
      if (evento.pointerType !== "mouse" || evento.button !== 0) return;
      pararInercia();
      arrastando = true;
      percorrido = 0;
      xInicial = evento.clientX;
      rolagemInicial = carrossel.scrollLeft;
      amostras = [{ x: evento.clientX, t: performance.now() }];
      carrossel.classList.add("esta-arrastando");
      // segue o ponteiro mesmo se ele sair da area do carrossel
      carrossel.setPointerCapture(evento.pointerId);
    });

    carrossel.addEventListener("pointermove", function (evento) {
      if (!arrastando) return;
      var distancia = evento.clientX - xInicial;
      percorrido = Math.max(percorrido, Math.abs(distancia));
      carrossel.scrollLeft = rolagemInicial - distancia;

      var agora = performance.now();
      amostras.push({ x: evento.clientX, t: agora });
      while (amostras.length > 2 && agora - amostras[0].t > JANELA_VELOCIDADE) {
        amostras.shift();
      }
      evento.preventDefault();
    });

    function soltar(evento) {
      if (!arrastando) return;
      arrastando = false;
      if (evento && carrossel.hasPointerCapture(evento.pointerId)) {
        carrossel.releasePointerCapture(evento.pointerId);
      }

      var primeira = amostras[0];
      var ultima = amostras[amostras.length - 1];
      var intervalo = ultima.t - primeira.t;
      var velocidade = intervalo > 0 ? (ultima.x - primeira.x) / intervalo : 0;

      if (Math.abs(velocidade) > VELOCIDADE_MINIMA) {
        deslizar(velocidade);
      } else {
        assentar();
      }
    }

    carrossel.addEventListener("pointerup", soltar);
    carrossel.addEventListener("pointercancel", soltar);

    // um arrasto nao pode virar clique em link/botao dentro do carrossel
    carrossel.addEventListener(
      "click",
      function (evento) {
        if (percorrido > LIMIAR_CLIQUE) {
          evento.preventDefault();
          evento.stopPropagation();
        }
      },
      true
    );

    // desliga o "arrastar imagem" nativo do navegador
    carrossel.addEventListener("dragstart", function (evento) {
      evento.preventDefault();
    });

    // roda do mouse ou toque cancelam a inercia em andamento
    carrossel.addEventListener("wheel", pararInercia, { passive: true });
    carrossel.addEventListener("touchstart", pararInercia, { passive: true });
  });
})();
