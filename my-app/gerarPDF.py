import os
import io

from datetime import date, timedelta

from config import supabase
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from gerar_barcode import gerar_conteudo_svg_barcode
from svglib.svglib import svg2rlg
from reportlab.platypus import Image as ImagemPDF


# ============================================================
# ESTILOS DE TEXTO USADOS NO DOCUMENTO
# ============================================================

styles = getSampleStyleSheet()

estilo_normal = styles["Normal"]

estilo_pequeno = ParagraphStyle(
    "Pequeno",
    parent=styles["Normal"],
    fontSize=8,
    leading=10
)

estilo_titulo_empresa = ParagraphStyle(
    "TituloEmpresa",
    parent=styles["Normal"],
    fontSize=11,
    leading=13,
    fontName="Helvetica-Bold"
)

estilo_titulo_documento = ParagraphStyle(
    "TituloDocumento",
    parent=styles["Normal"],
    fontSize=13,
    leading=16,
    fontName="Helvetica-Bold",
    alignment=TA_RIGHT
)

estilo_aviso = ParagraphStyle(
    "Aviso",
    parent=styles["Normal"],
    fontSize=9,
    leading=11,
    fontName="Helvetica-Oblique",
    alignment=TA_RIGHT
)

estilo_nome_cliente = ParagraphStyle(
    "NomeCliente",
    parent=styles["Normal"],
    fontSize=10,
    leading=12,
    fontName="Helvetica-Bold",
    alignment=TA_RIGHT
)

estilo_cliente_info = ParagraphStyle(
    "ClienteInfo",
    parent=styles["Normal"],
    fontSize=9,
    leading=11,
    alignment=TA_RIGHT
)

estilo_cabecalho_tabela = ParagraphStyle(
    "CabecalhoTabela",
    parent=styles["Normal"],
    fontSize=8,
    leading=10,
    fontName="Helvetica-Bold",
    textColor=colors.white
)

estilo_total_grande = ParagraphStyle(
    "TotalGrande",
    parent=styles["Normal"],
    fontSize=16,
    leading=19,
    fontName="Helvetica-Bold",
    alignment=TA_RIGHT
)


