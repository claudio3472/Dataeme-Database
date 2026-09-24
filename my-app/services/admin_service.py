import difflib
import re
import unicodedata
import pandas as pd

from deep_translator import GoogleTranslator
import webcolors

from config import supabase


# ============================================================
# TRADUÇÃO DE CORES + CONVERSÃO PARA HEX 
# ============================================================

CORES_PT_PARA_EN = {
    "branco": "white",
    "preto": "black",
    "cinza": "gray",
    "cinzento": "gray",
    "vermelho": "red",
    "verde": "green",
    "azul": "blue",
    "amarelo": "yellow",
    "laranja": "orange",
    "roxo": "purple",
    "violeta": "violet",
    "rosa": "pink",
    "rosa choque": "deeppink",
    "rosa claro": "lightpink",
    "castanho": "brown",
    "marrom": "brown",
    "dourado": "gold",
    "prateado": "silver",
    "bege": "beige",
    "turquesa": "turquoise",
    "bordô": "maroon",
    "bordeaux": "maroon",
    "grená": "maroon",
    "salmão": "salmon",
    "coral": "coral",
    "creme": "cornsilk",
    "azul claro": "lightblue",
    "azul escuro": "darkblue",
    "azul marinho": "navy",
    "verde claro": "lightgreen",
    "verde escuro": "darkgreen",
    "verde água": "aquamarine",
    "cinza claro": "lightgray",
    "cinza escuro": "darkgray",
    "lilás": "plum",
    "lavanda": "lavender",
    "vinho": "maroon",
    "mostarda": "darkkhaki",
    "caqui": "khaki",
    "prata": "silver",
    "ouro": "gold"
}


def traduzir_para_ingles(texto):
    """
    Traduz um texto (nome de uma cor) para inglês.
    Se a tradução falhar por qualquer motivo (ex: sem internet),
    devolve o texto original para não bloquear a criação da cor.
    """

    texto = (texto or "").strip()

    if not texto:
        return texto

    try:

        traduzido = (
            GoogleTranslator(source="auto", target="en")
            .translate(texto)
        )

        return (traduzido or texto).strip()

    except Exception as e:

        print("Aviso: não foi possível traduzir a cor:", e)

        return texto


def _nome_cor_para_hex(nome_ingles):
    """
    Converte um nome de cor em inglês no código hex mais próximo,
    usando a lista de cores CSS3 da biblioteca webcolors.
    """

    nome_normalizado = (
        unicodedata.normalize("NFKD", nome_ingles)
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )

    nome_sem_espacos = nome_normalizado.replace(" ", "").replace("-", "")

    # --------------------------------------------------------
    # 1) Correspondência exata (com e sem espaços/hífens)
    # --------------------------------------------------------

    for tentativa in (nome_normalizado, nome_sem_espacos):

        try:
            return webcolors.name_to_hex(tentativa, spec="css3")

        except ValueError:
            continue

    # --------------------------------------------------------
    # 2) Cor CSS3 mais parecida (ex: "brick red" -> "darkred")
    # --------------------------------------------------------

    try:
        nomes_css3 = list(webcolors.names(spec="css3"))

    except AttributeError:
        # Compatibilidade com versões mais antigas do webcolors
        nomes_css3 = list(webcolors.CSS3_NAMES_TO_HEX.keys())

    parecidas = difflib.get_close_matches(
        nome_sem_espacos,
        nomes_css3,
        n=1,
        cutoff=0.6
    )

    if parecidas:
        return webcolors.name_to_hex(parecidas[0], spec="css3")

    # --------------------------------------------------------
    # 3) Sem correspondência - cinzento neutro em vez de falhar
    # --------------------------------------------------------

    return "#808080"


