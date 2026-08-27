import pandas as pd

from config import supabase

#Obter id família de uma sub família
def obter_id_familia(nome):

    response = (
        supabase
        .table("familia")
        .select("id_familia")
        .eq("nome", nome)
        .execute()
    )

    if response.data:
        return response.data[0]["id_familia"]

    return None

#Ajuda a definir o id das subfamílias
def obter_ordem(id_familia):

    response = (
        supabase
        .table("subfamilia")
        .select("ordem")
        .eq("familia_id_familia", id_familia)
        .order("ordem", desc=True)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["ordem"] + 1

    return 1

#Implementa famílias através do csv
def importar_familias():

    df = pd.read_csv(
        "data/familias.csv",
        sep=";"
    )

    for _, row in df.iterrows():

        existe = (
            supabase
            .table("familia")
            .select("id_familia")
            .eq("nome", row["nome"])
            .execute()
        )

        if existe.data:
            continue

        (
            supabase
            .table("familia")
            .insert({
                "nome": row["nome"],
                "descricao": "",
                "ordem": int(row["ordem"]),
                "pagina_inicial": int(row["pagina_inicial"]),
                "pagina_final": int(row["pagina_final"]),
                "cor": row["cor"]
            })
            .execute()
        )

#Implementa subfamílias através do csv, com recurso a famílias
def importar_subfamilias():

    df = pd.read_csv(
        "data/subfamilias.csv",
        sep=";"
    )

    id_atual = None
    ordem = 1

    for _, row in df.iterrows():

        id_familia = obter_id_familia(
            row["Familia"]
        )

        if id_familia is None:
            continue

        if id_familia != id_atual:

            id_atual = id_familia
            ordem = obter_ordem(id_familia)

        existe = (
            supabase
            .table("subfamilia")
            .select("id_subfamilia")
            .eq("nome", row["Subfamilia"])
            .eq(
                "familia_id_familia",
                id_familia
            )
            .execute()
        )

        if existe.data:
            continue

        (
            supabase
            .table("subfamilia")
            .insert({
                "nome": row["Subfamilia"],
                "descricao": "",
                "ordem": ordem,
                "pagina": int(
                    row["PaginaSubfamilia"]
                ),
                "familia_id_familia": id_familia
            })
            .execute()
        )

        ordem += 1