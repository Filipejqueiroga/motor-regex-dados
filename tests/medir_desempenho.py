"""Mede a tokenização. Execute com ``python -m tests.medir_desempenho``."""

from time import perf_counter

from motor.padroes import PADROES
from motor.tokenizador import Tokenizador

TAMANHO = 100_000
TRECHO = "Oi, meu CPF é 123.456.789-09 e o e-mail é maria.silva@gmail.com. Paguei R$ 1.234,56 em 03/11/2026. "


def medir(tokenizador, texto):
    inicio = perf_counter()
    tokens = tokenizador.tokenizar(texto)
    return perf_counter() - inicio, len(tokens)


def main():
    tokenizador = Tokenizador(PADROES)
    texto = (TRECHO * (TAMANHO // len(TRECHO) + 1))[:TAMANHO]
    segundos, quantidade = medir(tokenizador, texto)
    print(f"texto realista: {TAMANHO} caracteres, {quantidade} tokens, {segundos:.3f} s")

    for tamanho in (1_000, 2_000, 4_000):
        segundos, _ = medir(tokenizador, "a" * tamanho)
        print(f"pior caso ('a' repetido, sem @): {tamanho} caracteres, {segundos:.3f} s")


if __name__ == "__main__":
    main()
