#!/usr/bin/env python3
"""
Cliente minimo para o Figma Dev Mode MCP Server (Figma Desktop, porta 3845).

    python scripts/figma_mcp.py tools
    python scripts/figma_mcp.py resources
    python scripts/figma_mcp.py read skill://figma/... [saida.md]
    python scripts/figma_mcp.py call get_metadata '{"nodeId":"134:6247"}' saida.xml
    python scripts/figma_mcp.py call get_screenshot '{"nodeId":"134:6247"}' ref/original.png

O servidor fala JSON-RPC sobre HTTP com resposta em SSE (`event: message` +
uma ou mais linhas `data:`). Este script cuida do handshake (initialize ->
notifications/initialized -> chamada), remonta o SSE e grava o resultado:

- conteudo `text`  -> gravado como texto no arquivo de saida (ou impresso);
- conteudo `image` -> base64 decodificado e gravado como binario.

Existe porque as tools MCP nativas devolvem a imagem inline no contexto, e o
fluxo pixel perfect precisa do PNG em disco para o scripts/compare.py.
"""

import base64
import json
import pathlib
import sys
import urllib.request

URL = "http://127.0.0.1:3845/mcp"
CABECALHOS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _post(corpo, sessao=None, timeout=300):
    cabecalhos = dict(CABECALHOS)
    if sessao:
        cabecalhos["Mcp-Session-Id"] = sessao
    req = urllib.request.Request(
        URL, data=json.dumps(corpo).encode("utf-8"), headers=cabecalhos, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.headers.get("Mcp-Session-Id"), resp.read().decode("utf-8")


def _desempacota(bruto):
    """Remonta o JSON de uma resposta SSE (ou JSON puro).

    Duas armadilhas deste servidor:

    - o corpo vem como evento SSE (`event: message` + `data: {...}`);
    - o JSON traz quebras de linha *literais* dentro das strings (nomes de
      camadas de texto com varias linhas). Isso e JSON invalido pelo padrao
      estrito e faz qualquer parser por linha cortar o payload no meio.

    Por isso: pega tudo depois do primeiro `data:`, remonta as linhas como
    estavam e parseia com strict=False, que aceita controle dentro de string.
    """
    inicio = bruto.find("data:")
    corpo = bruto if inicio == -1 else bruto[inicio + len("data:") :]
    linhas = corpo.splitlines()
    if linhas:
        linhas[0] = linhas[0].lstrip(" ")
    remontado = []
    for linha in linhas:
        # se o servidor de fato quebrar em varios `data:`, tira o prefixo
        remontado.append(linha[5:].lstrip(" ") if linha.startswith("data:") else linha)
    payload = "\n".join(remontado).strip()
    if not payload.startswith("{"):
        raise SystemExit("resposta inesperada do servidor: " + bruto[:500])
    return json.loads(payload, strict=False)


def conecta():
    sessao, bruto = _post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "claude-code", "version": "1"},
            },
        }
    )
    _desempacota(bruto)
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sessao)
    return sessao


def _grava(destino, texto=None, binario=None):
    caminho = pathlib.Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if binario is not None:
        caminho.write_bytes(binario)
        print("[imagem] " + str(len(binario)) + " bytes -> " + destino)
    else:
        caminho.write_text(texto, encoding="utf-8")
        print("[texto] " + str(len(texto)) + " chars -> " + destino)


def chama(nome, argumentos, destino=None):
    sessao = conecta()
    _, bruto = _post(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos},
        },
        sessao,
    )
    resposta = _desempacota(bruto)
    if "error" in resposta:
        raise SystemExit("erro do servidor: " + json.dumps(resposta["error"])[:800])

    resultado = resposta.get("result", {})
    if resultado.get("isError"):
        raise SystemExit("tool retornou erro: " + json.dumps(resultado)[:800])

    partes = resultado.get("content", [])
    imagens = 0
    textos = []
    for parte in partes:
        tipo = parte.get("type")
        if tipo == "text":
            # varias partes de texto no mesmo retorno: juntar, nunca sobrescrever
            textos.append(parte["text"])
        elif tipo == "image":
            dados = base64.b64decode(parte["data"])
            # o destino pode ser um .txt/.xml (o retorno mistura texto e imagem):
            # nesse caso a imagem vai para um .png irmao, nunca por cima do texto
            base = destino if destino else "figma_out.png"
            if not base.lower().endswith(".png"):
                base = base.rsplit(".", 1)[0] + ".png"
            if imagens:
                base = base[:-4] + "_" + str(imagens) + ".png"
            _grava(base, binario=dados)
            imagens += 1
        else:
            print("[" + str(tipo) + "] " + json.dumps(parte)[:300])

    if textos:
        junto = "\n\n".join(textos)
        if destino and not destino.lower().endswith(".png"):
            _grava(destino, texto=junto)
        else:
            print(junto)
    if not partes:
        print(json.dumps(resultado)[:1000])


def le_resource(uri, destino=None):
    sessao = conecta()
    _, bruto = _post(
        {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": uri}},
        sessao,
    )
    resposta = _desempacota(bruto)
    if "error" in resposta:
        raise SystemExit("erro do servidor: " + json.dumps(resposta["error"])[:800])
    conteudos = resposta.get("result", {}).get("contents", [])
    if not conteudos:
        print("resource vazio: " + json.dumps(resposta.get("result", {}))[:500])
    for parte in conteudos:
        texto = parte.get("text", "")
        if destino:
            _grava(destino, texto=texto)
        else:
            print(texto)


def lista_resources():
    sessao = conecta()
    for metodo in ("resources/list", "resources/templates/list", "prompts/list"):
        _, bruto = _post({"jsonrpc": "2.0", "id": 2, "method": metodo}, sessao)
        resposta = _desempacota(bruto)
        print("== " + metodo + " ==")
        print(json.dumps(resposta.get("result", resposta), ensure_ascii=False)[:1500])


def lista_tools():
    sessao = conecta()
    _, bruto = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sessao)
    for tool in _desempacota(bruto)["result"]["tools"]:
        print("=" * 70)
        print(tool["name"])
        print("-", (tool.get("description") or "").strip())
        print("  params:", json.dumps(tool.get("inputSchema", {}), ensure_ascii=False))


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else "tools"
    if comando == "tools":
        lista_tools()
    elif comando == "resources":
        lista_resources()
    elif comando == "read":
        le_resource(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif comando == "call":
        chama(
            sys.argv[2],
            json.loads(sys.argv[3]),
            sys.argv[4] if len(sys.argv) > 4 else None,
        )
    else:
        raise SystemExit(__doc__)
