"""Exportação dos dados extraídos agrupados por tipo."""

import json

from motor.tokenizador import Token


def exportar_json(tokens: list[Token]) -> str:
    grupos = {}
    for token in tokens:
        dados = {"texto": token.texto, "inicio": token.inicio, "fim": token.fim}
        if token.tipo in ("CPF", "CNPJ"):
            dados["digitos_validos"] = token.digitos_validos
        grupos.setdefault(token.tipo, []).append(dados)
    return json.dumps(grupos, ensure_ascii=False, indent=2)
