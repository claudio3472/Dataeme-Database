from config import supabase, ph

#Verifica se a password e username correspondem á base de dados no login
def autenticar(username, password):

    response = (
        supabase
        .table("utilizador")
        .select("*")
        .eq("username", username)
        .execute()
    )

    if not response.data:
        return None

    utilizador = response.data[0]

    try:

        ph.verify(
            utilizador["password"],
            password
        )

        return utilizador

    except Exception as e:

        print("Erro:")
        print(e)

        return None