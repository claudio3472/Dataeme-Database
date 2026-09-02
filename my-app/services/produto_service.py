from config import supabase

PRODUTOS_POR_PAGINA = 5


def calcular_preco_com_iva(preco_base, percentagem_iva):

    preco_base = float(preco_base or 0)
    percentagem_iva = float(percentagem_iva or 0)

    return round(
        preco_base * (1 + percentagem_iva / 100),
        2
    )


# ============================================================
# OBTER PRODUTOS PARA O CATÁLOGO
# ============================================================

def obter_produtos(pagina=1):

    produtos_modelo_response = (
        supabase
        .table("produtos_modelo")
        .select("*")
        .execute()
    )

    subfamilias_response = (
        supabase
        .table("subfamilia")
        .select("*")
        .execute()
    )

    familias_response = (
        supabase
        .table("familia")
        .select("*")
        .execute()
    )

    produtos_modelo = produtos_modelo_response.data or []
    subfamilias = subfamilias_response.data or []
    familias = familias_response.data or []

    # --------------------------------------------------------
    # DICIONÁRIOS PARA ACESSO MAIS RÁPIDO
    # --------------------------------------------------------

    subfamilias_dict = {
        subfamilia["id_subfamilia"]: subfamilia
        for subfamilia in subfamilias
    }

    familias_dict = {
        familia["id_familia"]: familia
        for familia in familias
    }

    lista = []

    # ========================================================
    # PARA CADA MODELO
    # ========================================================

    for modelo in produtos_modelo:

        # ----------------------------------------------------
        # OBTER SUBFAMÍLIA
        # ----------------------------------------------------

        subfamilia = subfamilias_dict.get(
            modelo["id_subfamilia"]
        )

        if not subfamilia:
            continue

        # ----------------------------------------------------
        # OBTER FAMÍLIA
        # ----------------------------------------------------

        familia = familias_dict.get(
            subfamilia["familia_id_familia"]
        )

        if not familia:
            continue

        # ----------------------------------------------------
        # OBTER TODOS OS PRODUTOS / VARIANTES DO MODELO
        # ----------------------------------------------------

        produtos_response = (
            supabase
            .table("produtos")
            .select("""
                referencia,
                preco_base,
                quantidade_stock,
                codigo_barras_produto,
                descontinuado,

                iva (
                    percentagem
                ),

                cores_produto (
                    id_cor,
                    nome_cor,
                    codigo_cor
                )
            """)
            .eq(
                "id_modelo",
                modelo["id_modelo"]
            )
            .order("referencia")
            .execute()
        )

        produtos_variantes = produtos_response.data or []

        if not produtos_variantes:
            continue

        # ----------------------------------------------------
        # PRODUTO BASE
        # Primeiro produto será mostrado no catálogo
        # ----------------------------------------------------

        produto_base = produtos_variantes[0]

        iva = produto_base.get("iva") or {}

        preco_com_iva = calcular_preco_com_iva(
            produto_base.get("preco_base"),
            iva.get("percentagem")
        )

        # ----------------------------------------------------
        # CORES DO MODELO
        # ----------------------------------------------------

        cores = []
        ids_cores_adicionados = set()

        for produto in produtos_variantes:

            cor = produto.get("cores_produto")

            if not cor:
                continue

            id_cor = cor.get("id_cor")

            # Evitar cores repetidas
            if id_cor in ids_cores_adicionados:
                continue

            ids_cores_adicionados.add(id_cor)

            cores.append({
                "referencia": produto["referencia"],
                "nome": cor.get("nome_cor"),
                "codigo": cor.get("codigo_cor")
            })

        # ----------------------------------------------------
        # ADICIONAR MODELO À LISTA
        # ----------------------------------------------------

        lista.append({

            "referencia":
                produto_base["referencia"],

            "id_modelo":
                modelo["id_modelo"],

            "nome":
                modelo["nome_catalogo"],

            "descricao":
                modelo.get("descricao_catalogo"),

            "descricao_detalhada":
                modelo.get("descricao_detalhada"),

            "preco":
                preco_com_iva,

            "stock":
                produto_base.get("quantidade_stock", 0),

            "codigo_barras":
                produto_base.get("codigo_barras_produto"),

            "descontinuado":
                produto_base.get("descontinuado", False),

            "familia":
                familia["nome"],

            "familia_ordem":
                familia["ordem"],

            "subfamilia":
                subfamilia["nome"],

            "subfamilia_ordem":
                subfamilia["ordem"],

            "cor_familia":
                familia.get("cor"),

            "cores":
                cores
        })

    # ========================================================
    # ORDENAR
    # ========================================================

    lista.sort(
        key=lambda produto: (
            produto["familia_ordem"],
            produto["subfamilia_ordem"],
            produto["nome"] or ""
        )
    )

    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    total_produtos = len(lista)

    total_paginas = max(
        1,
        (
            total_produtos +
            PRODUTOS_POR_PAGINA -
            1
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

    fim = inicio + PRODUTOS_POR_PAGINA

    return (
        lista[inicio:fim],
        total_paginas
    )


# ============================================================
# OBTER UM PRODUTO PELA REFERÊNCIA
# ============================================================

def obter_produto_por_referencia(referencia):

    # --------------------------------------------------------
    # PRODUTO + IVA + COR
    # --------------------------------------------------------

    produto_response = (
        supabase
        .table("produtos")
        .select("""
            referencia,
            id_modelo,
            preco_base,
            quantidade_stock,
            codigo_barras_produto,
            descontinuado,

            iva (
                id_iva,
                percentagem,
                descricao
            ),

            cores_produto (
                id_cor,
                nome_cor,
                codigo_cor,
                imagem_url
            )
        """)
        .eq(
            "referencia",
            referencia
        )
        .limit(1)
        .execute()
    )

    if not produto_response.data:
        return None

    produto = produto_response.data[0]

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    modelo_response = (
        supabase
        .table("produtos_modelo")
        .select("*")
        .eq(
            "id_modelo",
            produto["id_modelo"]
        )
        .limit(1)
        .execute()
    )

    if not modelo_response.data:
        return None

    modelo = modelo_response.data[0]

    # --------------------------------------------------------
    # SUBFAMÍLIA
    # --------------------------------------------------------

    subfamilia_response = (
        supabase
        .table("subfamilia")
        .select("*")
        .eq(
            "id_subfamilia",
            modelo["id_subfamilia"]
        )
        .limit(1)
        .execute()
    )

    if not subfamilia_response.data:
        return None

    subfamilia = subfamilia_response.data[0]

    # --------------------------------------------------------
    # FAMÍLIA
    # --------------------------------------------------------

    familia_response = (
        supabase
        .table("familia")
        .select("*")
        .eq(
            "id_familia",
            subfamilia["familia_id_familia"]
        )
        .limit(1)
        .execute()
    )

    if not familia_response.data:
        return None

    familia = familia_response.data[0]

    # --------------------------------------------------------
    # VARIANTES / CORES
    # --------------------------------------------------------

    variantes_response = (
        supabase
        .table("produtos")
        .select("""
            referencia,

            cores_produto (
                id_cor,
                nome_cor,
                codigo_cor
            )
        """)
        .eq(
            "id_modelo",
            modelo["id_modelo"]
        )
        .order("referencia")
        .execute()
    )

    variantes = []

    for variante in variantes_response.data or []:

        cor_info = variante.get("cores_produto")

        if not cor_info:
            continue

        variantes.append({

            "referencia":
                variante["referencia"],

            "nome_cor":
                cor_info.get("nome_cor"),

            "codigo_cor":
                cor_info.get("codigo_cor")
        })

    # --------------------------------------------------------
    # IVA E PREÇO
    # --------------------------------------------------------

    iva = produto.get("iva") or {}
    cor = produto.get("cores_produto") or {}

    preco_base = float(
        produto.get("preco_base") or 0
    )

    percentagem_iva = float(
        iva.get("percentagem") or 0
    )

    preco_com_iva = calcular_preco_com_iva(
        preco_base,
        percentagem_iva
    )

    # ========================================================
    # DEVOLVER PRODUTO
    # ========================================================

    return {

        "referencia":
            produto["referencia"],

        "id_modelo":
            modelo["id_modelo"],

        "nome":
            modelo["nome_catalogo"],

        "descricao":
            modelo.get("descricao_catalogo"),

        "descricao_detalhada":
            modelo.get("descricao_detalhada"),

        "preco_com_iva":
            preco_com_iva,

        "preco_base":
            preco_base,

        "iva":
            percentagem_iva,

        "stock":
            produto.get("quantidade_stock", 0),

        "codigo_barras":
            produto.get("codigo_barras_produto"),

        "descontinuado":
            produto.get("descontinuado", False),

        "cor":
            cor.get("nome_cor"),

        "codigo_cor":
            cor.get("codigo_cor"),

        "imagem_url":
            cor.get("imagem_url"),

        "familia":
            familia["nome"],

        "subfamilia":
            subfamilia["nome"],

        "cor_familia":
            familia.get("cor"),

        "variantes":
            variantes
    }



    

