import pandas as pd
import json
from config import supabase

#Obtém o id subfamília de um produto
def obter_id_subfamilia(nome):

    response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia")
        .eq("nome", nome)
        .execute()
    )

    if response.data:
        return response.data[0]["id_subfamilia"]
    
    return None

#Inserção de produtos novos comforme o csv, sem duplicados.
def importar_produtos():

    df = pd.read_csv(
            "data/produtos.csv",
            sep=","
        )

    for _, row in df.iterrows():

        id_subfamilia = obter_id_subfamilia(
            row["subfamilia"]
        )

        if id_subfamilia is None:
            print("id subfamília não existe")
            continue
        
        existe = (
            supabase
            .table("produtos")
            .select("referencia")
            .eq("referencia", row["referencia"])
            .execute()
        )

        if existe.data:
            continue

        (
            supabase
            .table("produtos")
            .insert({
                "referencia": row["referencia"],
                "nome_catalogo": row["nome"],
                "descricao_catalogo": row["descrição no catalogo"],
                "descricao_detalhada": row["descricao"],
                "preco_base_iva": float(row["preco com iva"]),   
                "descontinuado": bool(row["descontinuado"]),
                "codigo_barras_produto": row["código de barras"],
                "quantidade_stock": int(row["Stock"]),
                "id_subfamilia": int(id_subfamilia)
            })
            .execute()
        )

#importar_produtos()

#Mostra todos os objetos na tabela dos produtos, ordenado por id da subfamília
def print_table():

    a = (
        supabase
        .table("produtos")
        .select("*")
        .order("id_subfamilia")
        .execute()
    )

    for row in a.data:

        b = (
            supabase
            .table("subfamilia")
            .select("nome")
            .eq("id_subfamilia", row["id_subfamilia"])
            .execute()
        )
        print("Referência: ", row["referencia"], "| Nome: ", row["nome_catalogo"], 
            "| Descrição: ", row["descricao_catalogo"], "| Descrição Detalhada: ", row["descricao_detalhada"],
            "| Preço Iva: ", row["preco_base_iva"], "| Descontinuado: ", row["descontinuado"],
            "| Código Barras: ", row["codigo_barras_produto"], "| Stock: ", row["quantidade_stock"],
            "| Subfamília: ", row["id_subfamilia"])

print_table()