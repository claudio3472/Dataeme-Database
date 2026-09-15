from config import supabase

def obter_ivas():
    """
    Obtém todas as taxas de IVA existentes.
    """

    response = (
        supabase
        .table("iva")
        .select("*")
        .order("percentagem")   
        .execute()
    )

    return response.data or []


def atualizar_ivas(ivas):
    """
    Atualiza taxas de IVA existentes e cria novas taxas.

    'ivas' é uma lista de dicionários:
    [
        {"id_iva": 1, "percentagem": 23, "descricao": "Taxa normal"},
        {"id_iva": "novo-1", "percentagem": 13, "descricao": "Taxa intermédia"}
    ]

    IDs no formato "novo-X" representam taxas criadas no formulário
    e ainda sem um ID atribuído pela base de dados.
    """

    resultado = []

    for iva in ivas:
        id_iva = iva.get("id_iva")
        percentagem = iva.get("percentagem")
        descricao = iva.get("descricao")

        if percentagem is None or percentagem == "":
            continue

        if isinstance(id_iva, str) and id_iva.startswith("novo-"):
            response = (
                supabase
                .table("iva")
                .insert({
                    "percentagem": percentagem,
                    "descricao": descricao
                })
                .execute()
            )
        else:
            try:
                id_iva = int(id_iva)
            except (TypeError, ValueError):
                continue

            response = (
                supabase
                .table("iva")
                .update({
                    "percentagem": percentagem,
                    "descricao": descricao
                })
                .eq("id_iva", id_iva)
                .execute()
            )

        if response.data:
            resultado.append(response.data[0])

    return resultado

def criar_ivas(ivas):
    """
    Cria novas taxas de IVA.

    Cada item de 'ivas' é um dicionário:
    {"percentagem": ..., "descricao": ...}

    Linhas sem percentagem são ignoradas (linha deixada vazia pelo utilizador).
    """

    criados = []

    for iva in ivas:

        percentagem = iva.get("percentagem")

        if not percentagem:
            continue

        response = (
            supabase
            .table("iva")
            .insert({
                "percentagem": percentagem,
                "descricao": iva.get("descricao")
            })
            .execute()
        )

        if response.data:
            criados.append(response.data[0])

    return criados


def agrupar_itens_pedidos(info):
    """
    Agrupa os itens de vários pedidos por produto,
    somando a quantidade total comprada e o valor total.
    """

    grupos = {}

    for item in info:

        chave = item["referencia"]

        if chave not in grupos:

            grupos[chave] = {
                "referencia": item["referencia"],
                "nome_produto": item["nome_produto"],
                "cor": item["cor"],
                "codigo": item["codigo"],
                "quantidade_total": 0,
                "valor_total": 0,
                "num_pedidos": set()
            }

        grupos[chave]["quantidade_total"] += item["quantidade"]
        grupos[chave]["valor_total"] += item["preco_total"]
        grupos[chave]["num_pedidos"].add(item["id_pedido"])

    resultado = []

    for grupo in grupos.values():

        grupo["num_pedidos"] = len(grupo["num_pedidos"])
        resultado.append(grupo)

    return sorted(
        resultado,
        key=lambda g: g["quantidade_total"],
        reverse=True
    )