def traduzir_e_converter_cor(nome_cor_original):
    """
    Recebe o nome de uma cor em qualquer idioma e devolve o
    código hex correspondente. Primeiro tenta o dicionário local
    de cores comuns em português (rápido e funciona sem internet);
    só recorre à tradução online para nomes que não estejam lá.
    """

    nome_limpo = (
        unicodedata.normalize("NFKD", (nome_cor_original or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )

    # Repetir a normalização sobre as chaves do dicionário para
    # que "Rosa Claro", "rosa claro", etc. correspondam sempre.
    for nome_pt, nome_en in CORES_PT_PARA_EN.items():

        nome_pt_normalizado = (
            unicodedata.normalize("NFKD", nome_pt)
            .encode("ascii", "ignore")
            .decode("ascii")
        )

        if nome_limpo == nome_pt_normalizado:
            return _nome_cor_para_hex(nome_en)

    nome_ingles = traduzir_para_ingles(nome_cor_original)

    return _nome_cor_para_hex(nome_ingles)


def obter_ivas():
    """
    Obtém todas as taxas de IVA existentes.
    """

    response = (
        supabase
        .table("iva")
        .select("*")
        .order("percentagem")   
        .execute()
    )

    return response.data or []


def atualizar_ivas(ivas):
    """
    Atualiza taxas de IVA existentes e cria novas taxas.

    'ivas' é uma lista de dicionários:
    [
        {"id_iva": 1, "percentagem": 23, "descricao": "Taxa normal"},
        {"id_iva": "novo-1", "percentagem": 13, "descricao": "Taxa intermédia"}
    ]

    IDs no formato "novo-X" representam taxas criadas no formulário
    e ainda sem um ID atribuído pela base de dados.
    """

    resultado = []

    for iva in ivas:
        id_iva = iva.get("id_iva")
        percentagem = iva.get("percentagem")
        descricao = iva.get("descricao")

        if percentagem is None or percentagem == "":
            continue

        if isinstance(id_iva, str) and id_iva.startswith("novo-"):
            response = (
                supabase
                .table("iva")
                .insert({
                    "percentagem": percentagem,
                    "descricao": descricao
                })
                .execute()
            )
        else:
            try:
                id_iva = int(id_iva)
            except (TypeError, ValueError):
                continue

            response = (
                supabase
                .table("iva")
                .update({
                    "percentagem": percentagem,
                    "descricao": descricao
                })
                .eq("id_iva", id_iva)
                .execute()
            )

        if response.data:
            resultado.append(response.data[0])

    return resultado

def criar_ivas(ivas):
    """
    Cria novas taxas de IVA.

    Cada item de 'ivas' é um dicionário:
    {"percentagem": ..., "descricao": ...}

    Linhas sem percentagem são ignoradas (linha deixada vazia pelo utilizador).
    """

    criados = []

    for iva in ivas:

        percentagem = iva.get("percentagem")

        if not percentagem:
            continue

        response = (
            supabase
            .table("iva")
            .insert({
                "percentagem": percentagem,
                "descricao": iva.get("descricao")
            })
            .execute()
        )

        if response.data:
            criados.append(response.data[0])

    return criados


def agrupar_itens_pedidos(info):
    """
    Agrupa os itens de vários pedidos por produto,
    somando a quantidade total comprada e o valor total.
    """

    grupos = {}

    for item in info:

        chave = item["referencia"]

        if chave not in grupos:

            grupos[chave] = {
                "referencia": item["referencia"],
                "nome_produto": item["nome_produto"],
                "cor": item["cor"],
                "codigo": item["codigo"],
                "quantidade_total": 0,
                "valor_total": 0,
                "num_pedidos": set()
            }

        grupos[chave]["quantidade_total"] += item["quantidade"]
        grupos[chave]["valor_total"] += item["preco_total"]
        grupos[chave]["num_pedidos"].add(item["id_pedido"])

    resultado = []

    for grupo in grupos.values():

        grupo["num_pedidos"] = len(grupo["num_pedidos"])
        resultado.append(grupo)

    return sorted(
        resultado,
        key=lambda g: g["quantidade_total"],
        reverse=True
    )


def obter_produtos_admin(filtro=None, id_familia=None, id_subfamilia=None):
    """
    Obtém os modelos de produtos e todas as suas variantes (cores).
    Ordenado pela ordem da família (e nome do modelo como desempate).
    """

    # --------------------------------------------------------
    # SUBFAMÍLIAS E FAMÍLIAS
    # --------------------------------------------------------

    subfamilias_response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia, nome, familia_id_familia")
        .execute()
    )

    subfamilias = {
        s["id_subfamilia"]: s
        for s in (subfamilias_response.data or [])
    }

    familias_response = (
        supabase
        .table("familia")
        .select("id_familia, nome, ordem")
        .execute()
    )

    familias = {
        f["id_familia"]: f
        for f in (familias_response.data or [])
    }

    # --------------------------------------------------------
    # RESTRINGIR SUBFAMÍLIAS RELEVANTES ANTES DE IR À BASE DE DADOS
    # --------------------------------------------------------

    ids_subfamilia_validas = None

    if id_subfamilia:
        ids_subfamilia_validas = [id_subfamilia]

    elif id_familia:
        ids_subfamilia_validas = [
            s["id_subfamilia"]
            for s in subfamilias.values()
            if s["familia_id_familia"] == id_familia
        ]

        if not ids_subfamilia_validas:
            return []

    # --------------------------------------------------------
    # MODELOS
    # --------------------------------------------------------

    modelos_query = (
        supabase
        .table("produtos_modelo")
        .select(
            "id_modelo, "
            "nome_catalogo, "
            "descricao_catalogo, "
            "descricao_detalhada, "
            "id_subfamilia"
        )
    )

    if filtro:
        modelos_query = modelos_query.ilike(
            "nome_catalogo",
            f"%{filtro}%"
        )

    if ids_subfamilia_validas is not None:
        modelos_query = modelos_query.in_(
            "id_subfamilia",
            ids_subfamilia_validas
        )

    modelos_response = modelos_query.execute()

    if not modelos_response.data:
        return []

    modelos = modelos_response.data

    # --------------------------------------------------------
    # UMA ÚNICA QUERY PARA TODAS AS VARIANTES DE TODOS OS MODELOS
    # --------------------------------------------------------

    ids_modelo = [
        modelo["id_modelo"] for modelo in modelos
    ]

    produtos_response = (
        supabase
        .table("produtos")
        .select(
            "referencia",
            "id_modelo",
            "id_cor",
            "preco_base",
            "descontinuado",
            "quantidade_stock",
            "codigo_barras_produto",
            "id_iva"
        )
        .in_("id_modelo", ids_modelo)
        .order("referencia")
        .execute()
    )

    # --------------------------------------------------------
    # IVAs — indexados pelo id_iva real (não pela posição na lista)
    # --------------------------------------------------------

    iva_response = (
        supabase
        .table("iva")
        .select("id_iva, percentagem")
        .order("percentagem")
        .execute()
    )

    ivas = iva_response.data or []

    ivas_por_id = {
        iva["id_iva"]: iva["percentagem"]
        for iva in ivas
    }

    # Lista de percentagens disponíveis, para preencher
    # dropdowns/selects no template
    iva_lista = [iva["percentagem"] for iva in ivas]

    produtos_todos = produtos_response.data or []

    # Agrupar variantes por modelo (em memória, O(n))
    produtos_por_modelo = {}

    for produto in produtos_todos:
        produtos_por_modelo.setdefault(
            produto["id_modelo"],
            []
        ).append(produto)

    # --------------------------------------------------------
    # UMA ÚNICA QUERY PARA TODAS AS CORES DE TODOS OS PRODUTOS
    # --------------------------------------------------------

    cores_ids = list({
        p["id_cor"]
        for p in produtos_todos
        if p.get("id_cor") is not None
    })

    cores = {}

    if cores_ids:
        cores_response = (
            supabase
            .table("cores_produto")
            .select(
                "id_cor, nome_cor, codigo_cor, imagem_url"
            )
            .in_("id_cor", cores_ids)
            .execute()
        )

        cores = {
            c["id_cor"]: c
            for c in (cores_response.data or [])
        }

    # ========================================================
    # MONTAR RESULTADO
    # ========================================================

    resultado = []

    for modelo in modelos:

        id_modelo = modelo["id_modelo"]

        produtos = produtos_por_modelo.get(id_modelo, [])

        variantes = []

        for produto in produtos:

            cor = cores.get(produto["id_cor"])

            variantes.append({
                "referencia": produto["referencia"],
                "id_cor": produto["id_cor"],
                "cor": cor["nome_cor"] if cor else "",
                "codigo_cor": cor["codigo_cor"] if cor else "",
                "imagem_url": cor["imagem_url"] if cor else "",
                "preco_base": produto["preco_base"],
                "descontinuado": produto["descontinuado"],
                "stock": produto["quantidade_stock"],
                "iva": ivas_por_id.get(produto["id_iva"]),
                "iva_lista": iva_lista,
                "codigo_barras": produto.get("codigo_barras", "")
            })

        subfamilia = subfamilias.get(modelo["id_subfamilia"])

        familia = None

        if subfamilia:
            familia = familias.get(
                subfamilia["familia_id_familia"]
            )

        resultado.append({
            "id_modelo": modelo["id_modelo"],
            "nome": modelo["nome_catalogo"],
            "descricao": modelo["descricao_catalogo"],
            "descricao_detalhada": modelo["descricao_detalhada"],
            "familia": familia["nome"] if familia else "",
            "id_familia": familia["id_familia"] if familia else None,
            "ordem_familia": familia["ordem"] if familia else None,
            "subfamilia": subfamilia["nome"] if subfamilia else "",
            "id_subfamilia": subfamilia["id_subfamilia"] if subfamilia else None,
            "variantes": variantes
        })

    resultado.sort(
        key=lambda item: (
            item["ordem_familia"] if item["ordem_familia"] is not None else float("inf"),
            item["nome"]
        )
    )

    return resultado


# ============================================================
# NOVO PRODUTO - LISTAS PARA OS DROPDOWNS DO POP-UP
# ============================================================

def obter_familias():
    """
    Obtém todas as famílias (para o dropdown do pop-up "Novo produto").
    """

    response = (
        supabase
        .table("familia")
        .select("id_familia, nome, cor, descricao")
        .order("nome")
        .execute()
    )

    return response.data or []


def obter_subfamilias(id_familia=None):
    """
    Obtém as subfamílias. Se 'id_familia' for indicado, devolve
    apenas as subfamílias dessa família (usado pelo dropdown
    dependente do pop-up "Novo produto").
    """

    query = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia, nome, familia_id_familia")
        .order("nome")
    )

    if id_familia:
        query = query.eq("familia_id_familia", id_familia)

    response = query.execute()

    return response.data or []


