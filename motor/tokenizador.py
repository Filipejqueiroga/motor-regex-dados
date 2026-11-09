"""Busca de dados em texto usando um único AFD mínimo."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from motor.automatos import AFN, EPSILON
from motor.padroes import Padrao
from motor.parser import parse
from motor.simulador import maior_casamento


@dataclass
class Token:
    """Ocorrência com índices de caracteres: texto_original[inicio:fim]."""

    tipo: str
    texto: str
    inicio: int
    fim: int
    digitos_validos: bool | None = None


class Tokenizador:
    """Compila os padrões; PERSONALIZADO tem prioridade e não exige fronteira.

    O pipeline usa construir_afn(arvore, id_token), construir_afd(afn) e
    minimizar(afd), fornecidos pela Task 2. A interface pode acessar afd para
    executar passos e usa validar_documentos após tokenizar.
    """

    def __init__(self, padroes: Iterable[Padrao]):
        from motor.minimizacao import minimizar
        from motor.subconjuntos import construir_afd
        from motor.thompson import construir_afn

        self.padroes = tuple(
            replace(padrao, fronteira_numerica=False)
            if padrao.nome == "PERSONALIZADO" else padrao
            for padrao in sorted(padroes, key=lambda p: p.nome != "PERSONALIZADO")
        )
        afn = AFN(num_estados=1)
        for id_token, padrao in enumerate(self.padroes):
            parte = construir_afn(parse(padrao.expressao), id_token)
            deslocamento = afn.num_estados
            afn.num_estados += parte.num_estados
            afn.adicionar_transicao(afn.inicial, EPSILON, parte.inicial + deslocamento)
            for origem, saidas in parte.transicoes.items():
                for intervalo, destino in saidas:
                    afn.adicionar_transicao(origem + deslocamento, intervalo, destino + deslocamento)
            for estado, token in parte.aceitacao.items():
                afn.aceitacao[estado + deslocamento] = token
        self.afd = minimizar(construir_afd(afn))

    def tokenizar(self, texto: str) -> list[Token]:
        """Retorna tokens ordenados, sem sobreposição e com fim exclusivo.

        A validação aritmética é um pós-processamento explícito; os tokens
        retornados têm digitos_validos=None.
        """
        tokens = []
        inicio = 0
        while inicio < len(texto):
            casamento = maior_casamento(self.afd, texto, inicio)
            if casamento is None or casamento[0] == inicio:
                inicio += 1
                continue
            fim, id_token = casamento
            padrao = self.padroes[id_token]
            if padrao.fronteira_numerica and (
                (inicio > 0 and texto[inicio - 1].isdigit())
                or (fim < len(texto) and texto[fim].isdigit())
            ):
                inicio += 1
                continue
            tokens.append(Token(padrao.nome, texto[inicio:fim], inicio, fim))
            inicio = fim
        return tokens