def obter_produtos_admin(filtro=None):
    """
    Obtém os modelos de produtos e todas as suas variantes (cores).
    """

    modelos_query = (
        supabase
        .table("produtos_modelo")
        .select(
            "id_modelo, "
            "nome_catalogo, "
            "descricao_catalogo, "
            "descricao_detalhada, "
            "id_subfamilia"
        )
        .order("nome_catalogo")
    )

    if filtro:
        modelos_query = modelos_query.ilike(
            "nome_catalogo",
            f"%{filtro}%"
        )

    modelos_response = modelos_query.execute()

    if not modelos_response.data:
        return []

    modelos = modelos_response.data

    # --------------------------------------------------------
    # SUBFAMÍLIAS E FAMÍLIAS
    # --------------------------------------------------------

    subfamilias_response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia, nome, familia_id_familia")
        .execute()
    )

    subfamilias = {
        s["id_subfamilia"]: s
        for s in (subfamilias_response.data or [])
    }

    familias_response = (
        supabase
        .table("familia")
        .select("id_familia, nome")
        .execute()
    )

    familias = {
        f["id_familia"]: f
        for f in (familias_response.data or [])
    }

    # --------------------------------------------------------
    # UMA ÚNICA QUERY PARA TODAS AS VARIANTES DE TODOS OS MODELOS
    # --------------------------------------------------------

    ids_modelo = [
        modelo["id_modelo"] for modelo in modelos
    ]

    produtos_response = (
        supabase
        .table("produtos")
        .select(
            "referencia",
            "id_modelo",
            "id_cor",
            "preco_base",
            "descontinuado",
            "quantidade_stock",
            "codigo_barras_produto"
        )
        .in_("id_modelo", ids_modelo)
        .order("referencia")
        .execute()
    )

    produtos_todos = produtos_response.data or []

    # Agrupar variantes por modelo (em memória, O(n))
    produtos_por_modelo = {}

    for produto in produtos_todos:
        produtos_por_modelo.setdefault(
            produto["id_modelo"],
            []
        ).append(produto)

    # --------------------------------------------------------
    # UMA ÚNICA QUERY PARA TODAS AS CORES DE TODOS OS PRODUTOS
    # --------------------------------------------------------

    cores_ids = list({
        p["id_cor"]
        for p in produtos_todos
        if p.get("id_cor") is not None
    })

    cores = {}

    if cores_ids:
        cores_response = (
            supabase
            .table("cores_produto")
            .select(
                "id_cor, nome_cor, codigo_cor, imagem_url"
            )
            .in_("id_cor", cores_ids)
            .execute()
        )

        cores = {
            c["id_cor"]: c
            for c in (cores_response.data or [])
        }

    # ========================================================
    # MONTAR RESULTADO
    # ========================================================

    resultado = []

    for modelo in modelos:

        id_modelo = modelo["id_modelo"]

        produtos = produtos_por_modelo.get(id_modelo, [])

        variantes = []

        for produto in produtos:

            cor = cores.get(produto["id_cor"])

            variantes.append({
                "referencia": produto["referencia"],
                "id_cor": produto["id_cor"],
                "cor": cor["nome_cor"] if cor else "",
                "codigo_cor": cor["codigo_cor"] if cor else "",
                "imagem_url": cor["imagem_url"] if cor else "",
                "preco_base": produto["preco_base"],
                "descontinuado": produto["descontinuado"],
                "stock": produto["quantidade_stock"],
                "codigo_barras": produto.get("codigo_barras", "")
            })

        subfamilia = subfamilias.get(modelo["id_subfamilia"])

        familia = None

        if subfamilia:
            familia = familias.get(
                subfamilia["familia_id_familia"]
            )

        resultado.append({
            "id_modelo": modelo["id_modelo"],
            "nome": modelo["nome_catalogo"],
            "descricao": modelo["descricao_catalogo"],
            "descricao_detalhada": modelo["descricao_detalhada"],
            "familia": familia["nome"] if familia else "",
            "subfamilia": subfamilia["nome"] if subfamilia else "",
            "variantes": variantes
        })

    return resultado