def obter_modelos(id_subfamilia=None):
    """
    Obtém os modelos de produto. Se 'id_subfamilia' for indicado,
    devolve apenas os modelos dessa subfamília (dropdown dependente
    do pop-up "Novo produto").
    """

    query = (
        supabase
        .table("produtos_modelo")
        .select("id_modelo, nome_catalogo, id_subfamilia")
        .order("nome_catalogo")
    )

    if id_subfamilia:
        query = query.eq("id_subfamilia", id_subfamilia)

    response = query.execute()

    return response.data or []


def obter_cores():
    """
    Obtém todas as cores já existentes (para o dropdown do pop-up
    "Novo produto").
    """

    response = (
        supabase
        .table("cores_produto")
        .select("id_cor, nome_cor, codigo_cor")
        .order("nome_cor")
        .execute()
    )

    return response.data or []


# ============================================================
# NOVO PRODUTO - CRIAÇÃO DE FAMÍLIA / SUBFAMÍLIA / MODELO / COR
# ============================================================

def criar_familia(nome, cor, ordem, pagina_inicial, pagina_final, descricao=None):
    """
    Cria uma nova família. 'cor' é o código/etiqueta de cor da
    própria família (usado no catálogo), não a cor de uma variante.
    """

    response = (
        supabase
        .table("familia")
        .insert({
            "nome": nome,
            "descricao": descricao,
            "ordem": ordem,
            "pagina_inicial": pagina_inicial,
            "pagina_final": pagina_final,
            "cor": cor
        })
        .execute()
    )

    return response.data[0] if response.data else None


