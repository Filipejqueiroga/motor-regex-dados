from motor.arvore import (
    Classe,
    Concat,
    Estrela,
    Uniao,
    Vazio,
    concatenar,
    formatar_arvore,
    unir,
)

a, b, c = Classe.literal("a"), Classe.literal("b"), Classe.literal("c")


def test_classe_normaliza_e_testa_pertinencia():
    classe = Classe(((ord("m"), ord("z")), (ord("a"), ord("n"))))
    assert classe.intervalos == ((ord("a"), ord("z")),)
    assert classe.contem("q") and classe.contem(ord("a"))
    assert not classe.contem("A")
    assert not Classe(()).contem("a")


def test_nos_sao_comparaveis_e_imutaveis():
    assert Concat(a, Estrela(b)) == Concat(Classe.literal("a"), Estrela(Classe.literal("b")))
    assert hash(Uniao(a, Vazio())) == hash(Uniao(a, Vazio()))


def test_concatenar_descarta_vazio():
    assert concatenar([]) == Vazio()
    assert concatenar([Vazio(), a, Vazio()]) == a
    assert concatenar([a, b]) == Concat(a, b)


def test_concatenar_e_unir_ficam_balanceados():
    def altura(no):
        if isinstance(no, (Concat, Uniao)):
            return 1 + max(altura(no.esq), altura(no.dir))
        return 0

    assert altura(concatenar([a] * 1024)) == 10
    assert altura(unir([a] * 1024)) == 10


def test_formatar_arvore():
    arvore = Uniao(Concat(a, b), Estrela(c))
    assert formatar_arvore(arvore) == (
        "Uniao\n"
        "├─ Concat\n"
        "│  ├─ Classe [a]\n"
        "│  └─ Classe [b]\n"
        "└─ Estrela\n"
        "   └─ Classe [c]"
    )
