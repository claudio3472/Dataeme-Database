from config import supabase


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

    # Obter subfamílias
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

    # Obter famílias
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

    resultado = []

    for modelo in modelos:

        id_modelo = modelo["id_modelo"]

        # Obter todas as variantes deste modelo
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
            .eq("id_modelo", id_modelo)
            .order("referencia")
            .execute()
        )

        produtos = produtos_response.data or []

        # Obter cores
        cores_ids = [
            p["id_cor"]
            for p in produtos
            if p.get("id_cor") is not None
        ]

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


def obter_info():

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

    return sorted(
        info,
        key=lambda p: p["num_cliente"]
    )

