"""Validação aritmética de CPF e CNPJ após a tokenização."""

from motor.tokenizador import Token


def _digito(digitos: list[int], pesos: list[int]) -> int:
    resto = sum(digito * peso for digito, peso in zip(digitos, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def _validar(texto: str, tipo: str) -> bool:
    digitos = [int(c) for c in texto if c in "0123456789"]
    tamanho = 11 if tipo == "CPF" else 14
    if len(digitos) != tamanho or len(set(digitos)) == 1:
        return False
    base = digitos[:-2]
    for indice in range(2):
        pesos = list(range(10 + indice, 1, -1)) if tipo == "CPF" else (
            list(range(5 + indice, 1, -1)) + list(range(9, 1, -1))
        )
        base.append(_digito(base, pesos))
    return base == digitos


def validar_documentos(tokens: list[Token]) -> list[Token]:
    """Preenche a validade dos documentos sem remover ou reclassificar tokens."""
    for token in tokens:
        token.digitos_validos = _validar(token.texto, token.tipo) if token.tipo in ("CPF", "CNPJ") else None
    return tokens
