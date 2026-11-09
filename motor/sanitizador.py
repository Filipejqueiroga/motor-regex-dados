"""Substituição de tokens sem alterar as posições do texto de entrada."""

from motor.tokenizador import Token


def sanitizar(texto: str, tokens: list[Token], regras: dict[str, str]) -> str:
    trechos = []
    inicio = 0
    for token in tokens:
        trechos.append(texto[inicio:token.inicio])
        regra = regras.get(token.tipo, "rotulo")
        if regra == "rotulo":
            trechos.append(f"[{token.tipo}]")
        elif regra == "mascarar":
            trechos.append("*" * (token.fim - token.inicio))
        elif regra == "manter":
            trechos.append(texto[token.inicio:token.fim])
        elif regra != "remover":
            raise ValueError(f"regra de sanitização inválida: {regra}")
        inicio = token.fim
    trechos.append(texto[inicio:])
    return "".join(trechos)