def gerar_fatura_pdf(dados_compra, nome_arquivo):
    """
    Gera o PDF da "Nota de Encomenda", com o mesmo layout do modelo
    em papel: cabeçalho (empresa + cliente), linha de informações do
    documento, tabela de artigos, IBAN, resumo de impostos, resumo
    financeiro, resumo de transporte e total final.

    'dados_compra' é um dicionário com, pelo menos, esta forma
    (ver obter_info_pdf() mais abaixo para um exemplo de como se
    monta a partir da base de dados):

        {
            "empresa": "Dataeme Acessórios Para Informática, LDA",
            "empresa_morada": "Praça Professor Santos Andrea, Nº 16-A",
            "empresa_codigo_postal": "1500-510 Benfica",
            "empresa_pais": "Portugal",
            "empresa_nif": "517975392",
            "empresa_iban": "PT50 0036 0444 9910 4021 7467 2",
            "empresa_email": "comercial@dataeme.pt",
            "empresa_telefone": "217 165 900",

            "id": "1/135",
            "data": date(2026, 9, 14),
            "data_vencimento": date(2026, 9, 14),
            "pagina": "1/1",
            "condicao_pagamento": "Pronto Pagamento",

            "nome_cliente": "Ana Cláudia Martins e Vasconcelos",
            "email": "...",
            "num_cliente": "8264",
            "cliente_morada": "...",
            "cliente_codigo_postal": "2700-750 Amadora",
            "cliente_pais": "PT",
            "cliente_v_ref": "-",

            "desconto_global": 0.0,
            "descontos_linha": 0.0,
            "portes": 0.0,
            "retencao": 0.0,

            "viatura": "-",
            "dados_carga": "Praça Professor Santos Andrea, Nº 16-A\\n1500-510 Benfica",
            "dados_descarga": "2700-750 Amadora",

            "itens": [
                {
                    "referencia": "1000041",
                    "nome_produto": "Cadeira Mars Gaming MGC - Ergoplus",
                    "quantidade": 1,
                    "preco": 89.90,
                    "desconto_pct": 0.0,
                    "taxa_iva": 23.0,
                    "preco_total": 89.90
                },
                ...
            ]
        }
    """

    caminho_completo = os.path.join("generated", nome_arquivo)

    os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

    doc = SimpleDocTemplate(
        caminho_completo,
        pagesize=letter,
        title=f"Nota de Encomenda {dados_compra['id']}",
        topMargin=20 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm
    )

    story = []

    # ============================================================
    # 1) CABEÇALHO
    #    Coluna esquerda -> logótipo + dados da empresa
    #    Coluna direita  -> nº do documento + dados do cliente
    #                       + aviso "Este documento não serve de Fatura"
    # ============================================================

    
    logo = ImagemPDF("media/logo/Dataeme_logo.png", width=90, height=60)
    

    dados_empresa_html = "<br/>".join(filter(None, [
        f"<b>{dados_compra['empresa']}</b>",
        dados_compra.get("empresa_morada"),
        dados_compra.get("empresa_codigo_postal"),
        dados_compra.get("empresa_pais"),
        f"NIF: {dados_compra.get('empresa_nif', '')}" if dados_compra.get("empresa_nif") else None,
        f"IBAN: {dados_compra.get('empresa_iban', '')}" if dados_compra.get("empresa_iban") else None,
        f"Email: {dados_compra.get('empresa_email', '')}" if dados_compra.get("empresa_email") else None,
        f"Tel: {dados_compra.get('empresa_telefone', '')}" if dados_compra.get("empresa_telefone") else None,
    ]))

    bloco_empresa = [
        logo,
        Spacer(1, 6),
        Paragraph(dados_empresa_html, estilo_pequeno)
    ]

    # ---- Coluna direita: nº documento + dados do cliente -------

    dados_cliente_html = "<br/>".join(filter(None, [
        f"<b>{dados_compra['nome_cliente']}</b>",
        dados_compra.get("cliente_morada"),
        dados_compra.get("cliente_codigo_postal"),
        dados_compra.get("cliente_pais"),
    ]))

    bloco_cliente = [
        Paragraph(f"Nota de Encomenda Nº BD {dados_compra['id']}", estilo_titulo_documento),
        Spacer(1, 10),
        Paragraph(dados_cliente_html, estilo_nome_cliente),
        Spacer(1, 10),
        Paragraph("Este documento não serve de Fatura", estilo_aviso)
    ]

    tabela_cabecalho = Table(
        [[bloco_empresa, bloco_cliente]],
        colWidths=[260, 260]
    )

    tabela_cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(tabela_cabecalho)
    story.append(Spacer(1, 14))

    # ============================================================
    # 2) LINHA DE INFORMAÇÕES DO DOCUMENTO
    #    V/Nº Contrib. | Cliente V/Ref | Condição Pagamento
    #    | Data Emissão | Data Vencimento | Pág.
    # ============================================================

    linha_info_cabecalho = [
        "V/Nº Contrib.",
        "Cliente V/ Ref.",
        "Condição de Pagamento",
        "Data Emissão",
        "Data Vencimento",
        "Pág."
    ]

    linha_info_valores = [
        dados_compra.get("nif", ""),
        dados_compra.get("num_cliente", ""),
        dados_compra.get("condicao_pagamento", "Pronto Pagamento"),
        dados_compra["data"].strftime("%Y-%m-%d") if hasattr(dados_compra["data"], "strftime") else str(dados_compra["data"]),
        dados_compra.get("data_vencimento").strftime("%Y-%m-%d") if hasattr(dados_compra.get("data_vencimento"), "strftime") else str(dados_compra.get("data_vencimento", "")),
        dados_compra.get("pagina", "1/1")
    ]

    tabela_info_documento = Table(
        [linha_info_cabecalho, linha_info_valores],
        colWidths=[75, 75, 110, 75, 85, 40]
    )

    tabela_info_documento.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story.append(tabela_info_documento)
    story.append(Spacer(1, 16))

    # ============================================================
    # 3) TABELA DE ARTIGOS
    #    Referência | Descrição | Qtd | Un. | P.Unit (c/Imp.)
    #    | Desc (%) | Taxa (%) | Total  [+ Cód. Barras, opcional]
    # ============================================================

    incluir_codigo_barras = False  # <- muda para False para tirar a coluna

    cabecalho_tabela_itens = [
        Paragraph("Referência", estilo_cabecalho_tabela),
        Paragraph("Descrição", estilo_cabecalho_tabela),
        Paragraph("Qtd.", estilo_cabecalho_tabela),
        Paragraph("Un.", estilo_cabecalho_tabela),
        Paragraph("P.Unit (c/Imp.)", estilo_cabecalho_tabela),
        Paragraph("Desc (%)", estilo_cabecalho_tabela),
        Paragraph("Taxa (%)", estilo_cabecalho_tabela),
        Paragraph("Total", estilo_cabecalho_tabela),
    ]

    if incluir_codigo_barras:
        cabecalho_tabela_itens.append(
            Paragraph("Cód. Barras", estilo_cabecalho_tabela)
        )

    tabela_dados = [cabecalho_tabela_itens]

    total_fatura = 0

    for item in dados_compra["itens"]:

        total_item = item["preco_total"]
        total_fatura += total_item

        linha = [
            item["referencia"],
            Paragraph(item["nome_produto"], styles["BodyText"]),
            str(item["quantidade"]),
            "UND",
            f"{item['preco']:.2f}",
            f"{item.get('desconto_pct', 0):.2f}%",
            f"{item.get('taxa_iva', 0):.2f}",
            f"{total_item:.2f}",
        ]

        if incluir_codigo_barras:

            codigo_barras_bytes = gerar_conteudo_svg_barcode(
                item["referencia"],
                item["quantidade"]
            )
            ficheiro_virtual_svg = io.BytesIO(codigo_barras_bytes)
            desenho_reportlab = svg2rlg(ficheiro_virtual_svg)
            desenho_reportlab.scale(0.55, 0.45)

            linha.append(desenho_reportlab)

        tabela_dados.append(linha)

    # ---- Linha do total geral da tabela -------------------------

    linha_total = [""] * (len(cabecalho_tabela_itens) - 2)
    linha_total += ["Total Geral:", f"€ {total_fatura:.2f}"]

    tabela_dados.append(linha_total)

    larguras_colunas = [55, 150, 30, 30, 60, 45, 40, 55]

    if incluir_codigo_barras:
        larguras_colunas.append(90)

    tabela_itens = Table(tabela_dados, colWidths=larguras_colunas)

    estilo_tabela_itens = [
        # Cabeçalho
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("FONTSIZE", (0, 0), (-1, 0), 8),

        # Grelha
        ("GRID", (0, 0), (-1, -2), 0.5, colors.black),

        # Espaçamento
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Alinhamentos das colunas de dados
        ("ALIGN", (0, 1), (0, -2), "CENTER"),   # Referência
        ("ALIGN", (1, 1), (1, -2), "LEFT"),     # Descrição
        ("ALIGN", (2, 1), (6, -2), "CENTER"),   # Qtd/Un/PUnit/Desc/Taxa
        ("ALIGN", (7, 1), (7, -2), "RIGHT"),    # Total

        # Linha do total geral
        ("LINEABOVE", (-2, -1), (-1, -1), 1.2, colors.black),
        ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (-2, -1), (-1, -1), "RIGHT"),
    ]

    if incluir_codigo_barras:
        estilo_tabela_itens.append(("ALIGN", (8, 1), (8, -2), "CENTER"))

    tabela_itens.setStyle(TableStyle(estilo_tabela_itens))

    story.append(tabela_itens)
    story.append(Spacer(1, 18))


    # ============================================================
    # 4) RESUMO DE IMPOSTOS (esquerda) + RESUMO FINANCEIRO (direita)
    # ============================================================

    # ---- Resumo de impostos -------------------------------------
    #
    # Agrupa os itens por taxa de IVA para mostrar a incidência e o
    # imposto de cada taxa (tal como no modelo em papel).

    resumo_por_taxa = {}

    for item in dados_compra["itens"]:

        taxa = item.get("taxa_iva", 0)
        incidencia = item["preco_total"] / (1 + taxa / 100) if taxa else item["preco_total"]

        if taxa not in resumo_por_taxa:
            resumo_por_taxa[taxa] = {"incidencia": 0, "imposto": 0}

        imposto = item["preco_total"] - incidencia

        resumo_por_taxa[taxa]["incidencia"] += incidencia
        resumo_por_taxa[taxa]["imposto"] += imposto

    linhas_resumo_impostos = [
        ["Designação", "Taxa", "Incidência", "Imposto"]
    ]

    total_incidencia = 0
    total_imposto = 0

    for taxa, valores in resumo_por_taxa.items():

        nome_taxa = "IVA Normal" if taxa == 23 else f"IVA {taxa:.0f}%"

        linhas_resumo_impostos.append([
            nome_taxa,
            f"{taxa:.0f}%",
            f"{valores['incidencia']:.2f}",
            f"{valores['imposto']:.2f}"
        ])

        total_incidencia += valores["incidencia"]
        total_imposto += valores["imposto"]

    tabela_resumo_impostos = Table(
        linhas_resumo_impostos,
        colWidths=[90, 40, 65, 65]
    )

    tabela_resumo_impostos.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # ---- Resumo financeiro (mercadorias, descontos, portes...) --

    mercadorias_servicos = sum(
        item["preco_total"] for item in dados_compra["itens"]
    )

    desconto_global = dados_compra.get("desconto_global", 0.0)
    descontos_linha = dados_compra.get("descontos_linha", 0.0)
    portes = dados_compra.get("portes", 0.0)
    retencao = dados_compra.get("retencao", 0.0)

    liquido = mercadorias_servicos - desconto_global - descontos_linha - total_imposto

    linhas_resumo_financeiro = [
        ["Mercadorias/Serviços", f"{mercadorias_servicos:.2f}"],
        ["Desconto Global", f"{desconto_global:.2f}"],
        ["Descontos Linha", f"{descontos_linha:.2f}"],
        ["Portes", f"{portes:.2f}"],
        ["Líquido", f"{liquido:.2f}"],
        ["Imposto", f"{total_imposto:.2f}"],
        ["Retenção", f"{retencao:.2f}"],
    ]

    tabela_resumo_financeiro = Table(
        linhas_resumo_financeiro,
        colWidths=[130, 65]
    )

    tabela_resumo_financeiro.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # ---- As duas tabelas lado a lado -----------------------------

    tabela_resumos = Table(
        [[tabela_resumo_impostos, tabela_resumo_financeiro]],
        colWidths=[270, 210]
    )

    tabela_resumos.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(tabela_resumos)
    story.append(Spacer(1, 20))


    bloco_total = [
        Paragraph("TOTAL (Euro)", estilo_pequeno),
        Paragraph(f"€ {total_fatura:.2f}", estilo_total_grande),
    ]

    tabela_rodape = Table(
        [[bloco_total]],
        colWidths=[280, 200]
    )

    tabela_rodape.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))

    story.append(tabela_rodape)

    doc.build(story)

    return caminho_completo