def obter_produto_admin(referencia):
    """
    Obtém uma variante específica pelo número de referência.
    """

    response = (
        supabase
        .table("produtos")
        .select(
            "referencia, "
            "id_modelo, "
            "id_cor, "
            "preco_base, "
            "descontinuado, "
            "stock, "
            "codigo_barras"
        )
        .eq("referencia", referencia)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    produto = response.data[0]

    # Modelo
    modelo_response = (
        supabase
        .table("produtos_modelo")
        .select(
            "id_modelo, "
            "nome_catalogo"
        )
        .eq("id_modelo", produto["id_modelo"])
        .limit(1)
        .execute()
    )

    modelo = (
        modelo_response.data[0]
        if modelo_response.data
        else None
    )

    # Cor
    cor_response = (
        supabase
        .table("cores_produto")
        .select(
            "id_cor, nome_cor, codigo_cor, imagem_url"
        )
        .eq("id_cor", produto["id_cor"])
        .limit(1)
        .execute()
    )

    cor = (
        cor_response.data[0]
        if cor_response.data
        else None
    )

    return {
        "referencia": produto["referencia"],
        "id_modelo": produto["id_modelo"],
        "id_cor": produto["id_cor"],
        "nome": modelo["nome_catalogo"] if modelo else "",
        "cor": cor["nome_cor"] if cor else "",
        "codigo_cor": cor["codigo_cor"] if cor else "",
        "preco_base": produto["preco_base"],
        "descontinuado": produto["descontinuado"],
        "stock": produto.get("stock", 0),
        "codigo_barras": produto.get("codigo_barras", "")
    }


def atualizar_produto_admin(
    referencia,
    preco_base,
    stock,
    descontinuado
):
    """
    Atualiza apenas os dados da variante do produto.

    O nome do modelo e a cor não são alterados aqui.
    """

    response = (
        supabase
        .table("produtos")
        .update({
            "preco_base": preco_base,
            "quantidade_stock": stock,
            "descontinuado": descontinuado
        })
        .eq("referencia", referencia)
        .execute()
    )

    return response.data


def obter_clientes(filtro=None):

    query = (
        supabase
        .table("cliente")
        .select("*")
        .order("nome")
    )

    if filtro:
        query = query.or_(
            f"nome.ilike.%{filtro}%,"
            f"nif.ilike.%{filtro}%"
        )

    response = query.execute()

    return response.data


def obter_cliente_admin(id_cliente):

    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq("id_cliente", id_cliente)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def atualizar_cliente_admin(
    id_cliente,
    nome,
    nif,
    email,
    indicativo,
    telefone,
    codigo_postal,
    localizacao,
    morada
):

    response = (
        supabase
        .table("cliente")
        .update({
            "nome": nome,
            "nif": nif,
            "email": email,
            "indicativo": indicativo,
            "telefone": telefone,
            "codigo_postal": codigo_postal,
            "localizacao": localizacao,
            "morada": morada
        })
        .eq("id_cliente", id_cliente)
        .execute()
    )

    return response.data

def obter_info(filtro_cliente=None, data_inicio=None, data_fim=None):

    response = (
        supabase
        .table("linhas_pedido")
        .select("""
            produto_referencia,
            quantidade,
            valor_linha,

            produtos(
                id_modelo,
                preco_base,
                codigo_barras_produto,
                cores_produto(
                    nome_cor
                ),
                iva(
                    percentagem
                ),
                produtos_modelo(
                    nome_catalogo
                )
            ),

            pedido(
                id_pedido,
                valor_total,
                estado,
                observacoes,
                data_pedido,
                id_cliente,
                cliente(
                    nome
                )
            )
        """)
        .execute()
    )

    if not response.data:
        return []

    info = []

    for r in response.data:

        ped = r.get("pedido")
        prod = r.get("produtos")

        if not ped or not prod:
            continue

        cli = ped.get("cliente") or {}
        cor = prod.get("cores_produto") or {}
        iva = prod.get("iva") or {}
        model = prod.get("produtos_modelo") or {}

        info.append({
            "data": ped["data_pedido"],
            "id_pedido": ped["id_pedido"],
            "valor_total": ped["valor_total"],
            "estado_pedido": ped["estado"],
            "observacoes": ped["observacoes"],
            "nome_cliente": cli.get("nome"),
            "num_cliente": ped["id_cliente"],

            "id_modelo": prod["id_modelo"],
            "referencia": r["produto_referencia"],
            "preco": round(
                prod["preco_base"] * (
                    1 + iva.get("percentagem", 0) / 100
                ),
                2
            ),
            "nome_produto": model.get("nome_catalogo"),
            "quantidade": r["quantidade"],
            "codigo": prod["codigo_barras_produto"],
            "preco_total": r["valor_linha"],
            "cor": cor.get("nome_cor")
        })

    # --------------------------------------------------------
    # FILTRAR POR CLIENTE (nome ou número)
    # --------------------------------------------------------

    if filtro_cliente:

        filtro_lower = filtro_cliente.lower()

        info = [
            i for i in info
            if filtro_lower in (i["nome_cliente"] or "").lower()
            or filtro_lower == str(i["num_cliente"])
        ]

    # --------------------------------------------------------
    # FILTRAR POR PERÍODO
    # --------------------------------------------------------

    if data_inicio:
        info = [
            i for i in info
            if i["data"] and i["data"] >= data_inicio
        ]

    if data_fim:
        info = [
            i for i in info
            if i["data"] and i["data"] <= data_fim
        ]

    return sorted(
        info,
        key=lambda p: p["num_cliente"]
    )

def atualizar_estado_pedido_admin(id_pedido, estado):

    response = (
        supabase
        .table("pedido")
        .update({"estado": estado})
        .eq("id_pedido", id_pedido)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]