import re
from config import supabase, ph

""" MUDAR PARA USAR O PRIMEIRO DIGITO DO NIF PARA ESCOLHER SE É EMPRESA OU NÃO
E AJUSTAR O NOME CONSOANTE. 
SE FOR EMPRESA TEM DE TER PESSOA DE CONTACTO """

def validar_nome(nome):
    nome = nome.strip()

    if len(nome.split()) < 2:
        raise ValueError(
            "O nome deve conter pelo menos nome e apelido."
        )

    if any(char.isdigit() for char in nome):
        raise ValueError(
            "O nome não pode conter números."
        )

    if not re.match(
        r"^[A-Za-zÀ-ÿ\s\-]+$",
        nome
    ):
        raise ValueError(
            "O nome contém caracteres inválidos."
        )
    

def validar_nif(nif):
    if not nif.isdigit() or len(nif) != 9:
        raise ValueError(
            "O NIF deve conter exatamente 9 dígitos."
        )


def validar_indicativo(indicativo):
    if not re.match(
        r"^\+\d{1,4}$",
        indicativo
    ):
        raise ValueError(
            "Indicativo internacional inválido."
        )

def validar_telefone(telefone, indicativo):
    if not telefone.isdigit():
        raise ValueError(
            "O telefone só pode conter dígitos."
        )

    if indicativo == "+351":
        if len(telefone) != 9:
            raise ValueError(
                "O telefone português deve conter exatamente 9 dígitos."
            )

        prefixos_validos = (
            "91", "92", "93", "96",
            "21", "22",
            "231", "232", "233", "234", "235", "236", "238", "239",
            "241", "242", "243", "244", "245", "249",
            "251", "252", "253", "254", "255", "256", "258", "259",
            "261", "262", "263", "265", "266", "268", "269",
            "271", "272", "273", "274", "275", "276", "277", "278",
            "281", "282", "283", "284", "285", "286", "289",
            "291", "292", "295", "296"
        )

        if not telefone.startswith(prefixos_validos):
            raise ValueError(
                "O telefone deve ser um número português válido."
            )

    else:
        if len(telefone) < 6 or len(telefone) > 15:
            raise ValueError(
                "Número de telefone internacional inválido."
            )

    
def validar_email(email):
    if not re.match(
        r"^[^@]+@[^@]+\.[^@]+$",
        email
    ):
        raise ValueError(
            "Email inválido."
        )


def validar_codigo_postal(codigo_postal):
    if not re.match(
        r"^\d{4}-\d{3}$",
        codigo_postal
    ):
        raise ValueError(
            "Código postal inválido. Exemplo: 0000-000."
        )

"""FUTURAMENTE USAR WEB SCRAPPER PARA ATRAVES DO CODIGO POSTAL PREENCHER A LOCALIZACAO"""
def validar_localizacao(localizacao):
    localizacao = localizacao.strip()

    if len(localizacao) < 3:
        raise ValueError(
            "A localização deve conter pelo menos 3 caracteres."
        )

    if any(char.isdigit() for char in localizacao):
        raise ValueError(
            "A localização não pode conter números."
        )


"""Meter campo à parte para o numero/andar"""
def validar_morada(morada):
    morada = morada.strip()

    prefixos_validos = [
        "Alameda", "AL",
        "Avenida", "AV",
        "Azinhaga", "AZ",
        "Bairro", "BR",
        "Beco", "BC",
        "Calçada", "CC",
        "Calçadinha", "CCNH",
        "Caminho", "CAM",
        "Casa", "CS",
        "Conjunto", "CJ",
        "Escadas", "ESC",
        "Escadinhas", "ESCNH",
        "Estrada", "ESTR",
        "Jardim", "JD",
        "Largo", "LG",
        "Loteamento", "LOT",
        "Lugar", "LUG",
        "Parque", "PQ",
        "Pátio", "PAT",
        "Praça", "PC",
        "Praceta", "PCT",
        "Prolongamento", "PRL",
        "Quadra", "QD",
        "Quinta", "QTA",
        "Rotunda", "ROT",
        "Rua", "R",
        "Transversal", "TRANSV",
        "Travessa", "TV",
        "Urbanização", "URB",
        "Vila", "VL",
        "Vale", "V",
        "Zona", "ZN"
    ]

    prefixo_encontrado = None

    for prefixo in prefixos_validos:
        if morada.startswith(prefixo + " "):
            prefixo_encontrado = prefixo
            break

    if prefixo_encontrado is None:
        raise ValueError(
            "A morada deve começar por Rua, Avenida, Travessa, Praceta, Largo, Alameda, etc."
        )

    resto = morada[len(prefixo_encontrado):].strip()

    if len(resto) < 2:
        raise ValueError(
            "A morada deve conter um nome após o tipo de via."
        )


