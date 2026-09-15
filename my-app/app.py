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

from datetime import date, timedelta

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
    obter_produto_por_referencia,
    obter_categorias
)

from services.email_service import (
    enviar_codigo_recuperacao,
    enviar_nota_encomenda
)

from services.carrinho_service import (
    obter_pedido,
    obter_preco_por_referencia,
    criar_pedido,
    criar_linha,
    somar_preco_linhas,
    obter_linha,
    atualizar_linha,
    get_linhas,
    apagar_linha
)

from services.admin_service import (
    obter_clientes,
    obter_cliente_admin,
    atualizar_cliente_admin,
    obter_produtos_admin,
    atualizar_produto_admin,
    obter_info,
    atualizar_estado_pedido_admin,
    obter_ivas,
    atualizar_ivas,
    criar_ivas,
    agrupar_itens_pedidos
)

from gerarPDF import(
    obter_info_pdf
)

from services.avaliacao_service import (
    comparar_avaliacao
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
            erro="User ou password incorretos."
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
            erro="User ou password incorretos."
        )

    # ========================================================
    # GUARDAR DADOS DO UTILIZADOR NA SESSION
    # ========================================================

    session["id_utilizador"] = (
        utilizador["id_utilizador"]
    )

    session["is_admin"] = (
        utilizador["is_admin"]
    )

    # ========================================================
    # REDIRECIONAR CONSOANTE O TIPO DE UTILIZADOR
    # ========================================================

    if session["is_admin"]:

        return redirect(
            url_for("confirm_admin")
        )

    return redirect(
        url_for("catalogo")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
def confirm_admin():

    # Primeiro verificar se existe sessão
    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # Depois verificar se é administrador
    if not session.get("is_admin", False):

        return redirect(
            url_for("login")
        )

    return render_template(
        "admin.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
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
        url_for("login")
    )


# ============================================================
# CATÁLOGO
# ============================================================

@app.route("/catalogo")
def catalogo():

    if "id_utilizador" not in session:
        return redirect(url_for("login"))

    pagina = request.args.get("pagina", 1, type=int)
    id_familia = request.args.get("familia", type=int)
    id_subfamilia = request.args.get("subfamilia", type=int)

    produtos, total_paginas = obter_produtos(
        pagina,
        id_familia=id_familia,
        id_subfamilia=id_subfamilia
    )

    categorias = obter_categorias()

    return render_template(
        "catalogo.html",
        produtos=produtos,
        pagina=pagina,
        total_paginas=total_paginas,
        categorias=categorias,
        id_familia=id_familia,
        id_subfamilia=id_subfamilia
    )


# ============================================================
# PERFIL
# ============================================================

@app.route("/perfil", methods=["GET", "POST"])
def perfil():

    # Verificar login ANTES de aceder à session
    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # Admin não usa o perfil normal
    if session.get("is_admin", False):

        return redirect(
            url_for("confirm_admin")
        )

    id_utilizador = session["id_utilizador"]

    cliente = obter_cliente(
        id_utilizador
    )

    if cliente is None:

        return redirect(
            url_for("logout")
        )

    # ========================================================
    # ALTERAR DADOS
    # ========================================================

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
                    erro=str(e)
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
            .eq(
                "id_utilizador",
                id_utilizador
            )
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

    sucesso = request.args.get(
        "sucesso"
    )

    erro = request.args.get(
        "erro"
    )

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
        url_for("confirmar_codigo")
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
            url_for("recuperar_password")
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
        url_for("login")
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

@app.route(
    "/carrinho",
    methods=["GET", "POST"]
)
def carrinho():

    # ========================================================
    # VERIFICAR LOGIN
    # ========================================================

    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # ========================================================
    # ADMIN NÃO TEM CARRINHO NORMAL
    # ========================================================

    if session.get("is_admin", False):

        return redirect(
            url_for("confirm_admin")
        )

    # ========================================================
    # OBTER CLIENTE
    # ========================================================

    cliente = obter_cliente(
        session["id_utilizador"]
    )

    if cliente is None:

        return redirect(
            url_for("logout")
        )

    # ========================================================
    # OBTER PEDIDO
    # ========================================================

    pedido = obter_pedido(
        cliente["id_cliente"]
    )

    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        if pedido is None:

            return render_template(
                "carrinho.html",
                linha=[],
                valor_total=0
            )

        linha, valor_total, observacoes = get_linhas(
            pedido
        )

        if linha is None:

            return render_template(
                "carrinho.html",
                linha=[],
                valor_total=0
            )

        return render_template(
            "carrinho.html",
            linha=linha,
            valor_total=valor_total,
            observacoes=observacoes
        )

    # ========================================================
    # POST - APAGAR LINHA
    # ========================================================

    id_linha = request.form[
        "id_linha"
    ]

    b = apagar_linha(
        id_linha
    )

    if b is not None:

        a = somar_preco_linhas(
            pedido
        )

        if a is None:

            print(
                "Erro ao recalcular o preço do pedido."
            )

    return redirect(
        url_for("carrinho")
    )


# ============================================================
# FINALIZAR PEDIDO
# ============================================================

@app.route(
    "/carrinhofinalizar",
    methods=["POST", "GET"]
)
def finalizar_compra():

    # ========================================================
    # VERIFICAR LOGIN
    # ========================================================

    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # Admin não finaliza pedidos desta forma
    if session.get("is_admin", False):

        return redirect(
            url_for("confirm_admin")
        )

    cliente = obter_cliente(
        session["id_utilizador"]
    )

    if cliente is None:

        return redirect(
            url_for("logout")
        )

    pedido = obter_pedido(
        cliente["id_cliente"]
    )

    if pedido is None:

        return redirect(
            url_for("carrinho")
        )

    observacoes = request.form["observacoes"]

    response = (
        supabase
        .table("pedido")
        .update({
            "estado": "finalizado",
            "observacoes": observacoes,
            "data_pedido": date.today().isoformat()
        })
        .eq(
            "id_pedido",
            pedido
        )
        .execute()
    )

    if not response.data:

        print(
            "Ocorreu um erro ao finalizar o pedido."
        )

        return redirect(
            url_for("carrinho")
        )
    
    pdf = obter_info_pdf(pedido)
    enviar_nota_encomenda(cliente["email"], pdf)


    return redirect(
        url_for("carrinho")
    )


# ============================================================
# ADICIONAR AO CARRINHO
# ============================================================

@app.route(
    "/produto/<int:referencia>/adicionar-carrinho",
    methods=["POST"]
)
def adicionar_carrinho(referencia):

    # ========================================================
    # VERIFICAR LOGIN
    # ========================================================

    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # Admin não adiciona produtos ao carrinho normal
    if session.get("is_admin", False):

        return redirect(
            url_for("confirm_admin")
        )

    # ========================================================
    # QUANTIDADE
    # ========================================================

    quantidade = int(
        request.form.get(
            "quantidade",
            1
        )
    )

    if quantidade < 1:

        quantidade = 1

    print(
        f"Produto: {referencia} | "
        f"Quantidade: {quantidade}"
    )

    # ========================================================
    # CLIENTE
    # ========================================================

    id_utilizador = session[
        "id_utilizador"
    ]

    cliente = obter_cliente(
        id_utilizador
    )

    if cliente is None:

        return redirect(
            url_for("logout")
        )

    # ========================================================
    # PEDIDO
    # ========================================================

    id_pedido = obter_pedido(
        cliente["id_cliente"]
    )

    print(
        id_pedido
    )

    # ========================================================
    # PREÇO
    # ========================================================

    preco = obter_preco_por_referencia(
        referencia
    )

    preco_qtd = (
        preco * quantidade
    )

    print(
        preco_qtd
    )

    # ========================================================
    # NÃO EXISTE PEDIDO
    # ========================================================

    if id_pedido is None:

        id_pedido = criar_pedido(
            cliente["id_cliente"]
        )

        print(
            id_pedido
        )

        linha = criar_linha(
            quantidade,
            preco,
            preco_qtd,
            id_pedido,
            referencia
        )

        if linha is not None:

            a = somar_preco_linhas(
                id_pedido
            )

            if a is None:

                print(
                    "Ocorreu um erro."
                )

        return redirect(
            url_for(
                "produto",
                referencia=referencia
            )
        )

    # ========================================================
    # VERIFICAR SE JÁ EXISTE LINHA
    # ========================================================

    id_linha = obter_linha(
        referencia,
        id_pedido
    )

    # ========================================================
    # CRIAR NOVA LINHA
    # ========================================================

    if id_linha is None:

        linha = criar_linha(
            quantidade,
            preco,
            preco_qtd,
            id_pedido,
            referencia
        )

        if linha is not None:

            a = somar_preco_linhas(
                id_pedido
            )

            if a is None:

                print(
                    "Ocorreu um erro."
                )

        return redirect(
            url_for(
                "produto",
                referencia=referencia
            )
        )

    # ========================================================
    # ATUALIZAR LINHA EXISTENTE
    # ========================================================

    linha_atualizar = atualizar_linha(
        quantidade,
        preco,
        id_linha
    )

    if linha_atualizar is None:

        print(
            "Erro ao atualizar linha."
        )

        return redirect(
            url_for(
                "produto",
                referencia=referencia
            )
        )

    pedido_atualizar = somar_preco_linhas(
        id_pedido
    )

    if pedido_atualizar is None:

        print(
            "Erro ao atualizar pedido."
        )

    return redirect(
        url_for(
            "produto",
            referencia=referencia
        )
    )

# ============================================================
# AVALIAÇÕES 
# ============================================================

@app.route("/produto/<int:referencia>/avaliar", methods=["POST"])
def avaliacoes(referencia):

    # ========================================================
    # VERIFICAR LOGIN
    # ========================================================

    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # Admin não adiciona produtos ao carrinho normal
    if session.get("is_admin", False):

        return redirect(
            url_for("confirm_admin")
        )

    classificacao = request.form["classificacao"]
    comentario = request.form["comentario"]
    id_utilizador = session[
        "id_utilizador"
    ]
    cliente = obter_cliente(
        id_utilizador
    )
    id_cliente = cliente["id_cliente"]

    id_avaliacao = comparar_avaliacao(id_cliente, referencia, classificacao, comentario)

    return redirect(
        url_for(
            "produto", referencia = referencia
        )
    )

# ============================================================
# ADMIN - PRODUTOS
# ============================================================

@app.route("/produtos_admin", methods=["GET", "POST"])
def produtos_admin():

    if "id_utilizador" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        return redirect(url_for("login"))

    if request.method == "POST":

        referencia = request.form["referencia"]

        preco_base = request.form["preco_base"]
        stock = request.form["stock"]

        descontinuado = (
            "descontinuado" in request.form
        )

        resposta = atualizar_produto_admin(
            referencia=referencia,
            preco_base=preco_base,
            stock=stock,
            descontinuado=descontinuado
        )

        if not resposta:
            return redirect(
                url_for(
                    "produtos_admin",
                    erro="Não foi possível atualizar o produto."
                )
            )

        return redirect(
            url_for(
                "produtos_admin",
                sucesso="Produto atualizado com sucesso."
            )
        )

    filtro = request.args.get("filtro", "").strip()

    produtos = obter_produtos_admin(filtro)

    return render_template(
        "produtos_admin.html",
        produtos=produtos,
        filtro=filtro
    )

# ============================================================
# ADMIN - CLIENTES
# ============================================================

@app.route(
    "/clientes_admin",
    methods=["GET", "POST"]
)
def clientes_admin():

    # ========================================================
    # VERIFICAR LOGIN
    # ========================================================

    if "id_utilizador" not in session:

        return redirect(
            url_for("login")
        )

    # ========================================================
    # VERIFICAR ADMIN
    # ========================================================

    if not session.get("is_admin", False):

        return redirect(
            url_for("login")
        )

    # ========================================================
    # POST - ALTERAR CLIENTE
    # ========================================================

    if request.method == "POST":

        id_cliente = request.form[
            "id_cliente"
        ]

        nome = request.form[
            "nome"
        ]

        nif = request.form[
            "nif"
        ]

        email = request.form[
            "email"
        ]

        ind = request.form[
            "ind"
        ]

        tel = request.form[
            "tel"
        ]

        postal = request.form[
            "postal"
        ]

        local = request.form[
            "local"
        ]

        morada = request.form[
            "morada"
        ]

        response = atualizar_cliente_admin(
            id_cliente,
            nome,
            nif,
            email,
            ind,
            tel,
            postal,
            local,
            morada
        )

        if not response:

            return redirect(
                url_for(
                    "clientes_admin",
                    erro="Não foi possível alterar os dados."
                )
            )

        return redirect(
            url_for(
                "clientes_admin",
                cliente=id_cliente,
                sucesso="Os dados foram alterados com sucesso!"
            )
        )

    # ========================================================
    # GET - PESQUISA
    # ========================================================

    filtro = request.args.get(
        "filtro",
        ""
    ).strip()

    clientes = obter_clientes(
        filtro
    )

    id_cliente = request.args.get(
        "cliente",
        type=int
    )

    cliente = None

    if id_cliente:

        cliente = obter_cliente_admin(
            id_cliente
        )

    sucesso = request.args.get(
        "sucesso"
    )

    erro = request.args.get(
        "erro"
    )

    return render_template(
        "clientes_admin.html",
        clientes=clientes,
        cliente=cliente,
        filtro=filtro,
        sucesso=sucesso,
        erro=erro
    )

# ============================================================
# ADMIN - PEDIDOS
# ============================================================

@app.route("/pedidos_admin", methods=["GET", "POST"])
def pedidos_admin():

    if "id_utilizador" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        return redirect(url_for("login"))

    if request.method == "POST":

        estado = request.form["estado"]
        id_pedido = request.form["id_pedido"]

        atualizar_estado_pedido_admin(
            id_pedido=id_pedido,
            estado=estado
        )

        return redirect(
            url_for(
                "pedidos_admin",
                cliente=request.args.get("cliente", ""),
                periodo=request.args.get("periodo", "sempre"),
                data_inicio=request.args.get("data_inicio", ""),
                data_fim=request.args.get("data_fim", ""),
                agrupar=request.args.get("agrupar", "")
            )
        )

    filtro_cliente = request.args.get("cliente", "").strip()
    periodo = request.args.get("periodo", "sempre")
    data_inicio_personalizada = request.args.get("data_inicio", "")
    data_fim_personalizada = request.args.get("data_fim", "")
    agrupar = request.args.get("agrupar") == "1"

    data_inicio = None
    data_fim = None

    hoje = date.today()

    periodos_rapidos = {
        "7": 7,
        "30": 30,
        "90": 90,
        "180": 180,
        "365": 365
    }

    if periodo in periodos_rapidos:

        data_inicio = (
            hoje - timedelta(days=periodos_rapidos[periodo])
        ).isoformat()

    elif periodo == "personalizado":

        data_inicio = data_inicio_personalizada or None
        data_fim = data_fim_personalizada or None

    info = obter_info(
        filtro_cliente=filtro_cliente or None,
        data_inicio=data_inicio,
        data_fim=data_fim
    )

    itens_agrupados = None

    if agrupar:
        itens_agrupados = agrupar_itens_pedidos(info)

    return render_template(
        "pedidos_admin.html",
        info=info,
        itens_agrupados=itens_agrupados,
        agrupar=agrupar,
        filtro_cliente=filtro_cliente,
        periodo=periodo,
        data_inicio=data_inicio_personalizada,
        data_fim=data_fim_personalizada
    )

# ============================================================
# ADMIN - CONFIGURAÇÕES (MENU)
# ============================================================

@app.route("/configuracoes_admin")
def configuracoes_admin():

    if "id_utilizador" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        return redirect(url_for("login"))

    return render_template(
        "configuracoes_admin.html"
    )


# ============================================================
# ADMIN - CONFIGURAÇÕES - IMPOSTOS (IVA)
# ============================================================

@app.route("/configuracoes_admin/impostos", methods=["GET", "POST"])
def configuracoes_impostos():

    if "id_utilizador" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        return redirect(url_for("login"))

    if request.method == "POST":

        ids = request.form.getlist("id_iva")

        ivas_existentes = []
        ivas_novos = []

        for id_iva in ids:

            percentagem = request.form.get(f"percentagem_{id_iva}")
            descricao = request.form.get(f"descricao_{id_iva}")

            # Linhas novas (criadas pelo botão "+") têm um id que
            # começa por "novo-" em vez de um id_iva real
            if id_iva.startswith("novo-"):

                if not percentagem:
                    continue

                ivas_novos.append({
                    "percentagem": percentagem,
                    "descricao": descricao
                })

            else:

                ivas_existentes.append({
                    "id_iva": id_iva,
                    "percentagem": percentagem,
                    "descricao": descricao
                })

        if ivas_existentes:
            atualizar_ivas(ivas_existentes)

        if ivas_novos:
            criar_ivas(ivas_novos)

        return redirect(
            url_for(
                "configuracoes_impostos",
                sucesso="Taxas de IVA atualizadas com sucesso."
            )
        )

    ivas = obter_ivas()

    sucesso = request.args.get("sucesso")

    return render_template(
        "configuracoes_impostos.html",
        ivas=ivas,
        sucesso=sucesso
    )



# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )