from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for
)

import time
import secrets

from config import supabase, ph

from services.auth_service import autenticar

from services.clientes_service import (
    registar_cliente_web,
    obter_cliente,
    obter_cliente_por_email,
    validar_password,
    validar_nome,
    validar_nif, 
    validar_indicativo,
    validar_telefone,
    validar_email,
    validar_codigo_postal,
    validar_localizacao,
    validar_morada
)

from services.produto_service import (
    obter_produtos,
    obter_produto_por_referencia
)

from services.email_service import (
    enviar_codigo_recuperacao
)

from services.carrinho_service import (
    obter_pedido,
    obter_preco_por_referencia,
    criar_pedido,
    criar_linha,
    somar_preco_linhas,
    obter_linha,
    atualizar_linha,
    get_linhas
)

app = Flask(__name__)
app.secret_key = "ALTERAR_PARA_UMA_CHAVE_SECRETA"


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template(
        "index.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template(
            "login.html"
        )

    username = request.form["username"].strip()
    password = request.form["password"]

    response = (
        supabase
        .table("utilizador")
        .select("*")
        .eq(
            "username",
            username
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return render_template(
            "login.html",
            erro="NIF ou password incorretos."
        )

    utilizador = response.data[0]

    try:
        password_correta = ph.verify(
            utilizador["password"],
            password
        )
    except Exception:
        password_correta = False

    if not password_correta:
        return render_template(
            "login.html",
            erro="NIF ou password incorretos."
        )

    session["id_utilizador"] = (
        utilizador["id_utilizador"]
    )

    session["is_admin"] = (
        utilizador["is_admin"]
    )

    return redirect(
        "/catalogo"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/"
    )


# ============================================================
# REGISTO
# ============================================================

@app.route("/registar", methods=["GET", "POST"])
def registar():

    if request.method == "GET":
        return render_template(
            "registar.html"
        )

    try:

        registar_cliente_web(
            request.form
        )

    except ValueError as e:

        return render_template(
            "registar.html",
            erro=str(e)
        )

    except Exception as e:

        print(
            "Erro no registo:",
            e
        )

        return render_template(
            "registar.html",
            erro="Ocorreu um erro ao criar a conta."
        )

    return redirect(
        "/login"
    )


# ============================================================
# CATÁLOGO
# ============================================================

@app.route("/catalogo")
def catalogo():

    if "id_utilizador" not in session:
        return redirect("/login")

    pagina = request.args.get(
        "pagina",
        1,
        type=int
    )

    produtos, total_paginas = obter_produtos(pagina)

    return render_template(
        "catalogo.html",
        produtos=produtos,
        pagina=pagina,
        total_paginas=total_paginas
    )

# ============================================================
# PERFIL
# ============================================================



@app.route("/perfil", methods=["GET", "POST"])
def perfil():

    if "id_utilizador" not in session:
        return redirect("/login")

    id_utilizador = session["id_utilizador"]

    cliente = obter_cliente(id_utilizador)

    if cliente is None:
        return redirect("/logout")

    if request.method == "POST":

        nome = request.form["nome"]
        nif = request.form["nif"]
        email = request.form["email"]
        ind = request.form["ind"]
        tel = request.form["tel"]
        postal = request.form["postal"]
        local = request.form["local"]
        morada = request.form["morada"]

        try:
            validar_nome(nome)
            validar_nif(nif)
            validar_email(email)
            validar_telefone(tel, ind)
            validar_codigo_postal(postal)
            validar_localizacao(local)
            validar_morada(morada)

        except Exception as e:
            return redirect(
                            url_for(
                                "perfil",
                                erro=e
                            )
                        )

        response = (
            supabase
            .table("cliente")
            .update({
                "nif": nif,
                "nome": nome,
                "morada": morada,
                "email": email,
                "telefone": tel,
                "codigo_postal": postal,
                "localizacao": local,
                "indicativo": ind
            })
            .eq("id_utilizador", id_utilizador)
            .execute()
        )

        if not response.data:
            return redirect(
                url_for(
                    "perfil",
                    erro="Não foi possível alterar os dados."
                )
            )

        return redirect(
            url_for(
                "perfil",
                sucesso="Os dados foram alterados com sucesso!"
            )
        )

    sucesso = request.args.get("sucesso")
    erro = request.args.get("erro")

    return render_template(
        "perfil.html",
        cliente=cliente,
        sucesso=sucesso,
        erro=erro
    )




# ============================================================
# RECUPERAR PASSWORD
# ============================================================

@app.route(
    "/recuperar-password",
    methods=["GET", "POST"]
)
def recuperar_password():

    if request.method == "GET":

        return render_template(
            "recuperar_password.html"
        )

    email = request.form[
        "email"
    ].strip().lower()

    cliente = obter_cliente_por_email(
        email
    )

    if cliente is None:

        return render_template(
            "recuperar_password.html",
            erro="Não foi encontrada nenhuma conta com esse email."
        )

    codigo = str(
        secrets.randbelow(900000) + 100000
    )

    session[
        "recuperacao_codigo"
    ] = codigo

    session[
        "recuperacao_id_utilizador"
    ] = cliente[
        "id_utilizador"
    ]

    session[
        "recuperacao_email"
    ] = email

    session[
        "recuperacao_expira"
    ] = (
        time.time() + 300
    )

    try:

        enviar_codigo_recuperacao(
            email,
            codigo
        )

    except Exception as e:

        print(
            "Erro ao enviar email:",
            e
        )

        limpar_recuperacao()

        return render_template(
            "recuperar_password.html",
            erro="Não foi possível enviar o email."
        )

    return redirect(
        "/confirmar-codigo"
    )


# ============================================================
# CONFIRMAR CÓDIGO
# ============================================================

@app.route(
    "/confirmar-codigo",
    methods=["GET", "POST"]
)
def confirmar_codigo():

    if (
        "recuperacao_codigo"
        not in session
    ):
        return redirect(
            "/recuperar-password"
        )

    if request.method == "GET":
        return render_template(
            "confirmar_codigo.html"
        )

    codigo = request.form[
        "codigo"
    ].strip()

    password = request.form[
        "password"
    ]

    password_confirmacao = request.form[
        "password_confirmacao"
    ]

    if time.time() > session[
        "recuperacao_expira"
    ]:

        limpar_recuperacao()

        return render_template(
            "confirmar_codigo.html",
            erro="O código expirou."
        )

    if codigo != session[
        "recuperacao_codigo"
    ]:

        return render_template(
            "confirmar_codigo.html",
            erro="Código inválido."
        )

    if password != password_confirmacao:

        return render_template(
            "confirmar_codigo.html",
            erro="As passwords não coincidem."
        )

    try:

        validar_password(
            password
        )

    except ValueError as e:

        return render_template(
            "confirmar_codigo.html",
            erro=str(e)
        )

    id_utilizador = session[
        "recuperacao_id_utilizador"
    ]

    password_hash = ph.hash(
        password
    )

    response = (
        supabase
        .table("utilizador")
        .update({
            "password": password_hash
        })
        .eq(
            "id_utilizador",
            id_utilizador
        )
        .execute()
    )

    if not response.data:

        return render_template(
            "confirmar_codigo.html",
            erro="Não foi possível alterar a password."
        )

    limpar_recuperacao()

    return redirect(
        "/login"
    )


# ============================================================
# LIMPAR RECUPERAÇÃO
# ============================================================

def limpar_recuperacao():

    session.pop(
        "recuperacao_codigo",
        None
    )

    session.pop(
        "recuperacao_id_utilizador",
        None
    )

    session.pop(
        "recuperacao_email",
        None
    )

    session.pop(
        "recuperacao_expira",
        None
    )


# ============================================================
# PRODUTO
# ============================================================

#Página do produto
@app.route("/produto/<int:referencia>")
def produto(referencia):

    produto = obter_produto_por_referencia(
        referencia
    )

    if produto is None:
        return "Produto não encontrado", 404

    return render_template(
        "produto.html",
        produto=produto
    )


# ============================================================
# CARRINHO
# ============================================================

#Página do carrinho

@app.route("/carrinho")
def carrinho():

    if "id_utilizador" not in session:
        return redirect("/login")

    cliente = obter_cliente(session["id_utilizador"])
    pedido = obter_pedido(cliente["id_cliente"])
    linha, valor_total = get_linhas(pedido)

    if linha is None:
        return "Linha não encontrada"

    return render_template(
        "carrinho.html",
        linha=linha,
        valor_total=valor_total
    )




@app.route(
    "/produto/<int:referencia>/adicionar-carrinho",
    methods=["POST"]
)
def adicionar_carrinho(referencia):

    quantidade = int(
        request.form.get("quantidade", 1)
    )

    if quantidade < 1:
        quantidade = 1

    print(
        f"Produto: {referencia} | Quantidade: {quantidade}"
    )

    if "id_utilizador" not in session:
        return redirect("/login")

    id_utilizador = session["id_utilizador"]

    cliente = obter_cliente(id_utilizador)

    if cliente is None:
        return redirect("/logout")

    id_pedido = obter_pedido(cliente["id_cliente"])
    print(id_pedido)


    preco = obter_preco_por_referencia(referencia) 
    preco_qtd = preco*quantidade
    print(preco_qtd)

    if id_pedido is None:
        id_pedido = criar_pedido(cliente["id_cliente"])
        print(id_pedido)

        linha = criar_linha(quantidade, preco, preco_qtd, id_pedido, referencia)

        if linha is not None:
            a = somar_preco_linhas(id_pedido)
            if a is None:
                print("ocorreu um erro")

        return redirect(
                url_for(
                    "produto",
                    referencia=referencia
                )
            )
    
    id_linha = obter_linha(referencia, id_pedido)

    if id_linha is None:

        linha = criar_linha(quantidade, preco, preco_qtd, id_pedido, referencia)
        
        if linha is not None:
            a = somar_preco_linhas(id_pedido)
            if a is None:
                print("ocorreu um erro")


        return redirect(
                url_for(
                    "produto",
                    referencia=referencia
                )
            )

    else:
        linha_atualizar = atualizar_linha(quantidade, preco, id_linha)
        if linha_atualizar is None:
            print("erro ao atualizar linha")
            return redirect(
                url_for(
                    "produto",
                    referencia=referencia
                )
            )

        pedido_atualizar = somar_preco_linhas(id_pedido)
        if linha_atualizar is None:
            print("erro ao atualizar pedido")
                

        return redirect(
            url_for(
                "produto",
                referencia=referencia
            )
        )




# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )