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
            return response.data[0]["id_pedido"]
        
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

    if not response.data:
        return None

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

    if not response.data:
        return None

    return response.data[0]["id_linha"]


def somar_preco_linhas(id_pedido):

    response = (
        supabase
        .table("linhas_pedido")
        .select("valor_linha")
        .eq("id_pedido", id_pedido)
        .execute()
    )

    if not response.data:
        return None
    
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

    if not response.data:
        return None

    return response.data[0]


def obter_linha(produto, id_pedido):

    response = (
        supabase
        .table("linhas_pedido")
        .select("id_linha")
        .eq("produto_referencia", produto)
        .eq("id_pedido", id_pedido)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]["id_linha"]


def atualizar_linha(quantidade, preco, id_linha):

    response_preco = (
        supabase
        .table("linhas_pedido")
        .select("quantidade", "valor_linha")
        .eq("id_linha", id_linha)
        .limit(1)
        .execute()
    )

    if not response_preco.data:
        return None
 
    response = (
        supabase
        .table("linhas_pedido")
        .update({
            "quantidade": response_preco.data[0]["quantidade"] + quantidade,
            "valor_linha": response_preco.data[0]["valor_linha"] + preco        
        })
        .eq("id_linha", id_linha)
        .execute()
    )

    if not response.data:
        return None
    
    return response.data[0]



def get_linhas(pedido):

    response_linha = (
        supabase
        .table("linhas_pedido")
        .select("""
        produto_referencia, 
        quantidade, 
        preco_unitario, 
        valor_linha,

        pedido (
            valor_total
        )
        
        
        """)
        .eq("id_pedido", pedido)
        .execute()
    )
    if not response_linha.data:
        return None

    valor = response_linha.data[0].get("pedido") or {}
    valor_total = f"{valor['valor_total']:.2f}"
    lista = [] 

    for prod in response_linha.data:

        ref = prod["produto_referencia"]

        response_produtos = (
            supabase
            .table("produtos")
            .select("""

                produtos_modelo (
                    nome_catalogo
                ),

                cores_produto(
                    nome_cor
                )
                
            """)
            .eq("referencia", ref)
            .execute()
        )
        if not response_produtos.data:
            return None

        modelo = response_produtos.data[0].get("produtos_modelo") or {}
        cor = response_produtos.data[0].get("cores_produto") or {}

        lista.append({
            "nome": modelo.get("nome_catalogo"),
            "cor": cor.get("nome_cor"),
            "quantidade": prod["quantidade"],
            "preco_unitario": f"{prod['preco_unitario']:.2f}",
            "valor_linha": f"{prod['valor_linha']:.2f}"
        })

    

    print(lista)
    return lista, valor_total

    
    

    
