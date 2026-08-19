/*
 * Video que so carrega e toca quando entra na tela.
 *
 * O arquivo tem quase 8 MB - mais que todo o resto da pagina somado. Com
 * `autoplay` no HTML o navegador baixaria isso para todo mundo, inclusive para
 * quem nunca rola ate o bloco. Por isso o elemento nasce com `preload="none"`
 * e quem manda tocar e este script, quando o video aparece.
 *
 * Ele tambem pausa ao sair da tela: sem isso, quem ligar o som continua ouvindo
 * a Manu falando enquanto le outro bloco. E respeita a pausa manual - se a
 * pessoa pausou, nao voltamos a tocar por conta propria.
 */
(function () {
  "use strict";

  var videos = document.querySelectorAll("video[data-toca-ao-ver]");
  if (!videos.length || !("IntersectionObserver" in window)) return;

  videos.forEach(function (video) {
    var pausadoPelaPessoa = false;
    var nossaPausa = false;

    video.addEventListener("pause", function () {
      // se a pausa nao partiu daqui, foi a pessoa: nao mexemos mais
      if (!nossaPausa && !video.ended) pausadoPelaPessoa = true;
      nossaPausa = false;
    });

    video.addEventListener("play", function () {
      pausadoPelaPessoa = false;
    });

    var observador = new IntersectionObserver(
      function (entradas) {
        entradas.forEach(function (entrada) {
          if (entrada.isIntersecting) {
            if (pausadoPelaPessoa || !video.paused) return;
            video.preload = "auto";
            var promessa = video.play();
            // o navegador pode recusar; os controles nativos continuam la
            if (promessa && promessa.catch) promessa.catch(function () {});
          } else if (!video.paused) {
            nossaPausa = true;
            video.pause();
          }
        });
      },
      { threshold: 0.25 }
    );

    observador.observe(video);
  });
})();
