import pandas as pd
from config import supabase
from services.admin_service import traduzir_e_converter_cor
from gerar_barcode import barcode_text

TAMANHO_LOTE = 500      # linhas por pedido à base de dados
TAMANHO_PAGINA = 1000   # linhas por leitura (limite do Supabase)


# ============================================================
# LEITURA / ESCRITA EM MASSA
# ============================================================

def _ler_tudo(tabela, colunas, ordenar_por):
    """Lê todas as linhas de uma tabela (o Supabase devolve no máximo
    1000 por pedido, por isso lê em páginas)."""

    dados = []
    inicio = 0

    while True:

        resposta = (
            supabase
            .table(tabela)
            .select(colunas)
            .order(ordenar_por)
            .range(inicio, inicio + TAMANHO_PAGINA - 1)
            .execute()
        )

        pagina = resposta.data or []
        dados.extend(pagina)

        if len(pagina) < TAMANHO_PAGINA:
            break

        inicio += TAMANHO_PAGINA

    return dados


def _inserir_em_lotes(tabela, linhas):
    """Insere várias linhas de uma vez. Se um lote falhar, tenta linha a
    linha para que uma linha com erro não estrague as restantes.
    Devolve (linhas_inseridas, numero_de_falhas)."""

    inseridas = []
    falhas = 0

    for i in range(0, len(linhas), TAMANHO_LOTE):

        lote = linhas[i:i + TAMANHO_LOTE]

        try:

            resposta = (
                supabase
                .table(tabela)
                .insert(lote)
                .execute()
            )

            inseridas.extend(resposta.data or [])

        except Exception as erro:

            print(
                f"Lote de {tabela} falhou ({erro}). "
                f"A inserir linha a linha..."
            )

            for linha in lote:

                try:

                    resposta = (
                        supabase
                        .table(tabela)
                        .insert(linha)
                        .execute()
                    )

                    inseridas.extend(resposta.data or [])

                except Exception as erro_linha:

                    falhas += 1

                    print(
                        f"ERRO em {tabela} {linha}: {erro_linha}"
                    )

        print(
            f"{tabela}: {min(i + TAMANHO_LOTE, len(linhas))}"
            f"/{len(linhas)} processadas"
        )

    return inseridas, falhas


def _texto_obrigatorio(valor, campo):

    if pd.isna(valor) or not str(valor).strip():
        raise ValueError(f"Campo obrigatório em falta: {campo}")

    return str(valor).strip()


# ============================================================
# CRIAÇÃO DE FAMÍLIA / SUBFAMÍLIA / COR / IVA
# (só usadas quando ainda não existem)
# ============================================================

def criar_id_familia(nome, cor=None, descricao=None):

    if pd.isna(cor):
        cor = "#0E7C86"

    elif not cor.startswith("#"):
        cor = traduzir_e_converter_cor(cor)



    if pd.isna(descricao):
        descricao = ""

    response = (
        supabase
        .table("familia")
        .insert({
            "nome": nome,
            "cor": cor,
            "descricao": descricao
        })
        .execute()
    )
    
    if not response.data:
        raise Exception(
            f"Erro ao criar a família: {nome}"
        )

    return response.data[0]["id_familia"]


def criar_id_subfamilia(nome, id_familia, descricao=None):

    if pd.isna(descricao):
        descricao = ""

    response = (
        supabase
        .table("subfamilia")
        .insert({
            "nome": nome,
            "descricao": descricao,
            "ordem": 0,
            "familia_id_familia": id_familia
        })
        .execute()
    )
    
    if not response.data:
        raise Exception(
            f"Erro ao criar a subfamília: {nome}"
        )

    return response.data[0]["id_subfamilia"]


