from config import supabase

PRODUTOS_POR_PAGINA = 5


def obter_produtos(pagina=1):

    produtos_modelo = (
        supabase
        .table("produtos_modelo")
        .select("*")
        .execute()
    )

    produtos = (
        supabase
        .table("produtos")
        .select("*")
        .execute()
    )

    subfamilias = (
        supabase
        .table("subfamilia")
        .select("*")
        .execute()
    )

    familias = (
        supabase
        .table("familia")
        .select("*")
        .execute()
    )

    produtos_dict = {
        p["id_modelo"]: p
        for p in produtos.data
    }

    subfamilias_dict = {
        s["id_subfamilia"]: s
        for s in subfamilias.data
    }

    familias_dict = {
        f["id_familia"]: f
        for f in familias.data
    }

    lista = []

    for produto in produtos_modelo.data:

        subfamilia = subfamilias_dict.get(
            produto["id_subfamilia"]
        )

        if not subfamilia:
            continue

        familia = familias_dict.get(
            subfamilia["familia_id_familia"]
        )

        if not familia:
            continue

        produto_base = produtos_dict.get(
            produto["id_modelo"]
        )

        if not produto_base:
            continue

        lista.append({
            "referencia":
                produto_base["referencia"],

            "nome":
                produto["nome_catalogo"],

            "descricao":
                produto["descricao_catalogo"],

            "descricao_detalhada":
                produto["descricao_detalhada"],

            "preco":
                produto_base["preco_base_iva"],

            "stock":
                produto_base["quantidade_stock"],

            "descontinuado":
                produto_base["descontinuado"],

            "codigo_barras":
                produto_base["codigo_barras_produto"],

            "familia":
                familia["nome"],

            "familia_ordem":
                familia["ordem"],

            "subfamilia":
                subfamilia["nome"],

            "subfamilia_ordem":
                subfamilia["ordem"]
        })

    lista.sort(
        key=lambda p: (
            p["familia_ordem"],
            p["subfamilia_ordem"],
            p["nome"]
        )
    )

    total_produtos = len(lista)

    total_paginas = max(
        1,
        (
            total_produtos
            + PRODUTOS_POR_PAGINA
            - 1
        ) // PRODUTOS_POR_PAGINA
    )

    pagina = max(
        1,
        min(
            pagina,
            total_paginas
        )
    )

    inicio = (
        pagina - 1
    ) * PRODUTOS_POR_PAGINA

    fim = (
        inicio +
        PRODUTOS_POR_PAGINA
    )

    return (
        lista[inicio:fim],
        total_paginas
    )

def obter_produto_por_nome(nome):

    response = (
        supabase
        .table("produtos_modelo")
        .select("*")
        .eq(
            "nome_catalogo",
            nome
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    produto = response.data[0]

    subfamilia_response = (
        supabase
        .table("subfamilia")
        .select(
            "nome,familia_id_familia"
        )
        .eq(
            "id_subfamilia",
            produto["id_subfamilia"]
        )
        .limit(1)
        .execute()
    )

    if not subfamilia_response.data:
        return None

    subfamilia = (
        subfamilia_response.data[0]
    )

    familia_response = (
        supabase
        .table("familia")
        .select("nome")
        .eq(
            "id_familia",
            subfamilia["familia_id_familia"]
        )
        .limit(1)
        .execute()
    )

    nome_familia = ""

    if familia_response.data:
        nome_familia = (
            familia_response.data[0]["nome"]
        )

    produto_base_response = (
        supabase
        .table("produtos")
        .select("*")
        .eq(
            "id_modelo",
            produto["id_modelo"]
        )
        .limit(1)
        .execute()
    )

    if not produto_base_response.data:
        return None

    produto_base = (
        produto_base_response.data[0]
    )

    return {
        "referencia":
            produto_base["referencia"],

        "nome":
            produto["nome_catalogo"],

        "descricao":
            produto["descricao_catalogo"],

        "descricao_detalhada":
            produto["descricao_detalhada"],

        "preco":
            produto_base["preco_base_iva"],

        "stock":
            produto_base["quantidade_stock"],

        "descontinuado":
            produto_base["descontinuado"],

        "codigo_barras":
            produto_base["codigo_barras_produto"],

        "familia":
            nome_familia,

        "subfamilia":
            subfamilia["nome"]
    }