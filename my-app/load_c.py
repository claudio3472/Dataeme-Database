import pandas as pd

from config import supabase


CSV_PATH = "data/produtos2.csv"


# ============================================================
# HELPERS
# ============================================================

def limpar_valor(valor):
    """
    Converts pandas NaN values into None.
    """
    if pd.isna(valor):
        return None

    if isinstance(valor, str):
        valor = valor.strip()

    return valor


# ============================================================
# CORES
# ============================================================

def obter_id_cor(nome_cor):
    """
    Returns the id_cor of an existing colour.
    Returns None if the colour does not exist.
    """

    nome_cor = limpar_valor(nome_cor)

    if not nome_cor:
        return None

    response = (
        supabase
        .table("cores_produto")
        .select("id_cor")
        .ilike("nome_cor", nome_cor)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["id_cor"]

    return None


def criar_cor(nome_cor, codigo_cor):
    """
    Creates a new colour and returns its id_cor.
    """

    nome_cor = limpar_valor(nome_cor)
    codigo_cor = limpar_valor(codigo_cor)

    if not nome_cor:
        raise ValueError(
            "Nome da cor não pode ser vazio."
        )

    response = (
        supabase
        .table("cores_produto")
        .insert({
            "nome_cor": nome_cor,
            "codigo_cor": codigo_cor,
            "imagem_url": None
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Não foi possível criar a cor: {nome_cor}"
        )

    return response.data[0]["id_cor"]


def obter_ou_criar_cor(nome_cor, codigo_cor):
    """
    Gets an existing colour or creates it if necessary.
    """

    id_cor = obter_id_cor(nome_cor)

    if id_cor is not None:

        print(
            f"  ✓ Cor existente: {nome_cor} "
            f"(id={id_cor})"
        )

        return id_cor

    id_cor = criar_cor(
        nome_cor,
        codigo_cor
    )

    print(
        f"  + Cor criada: {nome_cor} "
        f"(id={id_cor})"
    )

    return id_cor


# ============================================================
# SUBFAMÍLIAS
# ============================================================

def obter_id_subfamilia(nome_subfamilia):
    """
    Returns the id_subfamilia.
    """

    nome_subfamilia = limpar_valor(
        nome_subfamilia
    )

    if not nome_subfamilia:
        return None

    response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia")
        .eq(
            "nome",
            nome_subfamilia
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["id_subfamilia"]

    return None


# ============================================================
# PRODUTOS MODELO
# ============================================================

def obter_id_modelo(nome):
    """
    Returns the id_modelo of an existing product model.
    """

    nome = limpar_valor(nome)

    if not nome:
        return None

    response = (
        supabase
        .table("produtos_modelo")
        .select("id_modelo")
        .eq(
            "nome_catalogo",
            nome
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["id_modelo"]

    return None


def criar_modelo(
    nome,
    descricao_catalogo,
    descricao_detalhada,
    id_subfamilia
):
    """
    Creates a product model.
    """

    response = (
        supabase
        .table("produtos_modelo")
        .insert({
            "nome_catalogo": nome,
            "descricao_catalogo": descricao_catalogo,
            "descricao_detalhada": descricao_detalhada,
            "id_subfamilia": id_subfamilia
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Não foi possível criar o modelo: {nome}"
        )

    return response.data[0]["id_modelo"]


def obter_ou_criar_modelo(row, id_subfamilia):
    """
    Gets an existing product model or creates it.
    """

    nome = limpar_valor(
        row["nome"]
    )

    id_modelo = obter_id_modelo(nome)

    if id_modelo is not None:

        print(
            f"  ✓ Modelo existente: {nome} "
            f"(id={id_modelo})"
        )

        return id_modelo


    descricao_catalogo = limpar_valor(
        row["descrição no catalogo"]
    )

    descricao_detalhada = limpar_valor(
        row["descricao"]
    )


    id_modelo = criar_modelo(
        nome,
        descricao_catalogo,
        descricao_detalhada,
        id_subfamilia
    )

    print(
        f"  + Modelo criado: {nome} "
        f"(id={id_modelo})"
    )

    return id_modelo


# ============================================================
# PRODUTOS
# ============================================================

def obter_produto(referencia):
    """
    Returns a product by its reference.
    """

    response = (
        supabase
        .table("produtos")
        .select("*")
        .eq(
            "referencia",
            int(referencia)
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def criar_produto(
    referencia,
    id_modelo,
    id_cor,
    preco,
    stock,
    codigo_barras,
    descontinuado
):
    """
    Creates a concrete product.
    """

    response = (
        supabase
        .table("produtos")
        .insert({
            "referencia": referencia,
            "id_modelo": id_modelo,
            "id_cor": id_cor,
            "preco_base_iva": preco,
            "quantidade_stock": stock,
            "codigo_barras_produto": codigo_barras,
            "descontinuado": descontinuado
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Não foi possível criar o produto "
            f"{referencia}"
        )

    return response.data[0]


def atualizar_produto(
    referencia,
    id_modelo,
    id_cor,
    preco,
    stock,
    codigo_barras,
    descontinuado
):
    """
    Updates an existing product.
    """

    response = (
        supabase
        .table("produtos")
        .update({
            "id_modelo": id_modelo,
            "id_cor": id_cor,
            "preco_base_iva": preco,
            "quantidade_stock": stock,
            "codigo_barras_produto": codigo_barras,
            "descontinuado": descontinuado
        })
        .eq(
            "referencia",
            referencia
        )
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Não foi possível atualizar "
            f"o produto {referencia}"
        )

    return response.data[0]


# ============================================================
# IMPORTAR UMA LINHA
# ============================================================

def importar_linha(row):

    referencia = int(
        limpar_valor(
            row["referencia"]
        )
    )

    nome = limpar_valor(
        row["nome"]
    )

    nome_cor = limpar_valor(
        row["cor"]
    )

    codigo_cor = limpar_valor(
        row["codigo_cor"]
    )

    nome_subfamilia = limpar_valor(
        row["subfamilia"]
    )

    preco = float(
        limpar_valor(
            row["preco com iva"]
        )
    )

    stock = int(
        limpar_valor(
            row["Stock"]
        )
    )

    codigo_barras = limpar_valor(
        row["código de barras"]
    )

    descontinuado = (
        str(
            limpar_valor(
                row["descontinuado"]
            )
        ).lower() == "true"
    )


    print()
    print(
        "======================================"
    )
    print(
        f"Produto: {nome}"
    )
    print(
        f"Referência: {referencia}"
    )
    print(
        "======================================"
    )


    # --------------------------------------------------------
    # 1. SUBFAMÍLIA
    # --------------------------------------------------------

    id_subfamilia = obter_id_subfamilia(
        nome_subfamilia
    )

    if id_subfamilia is None:

        raise ValueError(
            f"Subfamília não encontrada: "
            f"{nome_subfamilia}"
        )

    print(
        f"  ✓ Subfamília: "
        f"{nome_subfamilia} "
        f"(id={id_subfamilia})"
    )


    # --------------------------------------------------------
    # 2. COR
    # --------------------------------------------------------

    id_cor = obter_ou_criar_cor(
        nome_cor,
        codigo_cor
    )


    # --------------------------------------------------------
    # 3. MODELO
    # --------------------------------------------------------

    id_modelo = obter_ou_criar_modelo(
        row,
        id_subfamilia
    )


    # --------------------------------------------------------
    # 4. PRODUTO
    # --------------------------------------------------------

    produto_existente = obter_produto(
        referencia
    )


    if produto_existente is None:

        criar_produto(
            referencia=referencia,
            id_modelo=id_modelo,
            id_cor=id_cor,
            preco=preco,
            stock=stock,
            codigo_barras=codigo_barras,
            descontinuado=descontinuado
        )

        print(
            f"  + Produto criado: {referencia}"
        )

    else:

        atualizar_produto(
            referencia=referencia,
            id_modelo=id_modelo,
            id_cor=id_cor,
            preco=preco,
            stock=stock,
            codigo_barras=codigo_barras,
            descontinuado=descontinuado
        )

        print(
            f"  ↻ Produto atualizado: {referencia}"
        )


# ============================================================
# IMPORTAR CSV COMPLETO
# ============================================================

def importar_produtos():

    df = pd.read_csv(
        CSV_PATH,
        sep=","
    )

    print(
        f"\nEncontradas {len(df)} linhas no CSV."
    )

    sucessos = 0
    erros = 0


    for index, row in df.iterrows():

        try:

            importar_linha(row)

            sucessos += 1

        except Exception as e:

            erros += 1

            print()
            print(
                f"❌ ERRO NA LINHA {index + 2}"
            )

            print(e)


    print()
    print("======================================")
    print("IMPORTAÇÃO TERMINADA")
    print("======================================")

    print(
        f"Sucessos: {sucessos}"
    )

    print(
        f"Erros: {erros}"
    )

    print(
        f"Total: {len(df)}"
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    importar_produtos()