def validar_password(password):
    if len(password) < 8:
        raise ValueError(
            "A password deve ter pelo menos 8 caracteres."
        )

    if not any(c.isupper() for c in password):
        raise ValueError(
            "A password deve conter pelo menos uma letra maiúscula."
        )

    if not any(c.islower() for c in password):
        raise ValueError(
            "A password deve conter pelo menos uma letra minúscula."
        )

    if not any(c.isdigit() for c in password):
        raise ValueError(
            "A password deve conter pelo menos um número."
        )


def verificar_duplicados(nif, email):
    nif_existe = (
        supabase
        .table("cliente")
        .select("nif")
        .eq("nif", nif)
        .execute()
    )

    if nif_existe.data:
        raise ValueError(
            "Já existe um cliente com esse NIF."
        )

    email_existe = (
        supabase
        .table("cliente")
        .select("email")
        .eq("email", email)
        .execute()
    )

    if email_existe.data:
        raise ValueError(
            "Já existe um cliente com esse email."
        )

    utilizador_existe = (
        supabase
        .table("utilizador")
        .select("username")
        .eq("username", nif)
        .execute()
    )

    if utilizador_existe.data:
        raise ValueError(
            "Já existe um utilizador com esse NIF."
        )


def registar_cliente_web(form):
    nome = form["nome"].strip()
    nif = form["nif"].strip()
    morada = form["morada"].strip()
    email = form["email"].strip().lower()
    indicativo = form["indicativo"].strip()
    telefone = form["telefone"].strip()
    codigo_postal = form["codigo_postal"].strip()
    localizacao = form["localizacao"].strip()
    password = form["password"]

    validar_nome(nome)
    validar_nif(nif)
    validar_indicativo(indicativo)
    validar_telefone(
        telefone,
        indicativo
    )
    validar_email(email)
    validar_codigo_postal(codigo_postal)
    validar_localizacao(localizacao)
    validar_morada(morada)
    validar_password(password)

    verificar_duplicados(
        nif,
        email
    )

    password_hash = ph.hash(password)

    utilizador = {
        "username": nif,
        "password": password_hash,
        "is_admin": False
    }

    response = (
        supabase
        .table("utilizador")
        .insert(utilizador)
        .execute()
    )

    id_utilizador = response.data[0]["id_utilizador"]

    cliente = {
        "nif": nif,
        "nome": nome,
        "morada": morada,
        "email": email,
        "telefone": int(telefone),
        "codigo_postal": codigo_postal,
        "localizacao": localizacao,
        "indicativo": indicativo,
        "id_utilizador": id_utilizador
    }

    (
        supabase
        .table("cliente")
        .insert(cliente)
        .execute()
    )

    return True


def obter_cliente(id_utilizador):
    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq(
            "id_utilizador",
            id_utilizador
        )
        .execute()
    )

    if not response.data:
        return None

    cliente = response.data[0]

    return {
        "nif": cliente["nif"],
        "nome": cliente["nome"],
        "morada": cliente["morada"],
        "email": cliente["email"],
        "tel": cliente["telefone"],
        "postal": cliente["codigo_postal"],
        "local": cliente["localizacao"],
        "indicativo": cliente["indicativo"]
    }

def obter_cliente_por_email(email):

    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq(
            "email",
            email
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None