# ============================================================
# OBTER OS DADOS DO PEDIDO PARA O PDF
# ============================================================

def obter_info_pdf(id):

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
                iva(
                    percentagem
                ),
                produtos_modelo(
                    nome_catalogo
                )
            ),

            pedido(
                id_cliente,
                portes_envio,
                data_pedido,
                cliente(
                    nome,
                    email,
                    nif,
                    morada,
                    codigo_postal,
                    localizacao
                )
            )

        """)
        .eq("id_pedido", id)
        .execute()
    )

    if not response.data:
        return None

    info = {}
    itens = []

    ped = response.data[0].get("pedido")
    cli = ped.get("cliente")

    data_emissao = ped.get("data_pedido") or date.today()

    # --------------------------------------------------------
    # DADOS DA EMPRESA
    #
    # Estes valores não vêm da base de dados (não existe uma
    # tabela "empresa"); por agora estão fixos aqui. Se um dia
    # criares essa tabela, troca estas linhas por uma consulta.
    # --------------------------------------------------------

    info.update({
        "empresa": "Dataeme Acessórios Para Informática, LDA",
        "empresa_morada": "Praça Professor Santos Andrea, Nº 18-A",
        "empresa_codigo_postal": "1500-510 Benfica",
        "empresa_pais": "Portugal",
        "empresa_nif": "502569514",
        "empresa_iban": "PT50 0036 0444 9910 4021 7467 2",
        "empresa_email": "comercial@dataeme.pt",
        "empresa_telefone": "217 169 968",
    })

    # --------------------------------------------------------
    # DADOS DO DOCUMENTO / CLIENTE
    # --------------------------------------------------------

    info.update({
        "id": f"{id}",
        "data": data_emissao,
        "data_vencimento": data_emissao,  # Pronto pagamento -> mesma data
        "pagina": "1/1",
        "condicao_pagamento": "Pronto Pagamento",

        "nome_cliente": cli["nome"],
        "email": cli["email"],
        "num_cliente": ped["id_cliente"],
        "nif": cli["nif"],
        "cliente_morada": cli.get("morada"),
        "cliente_codigo_postal": cli.get("codigo_postal"),
        "cliente_pais": cli.get("localizacao"),
        "cliente_v_ref": "-",

        # Não há colunas para isto ainda - fica a 0 por agora.
        "desconto_global": 0.0,
        "descontos_linha": 0.0,
        "portes": float(ped.get("portes_envio") or 0),
        "retencao": 0.0,

        # Transporte - preenche/ajusta se vieres a guardar isto.
        "viatura": "-",
        "dados_carga": "Praça Professor Santos Andrea, Nº 16-A<br/>1500-510 Benfica",
        "dados_descarga": f"{cli.get('morada', '')}<br/>{cli.get('codigo_postal', '')}",
    })

    # --------------------------------------------------------
    # ARTIGOS
    # --------------------------------------------------------

    for linha in response.data or []:

        produto = linha.get("produtos")
        modelo = produto.get("produtos_modelo")
        iva = produto.get("iva") or {}

        itens.append({
            "referencia": str(linha["produto_referencia"]),
            "preco": produto["preco_base"],
            "nome_produto": modelo["nome_catalogo"],
            "quantidade": linha["quantidade"],
            "desconto_pct": 0.0,
            "taxa_iva": float(iva.get("percentagem") or 0),
            "preco_total": linha["valor_linha"]
        })

    info["itens"] = itens

    nome_arquivo = f"Encomenda_{id}.pdf"

    return gerar_fatura_pdf(info, nome_arquivo)