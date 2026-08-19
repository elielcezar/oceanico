/*
 * Entrada dos blocos conforme a pagina rola - uma vez so por elemento.
 *
 * O script faz uma coisa so: poe a classe `visivel` quando o elemento entra na
 * tela e para de observa-lo. Todo o movimento (deslocamento, duracao, easing,
 * escalonamento das listas) esta no CSS, junto do resto do design.
 *
 * Marcacao no HTML:
 *   data-anima          -> o proprio elemento entra
 *   data-anima="lista"  -> os filhos diretos entram em sequencia
 *
 * O estado inicial (invisivel) so existe no CSS quando ha a classe `js` no
 * <html> e quando o sistema nao pede menos movimento. Por isso, sem JS ou com
 * `prefers-reduced-motion`, o conteudo nasce visivel e nada aqui e necessario
 * para a pagina ser lida.
 */
(function () {
  "use strict";

  // com movimento reduzido o CSS nem esconde: nao ha nada a fazer
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var alvos = document.querySelectorAll("[data-anima]");
  if (!alvos.length) return;

  // navegador sem IntersectionObserver: mostra tudo de uma vez
  if (!("IntersectionObserver" in window)) {
    alvos.forEach(function (elemento) {
      elemento.classList.add("visivel");
    });
    return;
  }

  var observador = new IntersectionObserver(
    function (entradas) {
      entradas.forEach(function (entrada) {
        // o segundo teste cobre quem ficou para tras num salto de rolagem
        // (link com ancora, restauracao de posicao): sem ele, tudo que a
        // pagina pulou continuaria invisivel para sempre
        var jaPassou = entrada.boundingClientRect.bottom < 0;
        if (!entrada.isIntersecting && !jaPassou) return;
        entrada.target.classList.add("visivel");
        // "primeira vez" e literal: o elemento sai da observacao e nao reanima
        observador.unobserve(entrada.target);
      });
    },
    {
      // dispara um pouco antes de o elemento encostar na borda de baixo
      rootMargin: "0px 0px -12% 0px",
    }
  );

  alvos.forEach(function (elemento) {
    observador.observe(elemento);
  });
})();
