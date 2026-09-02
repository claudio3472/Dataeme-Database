from config import supabase

from services.produto_service import (calcular_preco_com_iva)

def obter_pedido(cliente):
     
    response = (
            supabase
            .table("pedido")
            .select("id_pedido")
            .eq(
                "id_cliente",
                cliente
            )
            .eq(
                "estado",
                "aberto"
            )
            .limit(1)
            .execute()
        )

    if response.data:
            return response.data[0]
        
    return None


def obter_preco_por_referencia(referencia):

    # --------------------------------------------------------
    # PREÇO + IVA
    # --------------------------------------------------------

    produto_response = (
        supabase
        .table("produtos")
        .select("""
            preco_base,

            iva (
                id_iva,
                percentagem
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

    iva = produto.get("iva") or {}

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

    return preco_com_iva


def criar_pedido(id_cliente):

    cliente = {
        "id_cliente": id_cliente
    }


    response = (
        supabase 
        .table("pedido")
        .insert(cliente)
        .execute()
    )

    return response.data[0]["id_pedido"]


def criar_linha(quantidade, preco_unitario, valor_linha, id_pedido, produto_referencia):

    linha = {
        "quantidade": quantidade,
        "preco_unitario": preco_unitario,
        "valor_linha": valor_linha,
        "codigo_barras_linha": "Sem código",
        "id_pedido": id_pedido,
        "produto_referencia": produto_referencia
        
    }

    response = (
            supabase 
            .table("linhas_pedido")
            .insert(linha)
            .execute()
        )

    return response.data[0]["id_linha"]


def somar_preco_linhas(id_pedido):

    response = (
        supabase
        .table("linhas_pedido")
        .select("valor_linha")
        .eq("id_pedido", id_pedido)
        .execute()
    )

    total = 0

    for l in response.data:
        print(l)
        total += l["valor_linha"]

    att = atualizar_preco_total(total, id_pedido)

    return att



def atualizar_preco_total(total, id_pedido):

    response = (
        supabase
        .table("pedido")
        .update({
            "valor_total": float(total)
        })
        .eq("id_pedido", id_pedido)
        .execute()
    )

    return response.data[0]