def criar_subfamilia(nome, id_familia, ordem, pagina, descricao=None):
    """
    Cria uma nova subfamília dentro de uma família existente.
    """

    response = (
        supabase
        .table("subfamilia")
        .insert({
            "nome": nome,
            "descricao": descricao,
            "ordem": ordem,
            "pagina": pagina,
            "familia_id_familia": id_familia
        })
        .execute()
    )

    return response.data[0] if response.data else None


def criar_modelo(nome_catalogo, id_subfamilia, descricao_catalogo=None, descricao_detalhada=None):
    """
    Cria um novo modelo de produto dentro de uma subfamília existente.
    """

    response = (
        supabase
        .table("produtos_modelo")
        .insert({
            "nome_catalogo": nome_catalogo,
            "descricao_catalogo": descricao_catalogo,
            "descricao_detalhada": descricao_detalhada,
            "id_subfamilia": id_subfamilia
        })
        .execute()
    )

    return response.data[0] if response.data else None


def criar_cor(nome_cor, codigo_cor=None, imagem_url=None):
    """
    Cria uma nova cor. Se não vier um código hex explícito, o nome
    da cor é traduzido para inglês e convertido em hex automaticamente
    (tudo através de bibliotecas gratuitas).
    """

    if not codigo_cor:
        codigo_cor = traduzir_e_converter_cor(nome_cor)

    response = (
        supabase
        .table("cores_produto")
        .insert({
            "nome_cor": nome_cor,
            "codigo_cor": codigo_cor,
            "imagem_url": imagem_url
        })
        .execute()
    )

    return response.data[0] if response.data else None