def criar_cor(nome_cor, codigo_cor):

    if not codigo_cor.startswith("#"):
        codigo_cor = traduzir_e_converter_cor(codigo_cor)
        
    response = (
        supabase
        .table("cores_produto")
        .insert({
            "nome_cor": nome_cor.strip(),
            "codigo_cor": codigo_cor,
            "imagem_url": None
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar a cor: {nome_cor}"
        )

    return response.data[0]["id_cor"]


def criar_iva(percentagem, categoria=None):
    
    if pd.isna(categoria):
        categoria = ""
        
    percentagem = float(percentagem)

    response = (
        supabase
        .table("iva")
        .insert({
            "percentagem": percentagem,
            "descricao": categoria
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar IVA: {percentagem}%"
        )

    return response.data[0]["id_iva"]


# ============================================================
# IMPORTAÇÃO
# ============================================================

def importar_produtos(ficheiro):
    extensoes_aceites_X = (".xlsx", ".xls")

    if ficheiro.filename.lower().endswith(extensoes_aceites_X):

        # sheet_name=0 -> lê só a primeira folha e devolve já um DataFrame
        df = pd.read_excel(
            ficheiro,
            sheet_name=0,
            usecols="A:P",
        )

    else:

        df = pd.read_csv(
            ficheiro,
            sep=","
        )

    # --------------------------------------------------------
    # 1) CARREGAR TUDO O QUE JÁ EXISTE (poucos pedidos)
    #    Assim não é preciso perguntar à base de dados linha a linha.
    # --------------------------------------------------------

    familias = {
        f["nome"].strip(): f["id_familia"]
        for f in _ler_tudo("familia", "id_familia,nome", "id_familia")
    }

    subfamilias = {
        s["nome"].strip(): s["id_subfamilia"]
        for s in _ler_tudo("subfamilia", "id_subfamilia,nome", "id_subfamilia")
    }

    cores = {
        c["nome_cor"].strip(): c["id_cor"]
        for c in _ler_tudo("cores_produto", "id_cor,nome_cor", "id_cor")
    }

    ivas = {
        float(i["percentagem"]): i["id_iva"]
        for i in _ler_tudo("iva", "id_iva,percentagem", "id_iva")
    }

    modelos = {
        m["nome_catalogo"].strip(): m["id_modelo"]
        for m in _ler_tudo("produtos_modelo", "id_modelo,nome_catalogo", "id_modelo")
    }

    existentes = {
        int(p["referencia"])
        for p in _ler_tudo("produtos", "referencia", "referencia")
    }

    # --------------------------------------------------------
    # 2) PERCORRER O FICHEIRO (só em memória; cria apenas
    #    famílias/subfamílias/cores/IVA que ainda não existam)
    # --------------------------------------------------------

    novos_modelos = {}   # nome -> dados do modelo a criar
    pendentes = []       # produtos à espera do id do modelo
    vistos = set()

    ignorados = 0
    erros = 0

    for _, row in df.iterrows():

        try:

            if pd.isna(row["Referência"]):
                continue

            referencia = int(row["Referência"])

            if referencia in existentes or referencia in vistos:
                ignorados += 1
                continue

            # ------------------------------------------------
            # PREÇO
            # ------------------------------------------------

            preco = row["Preço Base Sem IVA"]

            if pd.isna(preco):
                ignorados += 1
                continue

            # ------------------------------------------------
            # FAMÍLIA
            # ------------------------------------------------

            nome_familia = _texto_obrigatorio(row["Família"], "Família")

            id_familia = familias.get(nome_familia)

            if id_familia is None:
                id_familia = criar_id_familia(
                    nome_familia,
                    row["Cor da Família"],
                    row["Descrição Família"]
                )
                familias[nome_familia] = id_familia

            # ------------------------------------------------
            # SUBFAMÍLIA
            # ------------------------------------------------

            nome_subfamilia = _texto_obrigatorio(row["Subfamília"], "Subfamília")

            id_subfamilia = subfamilias.get(nome_subfamilia)

            if id_subfamilia is None:
                id_subfamilia = criar_id_subfamilia(
                    nome_subfamilia,
                    id_familia,
                    row["Descrição Subfamília"]
                )
                subfamilias[nome_subfamilia] = id_subfamilia

            # ------------------------------------------------
            # IVA
            # ------------------------------------------------

            percentagem = float(row["Percentagem IVA"])

            id_iva = ivas.get(percentagem)

            if id_iva is None:
                id_iva = criar_iva(percentagem, row["Categoria IVA"])
                ivas[percentagem] = id_iva

            # ------------------------------------------------
            # COR
            # ------------------------------------------------

            if pd.isna(row["Nome Cor"]):
                nome_cor = "Sem Cor"
            else:
                nome_cor = str(row["Nome Cor"]).strip()

            id_cor = cores.get(nome_cor)

            if id_cor is None:

                if nome_cor == "Sem Cor":
                    codigo_cor = "#ffffff"
                elif pd.isna(row["Código Cor"]):
                    codigo_cor = "#cccccc"
                else:
                    codigo_cor = str(row["Código Cor"]).strip()

                id_cor = criar_cor(nome_cor, codigo_cor)
                cores[nome_cor] = id_cor

            # ------------------------------------------------
            # MODELO (criados todos de uma vez mais à frente)
            # ------------------------------------------------

            nome_modelo = _texto_obrigatorio(row["Nome Produto"], "Nome Produto")

            if nome_modelo not in modelos and nome_modelo not in novos_modelos:

                descricao_breve = row["Descrição Breve"]
                descricao_detalhada = row["Descrição Detalhada"]

                novos_modelos[nome_modelo] = {
                    "nome_catalogo": nome_modelo,
                    "descricao_catalogo": (
                        "Sem Descrição" if pd.isna(descricao_breve)
                        else str(descricao_breve)
                    ),
                    "descricao_detalhada": (
                        "Sem Descrição" if pd.isna(descricao_detalhada)
                        else str(descricao_detalhada)
                    ),
                    "id_subfamilia": id_subfamilia
                }

            # ------------------------------------------------
            # STOCK / DESCONTINUADO
            # ------------------------------------------------

            stock = row["Stock"]

            if pd.isna(stock):
                stock = 9999

            descontinuado = row["Descontinuado?"]

            if pd.isna(descontinuado):
                descontinuado = False

            pendentes.append({
                "_modelo": nome_modelo,
                "referencia": referencia,
                "id_cor": int(id_cor),
                "preco_base": float(preco),
                "id_iva": int(id_iva),
                "quantidade_stock": int(stock),
                "codigo_barras_produto": barcode_text(referencia),
                "descontinuado": bool(descontinuado)
            })

            vistos.add(referencia)

        except Exception as erro:

            erros += 1

            print(
                f"ERRO na linha do produto "
                f"{row.get('Referência')}: {erro}"
            )

    # --------------------------------------------------------
    # 3) CRIAR OS MODELOS NOVOS (em lotes)
    # --------------------------------------------------------

    if novos_modelos:

        criados, falhas = _inserir_em_lotes(
            "produtos_modelo",
            list(novos_modelos.values())
        )

        erros += falhas

        for modelo in criados:
            modelos[modelo["nome_catalogo"].strip()] = modelo["id_modelo"]

    # --------------------------------------------------------
    # 4) CRIAR OS PRODUTOS (em lotes)
    # --------------------------------------------------------

    linhas = []

    for produto in pendentes:

        id_modelo = modelos.get(produto.pop("_modelo"))

        if id_modelo is None:
            erros += 1
            print(
                f"ERRO: modelo não encontrado para o produto "
                f"{produto['referencia']}"
            )
            continue

        produto["id_modelo"] = int(id_modelo)
        linhas.append(produto)

    inseridos, falhas = _inserir_em_lotes("produtos", linhas)

    erros += falhas

    print(
        f"\nImportação concluída: {len(inseridos)} produtos inseridos, "
        f"{ignorados} ignorados (já existiam ou sem preço), {erros} erros."
    )

    return {
        "inseridos": len(inseridos),
        "ignorados": ignorados,
        "erros": erros
    }