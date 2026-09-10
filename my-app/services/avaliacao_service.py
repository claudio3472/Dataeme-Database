import re
from config import supabase
from datetime import date

def criar_avaliacao(id_cliente, referencia, classificacao, comentario):

    avaliacao = {
        "classificacao": classificacao,
        "comentario": comentario,
        "id_cliente": id_cliente,
        "produto_referencia": referencia,
        "data_avaliacao": date.today().isoformat()
    }

    response = (
        supabase
        .table("avaliacoes")
        .insert(avaliacao)
        .execute()
    )

    if response.data:
        return response.data[0]["id_avaliacoes"]
        
    return None


def comparar_avaliacao(id_cliente, referencia, classificacao, comentario):

    response = (
        supabase
        .table("avaliacoes")
        .select("id_avaliacoes", )
        .eq("id_cliente", id_cliente)
        .eq("produto_referencia", referencia)
        .limit(1)
        .execute()
    )

    if response.data:
        return atualizar_avaliacao(classificacao=classificacao, comentario=comentario, id_avaliacoes=response.data[0]["id_avaliacoes"])
        
    return criar_avaliacao(id_cliente=id_cliente, referencia=referencia, classificacao=classificacao, comentario=comentario)


def atualizar_avaliacao(classificacao, comentario, id_avaliacoes):

    response = (
        supabase
        .table("avaliacoes")
        .update({
            "classificacao": classificacao,
            "comentario": comentario,
            "data_avaliacao": date.today().isoformat()
        })
        .eq("id_avaliacoes", id_avaliacoes)
        .execute()
    )

    if not response.data:
        return None
    
    return response.data[0]