# ============================================================
# NOVO PRODUTO - CRIAÇÃO COMPLETA (usado pelo pop-up)
# ============================================================

def criar_produto_admin(dados):
    """
    Cria um novo produto (variante) a partir dos dados do pop-up
    "Novo produto". 'dados' é um dicionário tipo request.form.

    Para cada nível (família, subfamília, modelo, cor), o campo
    "<nivel>_id" vale "novo" quando o admin optou por criar um
    novo registo em vez de escolher um já existente; nesse caso,
    os campos "<nivel>_..._novo" são usados para o criar.

    Lança ValueError com uma mensagem percetível quando faltam
    dados obrigatórios ou a referência já existe.

    IMPORTANTE: a referência, o preço base e o IVA são validados
    logo no início, ANTES de criar qualquer família/subfamília/
    modelo/cor nova. Assim, se a referência já existir (ou faltar
    algum dado obrigatório), nada fica criado "a meio" na base
    de dados.
    """

    # --------------------------------------------------------
    # REFERÊNCIA / PREÇO / IVA - validados primeiro
    # --------------------------------------------------------

    referencia = (dados.get("referencia") or "").strip()

    if not referencia:
        raise ValueError("É necessário indicar a referência do produto.")

    try:
        referencia = int(referencia)
    except ValueError:
        raise ValueError("A referência do produto deve ser numérica.")

    existente = (
        supabase
        .table("produtos")
        .select("referencia")
        .eq("referencia", referencia)
        .limit(1)
        .execute()
    )

    if existente.data:
        raise ValueError(f"Já existe um produto com a referência {referencia}.")

    preco_base = dados.get("preco_base")

    if not preco_base:
        raise ValueError("É necessário indicar o preço base.")

    try:
        if float(preco_base) < 0:
            raise ValueError("O preço base não pode ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("O preço base indicado não é válido.")

    id_iva = dados.get("id_iva")

    if not id_iva:
        raise ValueError("É necessário escolher o IVA.")

    try:
        id_iva = int(id_iva)
    except ValueError:
        raise ValueError("O IVA escolhido não é válido.")

    codigo_barras = (dados.get("codigo_barras") or "").strip() or None

    if codigo_barras:

        codigo_existente = (
            supabase
            .table("produtos")
            .select("referencia")
            .eq("codigo_barras_produto", codigo_barras)
            .limit(1)
            .execute()
        )

        if codigo_existente.data:
            raise ValueError(
                f"Já existe um produto com o código de barras {codigo_barras}."
            )

    stock_bruto = dados.get("stock") or 0

    try:
        stock = int(stock_bruto)
    except (TypeError, ValueError):
        raise ValueError("O stock indicado não é válido.")

    if stock < 0:
        raise ValueError("O stock não pode ser negativo.")

    if stock > 2147483647:
        raise ValueError(
            "O stock indicado é demasiado grande "
            "(máximo permitido: 2.147.483.647)."
        )

    descontinuado = dados.get("descontinuado") in ("on", "true", "True", True)

    # --------------------------------------------------------
    # FAMÍLIA
    # --------------------------------------------------------

    id_familia = dados.get("familia_id")

    if not id_familia:
        raise ValueError("É necessário escolher ou criar uma família.")

    if id_familia == "novo":

        nome_familia = (dados.get("familia_nome_novo") or "").strip()
        cor_familia_bruta = (dados.get("familia_cor_novo") or "").strip()

        if not nome_familia or not cor_familia_bruta:
            raise ValueError("Preenche o nome e a cor da nova família.")

        # Se já for um código hex válido, usa-o tal como está.
        # Caso contrário, trata-se de um nome de cor (em qualquer
        # idioma) e traduz-se/converte-se para hex, tal como
        # acontece com a cor das variantes de produto.
        if re.fullmatch(r"#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})", cor_familia_bruta):
            cor_familia = cor_familia_bruta
        else:
            cor_familia = traduzir_e_converter_cor(cor_familia_bruta)

        familia = criar_familia(
            nome=nome_familia,
            cor=cor_familia,
            # Valores por defeito por agora - estas colunas vão sair
            # da tabela "familia" mais tarde.
            ordem=0,
            pagina_inicial=0,
            pagina_final=0
        )

        if not familia:
            raise ValueError("Não foi possível criar a nova família.")

        id_familia = familia["id_familia"]

    else:
        id_familia = int(id_familia)

    # --------------------------------------------------------
    # SUBFAMÍLIA
    # --------------------------------------------------------

    id_subfamilia = dados.get("subfamilia_id")

    if not id_subfamilia:
        raise ValueError("É necessário escolher ou criar uma subfamília.")

    if id_subfamilia == "novo":

        nome_subfamilia = (dados.get("subfamilia_nome_novo") or "").strip()

        if not nome_subfamilia:
            raise ValueError("Preenche o nome da nova subfamília.")

        subfamilia = criar_subfamilia(
            nome=nome_subfamilia,
            id_familia=id_familia,
            # Valores por defeito por agora - estas colunas vão sair
            # da tabela "subfamilia" mais tarde.
            ordem=0,
            pagina=0
        )

        if not subfamilia:
            raise ValueError("Não foi possível criar a nova subfamília.")

        id_subfamilia = subfamilia["id_subfamilia"]

    else:
        id_subfamilia = int(id_subfamilia)

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    id_modelo = dados.get("modelo_id")

    if not id_modelo:
        raise ValueError("É necessário escolher ou criar um modelo.")

    if id_modelo == "novo":

        nome_modelo = (dados.get("modelo_nome_novo") or "").strip()

        if not nome_modelo:
            raise ValueError("Preenche o nome do novo modelo.")

        modelo = criar_modelo(
            nome_catalogo=nome_modelo,
            id_subfamilia=id_subfamilia,
            descricao_catalogo=(dados.get("modelo_descricao_novo") or "").strip() or None,
            descricao_detalhada=(dados.get("modelo_descricao_detalhada_novo") or "").strip() or None
        )

        if not modelo:
            raise ValueError("Não foi possível criar o novo modelo.")

        id_modelo = modelo["id_modelo"]

    else:
        id_modelo = int(id_modelo)

    # --------------------------------------------------------
    # COR
    # --------------------------------------------------------

    id_cor = dados.get("cor_id")

    if not id_cor:
        raise ValueError("É necessário escolher ou criar uma cor.")

    if id_cor == "novo":

        nome_cor_novo = (dados.get("cor_nome_novo") or "").strip()

        if not nome_cor_novo:
            raise ValueError("Preenche o nome da nova cor.")

        cor = criar_cor(
            nome_cor=nome_cor_novo,
            codigo_cor=(dados.get("cor_hex_novo") or "").strip() or None
        )

        if not cor:
            raise ValueError(
                "Não foi possível criar a nova cor "
                "(já deve existir uma cor com esse nome)."
            )

        id_cor = cor["id_cor"]

    else:
        id_cor = int(id_cor)

    # --------------------------------------------------------
    # CRIAR O PRODUTO (VARIANTE)
    # --------------------------------------------------------

    response = (
        supabase
        .table("produtos")
        .insert({
            "referencia": referencia,
            "id_modelo": id_modelo,
            "id_cor": id_cor,
            "preco_base": preco_base,
            "id_iva": id_iva,
            "quantidade_stock": stock,
            "codigo_barras_produto": codigo_barras,
            "descontinuado": descontinuado
        })
        .execute()
    )

    if not response.data:
        raise ValueError("Não foi possível criar o produto.")

    return response.data[0]


def atualizar_produto_admin(
    referencia,
    preco_base,
    stock,
    descontinuado,
    iva
):
    """
    Atualiza apenas os dados da variante do produto.

    O nome do modelo e a cor não são alterados aqui.
    """
    response_iva = (
        supabase
        .table("iva")
        .select("id_iva")
        .eq("percentagem", iva)
        .limit(1)
        .execute()
    )
    id_iva = response_iva.data[0]["id_iva"]

    response = (
        supabase
        .table("produtos")
        .update({
            "preco_base": preco_base,
            "quantidade_stock": stock,
            "descontinuado": descontinuado,
            "id_iva": id_iva
        })
        .eq("referencia", referencia)
        .execute()
    )

    return response.data


def obter_clientes(filtro=None):

    query = (
        supabase
        .table("cliente")
        .select("*")
        .order("nome")
    )

    if filtro:
        query = query.or_(
            f"nome.ilike.%{filtro}%,"
            f"nif.ilike.%{filtro}%"
        )

    response = query.execute()

    return response.data


def obter_cliente_admin(id_cliente):

    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq("id_cliente", id_cliente)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    cliente = response.data[0]

    morada_completa = cliente["morada"].split(", ")

    tamanho = len(morada_completa)

    morada = morada_completa[0] if tamanho > 0 else ''
    predio = morada_completa[1] if tamanho > 1 else ''
    andar = morada_completa[2] if tamanho > 2  else ''
    print(cliente["codigo_postal"])
    return {
        "id_cliente": cliente["id_cliente"],
        "nif": cliente["nif"],
        "nome": cliente["nome"],
        "morada": morada,
        "predio": predio,
        "andar": andar,
        "email": cliente["email"],
        "tel": cliente["telefone"],
        "postal": cliente["codigo_postal"],
        "local": cliente["localizacao"],
        "indicativo": cliente["indicativo"]
    }


def atualizar_cliente_admin(
    id_cliente,
    nome,
    nif,
    email,
    indicativo,
    telefone,
    codigo_postal,
    localizacao,
    morada
):

    response = (
        supabase
        .table("cliente")
        .update({
            "nome": nome,
            "nif": nif,
            "email": email,
            "indicativo": indicativo,
            "telefone": telefone,
            "codigo_postal": codigo_postal,
            "localizacao": localizacao,
            "morada": morada
        })
        .eq("id_cliente", id_cliente)
        .execute()
    )

    return response.data

def obter_info(filtro_cliente=None, data_inicio=None, data_fim=None):

    response = (
        supabase
        .table("linhas_pedido")
        .select("""
            produto_referencia,
            quantidade,
            valor_linha,

            produtos(
                id_modelo,
                preco_base,
                codigo_barras_produto,
                cores_produto(
                    nome_cor
                ),
                iva(
                    percentagem
                ),
                produtos_modelo(
                    nome_catalogo
                )
            ),

            pedido(
                id_pedido,
                valor_total,
                estado,
                observacoes,
                data_pedido,
                id_cliente,
                cliente(
                    nome
                )
            )
        """)
        .execute()
    )

    if not response.data:
        return []

    info = []

    for r in response.data:

        ped = r.get("pedido")
        prod = r.get("produtos")

        if not ped or not prod:
            continue

        cli = ped.get("cliente") or {}
        cor = prod.get("cores_produto") or {}
        iva = prod.get("iva") or {}
        model = prod.get("produtos_modelo") or {}

        info.append({
            "data": ped["data_pedido"],
            "id_pedido": ped["id_pedido"],
            "valor_total": ped["valor_total"],
            "estado_pedido": ped["estado"],
            "observacoes": ped["observacoes"],
            "nome_cliente": cli.get("nome"),
            "num_cliente": ped["id_cliente"],

            "id_modelo": prod["id_modelo"],
            "referencia": r["produto_referencia"],
            "preco": round(
                prod["preco_base"] * (
                    1 + iva.get("percentagem", 0) / 100
                ),
                2
            ),
            "nome_produto": model.get("nome_catalogo"),
            "quantidade": r["quantidade"],
            "codigo": prod["codigo_barras_produto"],
            "preco_total": r["valor_linha"],
            "cor": cor.get("nome_cor")
        })

    # --------------------------------------------------------
    # FILTRAR POR CLIENTE (nome ou número)
    # --------------------------------------------------------

    if filtro_cliente:

        filtro_lower = filtro_cliente.lower()

        info = [
            i for i in info
            if filtro_lower in (i["nome_cliente"] or "").lower()
            or filtro_lower == str(i["num_cliente"])
        ]

    # --------------------------------------------------------
    # FILTRAR POR PERÍODO
    # --------------------------------------------------------

    if data_inicio:
        info = [
            i for i in info
            if i["data"] and i["data"] >= data_inicio
        ]

    if data_fim:
        info = [
            i for i in info
            if i["data"] and i["data"] <= data_fim
        ]

    return sorted(
        info,
        key=lambda p: p["num_cliente"]
    )

def atualizar_estado_pedido_admin(id_pedido, estado):

    response = (
        supabase
        .table("pedido")
        .update({"estado": estado})
        .eq("id_pedido", id_pedido)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


