from config import supabase

PRODUTOS_POR_PAGINA = 5


# ============================================================
# OBTER FAMÍLIAS E SUBFAMÍLIAS (PARA FILTROS)
# ============================================================

def obter_categorias():

    familias_response = (
        supabase
        .table("familia")
        .select("*")
        .order("ordem")
        .execute()
    )

    subfamilias_response = (
        supabase
        .table("subfamilia")
        .select("*")
        .order("ordem")
        .execute()
    )

    familias = familias_response.data or []
    subfamilias = subfamilias_response.data or []

    for familia in familias:
        familia["subfamilias"] = [
            sub for sub in subfamilias
            if sub["familia_id_familia"] == familia["id_familia"]
        ]

    return familias


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

def obter_produtos(pagina=1, id_familia=None, id_subfamilia=None):

    # --------------------------------------------------------
    # FAMÍLIAS E SUBFAMÍLIAS
    # --------------------------------------------------------

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

    subfamilias = subfamilias_response.data or []
    familias = familias_response.data or []

    subfamilias_dict = {
        subfamilia["id_subfamilia"]: subfamilia
        for subfamilia in subfamilias
    }

    familias_dict = {
        familia["id_familia"]: familia
        for familia in familias
    }

    # --------------------------------------------------------
    # RESTRINGIR SUBFAMÍLIAS RELEVANTES ANTES DE IR À BASE DE DADOS
    # --------------------------------------------------------

    ids_subfamilia_validas = None

    if id_subfamilia:
        ids_subfamilia_validas = [id_subfamilia]

    elif id_familia:
        ids_subfamilia_validas = [
            s["id_subfamilia"]
            for s in subfamilias
            if s["familia_id_familia"] == id_familia
        ]

        # Nenhuma subfamília nesta família -> não há produtos
        if not ids_subfamilia_validas:
            return [], 1

    # --------------------------------------------------------
    # OBTER APENAS OS MODELOS QUE INTERESSAM
    # --------------------------------------------------------

    modelos_query = (
        supabase
        .table("produtos_modelo")
        .select("*")
    )

    if ids_subfamilia_validas is not None:
        modelos_query = modelos_query.in_(
            "id_subfamilia",
            ids_subfamilia_validas
        )

    produtos_modelo = modelos_query.execute().data or []

    if not produtos_modelo:
        return [], 1

    # --------------------------------------------------------
    # UMA ÚNICA QUERY PARA TODAS AS VARIANTES DE TODOS OS MODELOS
    # --------------------------------------------------------

    ids_modelo = [
        modelo["id_modelo"]
        for modelo in produtos_modelo
    ]

    produtos_response = (
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
                percentagem
            ),

            cores_produto (
                id_cor,
                nome_cor,
                codigo_cor
            ),

            avaliacoes(
                classificacao
            )

        """)
        .in_("id_modelo", ids_modelo)
        .order("referencia")
        .execute()
    )

    produtos_todos = produtos_response.data or []

    # Agrupar variantes por modelo
    produtos_por_modelo = {}

    for produto in produtos_todos:
        produtos_por_modelo.setdefault(
            produto["id_modelo"],
            []
        ).append(produto)

    lista = []

    # ========================================================
    # PARA CADA MODELO
    # ========================================================

    for modelo in produtos_modelo:

        subfamilia = subfamilias_dict.get(
            modelo["id_subfamilia"]
        )

        if not subfamilia:
            continue

        familia = familias_dict.get(
            subfamilia["familia_id_familia"]
        )

        if not familia:
            continue

        produtos_variantes = produtos_por_modelo.get(
            modelo["id_modelo"],
            []
        )

        if not produtos_variantes:
            continue

        # ----------------------------------------------------
        # PRODUTO BASE
        # ----------------------------------------------------

        produto_base = produtos_variantes[0]

        iva = produto_base.get("iva") or {}

        preco_com_iva = calcular_preco_com_iva(
            produto_base.get("preco_base"),
            iva.get("percentagem")
        )

        # ----------------------------------------------------
        # CORES DO MODELO + AVALIAÇÕES
        # ----------------------------------------------------

        avaliacao = 0
        num_av = 0

        cores = []
        ids_cores_adicionados = set()

        for produto in produtos_variantes:

            cor = produto.get("cores_produto")

            if not cor:
                continue

            id_cor = cor.get("id_cor")

            if id_cor in ids_cores_adicionados:
                continue

            ids_cores_adicionados.add(id_cor)

            cores.append({
                "referencia": produto["referencia"],
                "nome": cor.get("nome_cor"),
                "codigo": cor.get("codigo_cor")
            })

            av = produto.get("avaliacoes") or []

            for item in av:
                classificacao = item.get("classificacao")
                if classificacao is not None:
                    avaliacao += classificacao
                    num_av += 1

        if num_av != 0:
            avaliacao /= num_av

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

            "id_familia":
                familia["id_familia"],

            "familia_ordem":
                familia["ordem"],

            "subfamilia":
                subfamilia["nome"],

            "id_subfamilia":
                subfamilia["id_subfamilia"],

            "subfamilia_ordem":
                subfamilia["ordem"],

            "cor_familia":
                familia.get("cor"),

            "cores":
                cores,

            "avaliacao":
                f"{avaliacao:.2f}",

            "num_avaliacao":
                num_av
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
    # PRODUTO + IVA + COR + MODELO + SUBFAMÍLIA + FAMÍLIA
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
            ),

            produtos_modelo (
                id_modelo,
                nome_catalogo,
                descricao_catalogo,
                descricao_detalhada,
                id_subfamilia,

                subfamilia (
                    id_subfamilia,
                    nome,
                    familia_id_familia,

                    familia (
                        id_familia,
                        nome,
                        ordem,
                        cor
                    )
                )
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

    modelo = produto.get("produtos_modelo")

    if not modelo:
        return None

    subfamilia = modelo.get("subfamilia")

    if not subfamilia:
        return None

    familia = subfamilia.get("familia")

    if not familia:
        return None

    # --------------------------------------------------------
    # VARIANTES / CORES / AVALIAÇÕES
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
            ),

            avaliacoes(
                classificacao
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

    avaliacao = 0
    num_av = 0

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

        av = variante.get("avaliacoes") or []

        for item in av:
            classificacao = item.get("classificacao")
            if classificacao is not None:
                avaliacao += classificacao
                num_av += 1

    if num_av != 0:
        avaliacao /= num_av

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

        "id_familia":
            familia["id_familia"],

        "subfamilia":
            subfamilia["nome"],

        "id_subfamilia":
            subfamilia["id_subfamilia"],

        "cor_familia":
            familia.get("cor"),

        "variantes":
            variantes,

        "avaliacao":
            avaliacao,

        "num_avaliacao":
            num_av
    }


def obter_avaliacao(id_modelo):
    
    response = (
        supabase
        .table("produtos")
        .select(""" 
                
            avaliacoes (
                classificacao,
                comentario,
                data_avaliacao, 
                
                cliente (
                    nome
                )
            )
                
        """)
        .eq("id_modelo", id_modelo)
        .execute()
    )
    
    lista_avaliacao = []

    for avaliacao in response.data:
        
        if avaliacao["comentario"].strip() is None:
            continue
        
        lista_avaliacao.append({
            
            "classificacao":
                avaliacao["classificacao"],
            
            "comentario":
                avaliacao["comentario"],
            
            "data_avaliacao":
                avaliacao["data_avaliacao"],
            
            "nome":
                avaliacao["nome"]
        })
        
        
    return {
        
        "lista_avaliacao":
            lista_avaliacao
    }
        
        
        
        