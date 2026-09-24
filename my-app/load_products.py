import pandas as pd
from config import supabase
from services.admin_service import( traduzir_e_converter_cor)
from gerar_barcode import (barcode_text)


# ============================================================
# FAMÍLIA
# ============================================================

def obter_id_familia(nome, cor=None, descricao=None):

    response = (
        supabase
        .table("familia")
        .select("id_familia")
        .eq("nome", nome.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_familia"]

    return criar_id_familia(
        nome, cor, descricao
    )

def criar_id_familia(nome, cor=None, descricao=None):

    if pd.isna(cor):
        cor = "#0E7C86"

    elif not cor.startswith("#"):
        cor = traduzir_e_converter_cor(cor)



    if pd.isna(descricao):
        descricao = ""

    response = (
        supabase
        .table("familia")
        .insert({
            "nome": nome,
            "cor": cor,
            "descricao": descricao,
            "pagina_inicial": 0,
            "pagina_final": 0
        })
        .execute()
    )
    
    if not response.data:
        raise Exception(
            f"Erro ao criar a família: {nome}"
        )

    return response.data[0]["id_familia"]


# ============================================================
# SUBFAMÍLIA
# ============================================================

def obter_id_subfamilia(nome, id_familia, descricao=None):

    response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia")
        .eq("nome", nome.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_subfamilia"]

    return criar_id_subfamilia(
        nome, id_familia, descricao
    )

def criar_id_subfamilia(nome, id_familia, descricao=None):

    if pd.isna(descricao):
        descricao = ""

    response = (
        supabase
        .table("subfamilia")
        .insert({
            "nome": nome,
            "descricao": descricao,
            "pagina": 0,
            "familia_id_familia": id_familia
        })
        .execute()
    )
    
    if not response.data:
        raise Exception(
            f"Erro ao criar a subfamília: {nome}"
        )

    return response.data[0]["id_subfamilia"]


# ============================================================
# COR
# ============================================================

def obter_id_cor(nome_cor):

    response = (
        supabase
        .table("cores_produto")
        .select("id_cor")
        .eq("nome_cor", nome_cor.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_cor"]

    return None


def criar_cor(nome_cor, codigo_cor):

    if not codigo_cor.startswith("#"):
        codigo_cor = traduzir_e_converter_cor(codigo_cor)
        
    response = (
        supabase
        .table("cores_produto")
        .insert({
            "nome_cor": nome_cor.strip(),
            "codigo_cor": codigo_cor,
            "imagem_url": None
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar a cor: {nome_cor}"
        )

    return response.data[0]["id_cor"]


def obter_ou_criar_cor(nome_cor, codigo_cor):
    if pd.isna(nome_cor):
        nome_cor = "Sem Cor"
        
    id_cor = obter_id_cor(nome_cor)

    if id_cor is not None:
        return id_cor
    
    if nome_cor == "Sem Cor":
        return criar_cor(
            nome_cor,
            "#ffffff"
        )
        
    return criar_cor(
        nome_cor,
        codigo_cor
    )


# ============================================================
# MODELO DO PRODUTO
# ============================================================

def obter_id_modelo(nome):

    response = (
        supabase
        .table("produtos_modelo")
        .select("id_modelo")
        .eq("nome_catalogo", nome.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_modelo"]

    return None


def criar_modelo(
    nome,
    id_subfamilia,
    descricao_catalogo=None,
    descricao_detalhada=None
):
    if pd.isna(descricao_catalogo):
        descricao_catalogo = "Sem Descrição"
        
    if pd.isna(descricao_detalhada):
        descricao_detalhada = "Sem Descrição"
        
    response = (
        supabase
        .table("produtos_modelo")
        .insert({
            "nome_catalogo": nome.strip(),
            "descricao_catalogo": descricao_catalogo,
            "descricao_detalhada": descricao_detalhada,
            "id_subfamilia": id_subfamilia
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar modelo: {nome}"
        )

    return response.data[0]["id_modelo"]


def obter_ou_criar_modelo(
    nome,
    id_subfamilia,
    descricao_catalogo=None,
    descricao_detalhada=None
):

    id_modelo = obter_id_modelo(nome)

    if id_modelo is not None:
        return id_modelo

    return criar_modelo(
        nome,
        id_subfamilia,
        descricao_catalogo,
        descricao_detalhada,
        
    )


# ============================================================
# IVA
# ============================================================

def obter_id_iva(percentagem):

    percentagem = float(percentagem)

    response = (
        supabase
        .table("iva")
        .select("id_iva")
        .eq("percentagem", percentagem)
        .execute()
    )

    if response.data:
        return response.data[0]["id_iva"]

    return None


def criar_iva(percentagem, categoria=None):
    
    if pd.isna(categoria):
        categoria = ""
        
    percentagem = float(percentagem)

    response = (
        supabase
        .table("iva")
        .insert({
            "percentagem": percentagem,
            "descricao": categoria
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar IVA: {percentagem}%"
        )

    return response.data[0]["id_iva"]


def obter_ou_criar_iva(percentagem, categoria=None):

    id_iva = obter_id_iva(percentagem)

    if id_iva is not None:
        return id_iva

    return criar_iva(percentagem, categoria)


# ============================================================
# PRODUTO
# ============================================================

def produto_existe(referencia):

    response = (
        supabase
        .table("produtos")
        .select("referencia")
        .eq("referencia", int(referencia))
        .execute()
    )

    return bool(response.data)


# ============================================================
# IMPORTAÇÃO
# ============================================================

def importar_produtos(ficheiro):
    extensoes_aceites_X = (".xlsx", ".xls")

    if ficheiro.filename.lower().endswith(extensoes_aceites_X):

        # sheet_name=0 -> lê só a primeira folha e devolve já um DataFrame
        df = pd.read_excel(
            ficheiro,
            sheet_name=0,
            usecols="A:P",
        )

    else:

        df = pd.read_csv(
                ficheiro,
                sep=","
        )

    for _, row in df.iterrows():

        referencia = int(
            row["Referência"]
        )

        print(
            f"\nProcessando produto: {referencia}"
        )

        # ------------------------------------------------
        # VERIFICAR PRODUTO
        # ------------------------------------------------

        if produto_existe(referencia):

            print(
                f"Produto {referencia} "
                f"já existe. Ignorado."
            )

            continue

        try:

            # ------------------------------------------------
            # FAMÍLIA
            # ------------------------------------------------

            id_familia = obter_id_familia(
                row["Família"],
                row["Cor da Família"],
                row["Descrição Família"]
            )

            if id_familia is None:
                continue

            # ------------------------------------------------
            # SUBFAMÍLIA
            # ------------------------------------------------

            id_subfamilia = obter_id_subfamilia(
                row["Subfamília"],
                id_familia,
                row["Descrição Subfamília"]
            )

            if id_subfamilia is None:
                continue

            # ------------------------------------------------
            # IVA
            # ------------------------------------------------

            id_iva = obter_ou_criar_iva(
                row["Percentagem IVA"],
                row["Categoria IVA"]
            )

            if id_iva is None:
                continue

            # ------------------------------------------------
            # COR
            # ------------------------------------------------

            id_cor = obter_ou_criar_cor(
                row["Nome Cor"],
                row["Código Cor"]
            )

            if id_cor is None:
                continue

            # ------------------------------------------------
            # MODELO
            # ------------------------------------------------

            id_modelo = obter_ou_criar_modelo(
                row["Nome Produto"],
                id_subfamilia,
                row["Descrição Breve"],
                row["Descrição Detalhada"]
            )

            if id_modelo is None:
                continue

            # ------------------------------------------------
            # PREÇO
            # ------------------------------------------------

            preco = row["Preço Base Sem IVA"]

            if pd.isna(preco):
                continue

            # ------------------------------------------------
            # STOCK
            # ------------------------------------------------

            stock = row["Stock"]

            if pd.isna(stock):
                stock = 9999

            # ------------------------------------------------
            # DESCONTINUADO
            # ------------------------------------------------

            descontinuado = row["Descontinuado?"]

            if pd.isna(descontinuado):
                descontinuado = False

            # ------------------------------------------------
            # BARCODE
            # ------------------------------------------------

            barcode = barcode_text(referencia)

            # ------------------------------------------------
            # INSERIR PRODUTO
            # ------------------------------------------------

            supabase \
                .table("produtos") \
                .insert({
                    "referencia": referencia,
                    "id_modelo": id_modelo,
                    "id_cor": id_cor,
                    "preco_base": float(preco),
                    "id_iva": id_iva,
                    "quantidade_stock": int(stock),
                    "codigo_barras_produto": barcode,
                    "descontinuado": bool(descontinuado)
                }) \
                .execute()

            print(
                f"Produto {referencia} "
                f"inserido com sucesso."
            )

        except Exception as erro:

            print(
                f"ERRO no produto "
                f"{referencia}: {erro}"
            )