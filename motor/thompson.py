"""Construção de Thompson: conversão de AST em AFN-ε.

Implementa a construção estrutural de Thompson para expressões regulares,
mapeando cada nó da árvore sintática (AST) para um fragmento de AFN com
exatamente um estado inicial e um estado de aceitação.
"""

from __future__ import annotations

from typing import Any

from motor.arvore import Classe, Concat, Estrela, No, Uniao, Vazio
from motor.automatos import AFN, EPSILON, ID_TOKEN_PADRAO


def construir_afn(arvore: No, id_token: int = ID_TOKEN_PADRAO) -> AFN:
    """Converte uma AST em um AFN com movimentos vazios (Thompson).

    Garante exatamente um estado inicial e um de aceitação por fragmento.
    Os identificadores dos estados são sequenciais de 0 a num_estados - 1.
    Usa abordagem iterativa com pilha explícita para evitar estouro de recursão
    em árvores profundas geradas por quantificadores como {n,m}.
    """
    afn = AFN()
    fragmentos: list[tuple[int, int]] = []

    # Ações da pilha explícita para percurso em pós-ordem:
    # 0: Visitar nó
    # 1: Finalizar Concat
    # 2: Finalizar Uniao (recebe novo_inicio)
    # 3: Finalizar Estrela (recebe novo_inicio)
    pilha: list[tuple[int, Any]] = [(0, arvore)]

    while pilha:
        acao, dado = pilha.pop()
        if acao == 0:
            no = dado
            if isinstance(no, Vazio):
                inicio = afn.novo_estado()
                fim = afn.novo_estado()
                afn.adicionar_transicao(inicio, EPSILON, fim)
                fragmentos.append((inicio, fim))
            elif isinstance(no, Classe):
                inicio = afn.novo_estado()
                fim = afn.novo_estado()
                for intervalo in no.intervalos:
                    afn.adicionar_transicao(inicio, intervalo, fim)
                fragmentos.append((inicio, fim))
            elif isinstance(no, Concat):
                pilha.append((1, None))
                pilha.append((0, no.dir))
                pilha.append((0, no.esq))
            elif isinstance(no, Uniao):
                novo_inicio = afn.novo_estado()
                pilha.append((2, novo_inicio))
                pilha.append((0, no.dir))
                pilha.append((0, no.esq))
            elif isinstance(no, Estrela):
                novo_inicio = afn.novo_estado()
                pilha.append((3, novo_inicio))
                pilha.append((0, no.filho))
            else:
                raise TypeError(f"Nó da AST não suportado: {type(no).__name__}")
        elif acao == 1:
            dir_s, dir_f = fragmentos.pop()
            esq_s, esq_f = fragmentos.pop()
            afn.adicionar_transicao(esq_f, EPSILON, dir_s)
            fragmentos.append((esq_s, dir_f))
        elif acao == 2:
            novo_inicio = dado
            dir_s, dir_f = fragmentos.pop()
            esq_s, esq_f = fragmentos.pop()
            novo_fim = afn.novo_estado()
            afn.adicionar_transicao(novo_inicio, EPSILON, esq_s)
            afn.adicionar_transicao(novo_inicio, EPSILON, dir_s)
            afn.adicionar_transicao(esq_f, EPSILON, novo_fim)
            afn.adicionar_transicao(dir_f, EPSILON, novo_fim)
            fragmentos.append((novo_inicio, novo_fim))
        elif acao == 3:
            novo_inicio = dado
            sub_s, sub_f = fragmentos.pop()
            novo_fim = afn.novo_estado()
            afn.adicionar_transicao(novo_inicio, EPSILON, sub_s)  # entrar
            afn.adicionar_transicao(novo_inicio, EPSILON, novo_fim)  # pular
            afn.adicionar_transicao(sub_f, EPSILON, sub_s)  # repetir
            afn.adicionar_transicao(sub_f, EPSILON, novo_fim)  # sair
            fragmentos.append((novo_inicio, novo_fim))

    inicial_raiz, fim_raiz = fragmentos.pop()
    afn.inicial = inicial_raiz
    afn.aceitacao[fim_raiz] = id_token
    afn.validar()
    return afn
