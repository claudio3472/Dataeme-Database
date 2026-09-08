import os
import io

from config import supabase, ph
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from svglib.svglib import svg2rlg
from datetime import date

from gerar_barcode import gerar_conteudo_svg_barcode


def gerar_fatura_pdf(dados_compra, nome_arquivo):

    # Criar pasta se não existir
    os.makedirs(os.path.dirname(nome_arquivo), exist_ok=True)

    doc = SimpleDocTemplate(nome_arquivo, pagesize=letter, title=f"Fatura {dados_compra['id']}")
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo do Título
    titulo_style = ParagraphStyle(
        'TituloFatura',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.black,
        spaceAfter=15
    )
    
    # Cabeçalho da Empresa
    story.append(Paragraph(f"<b>{dados_compra['empresa']}</b>", titulo_style))
    story.append(Paragraph(f"Data da Emissão: {dados_compra['data']}", styles['Normal']))
    story.append(Paragraph(f"Número da Nota de Encomenda: #{dados_compra['id']}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Dados do Cliente
    story.append(Paragraph("<b>Dados do Cliente:</b>", styles['Heading3']))
    story.append(Paragraph(f"Nome: {dados_compra['nome_cliente']}", styles['Normal']))
    story.append(Paragraph(f"E-mail: {dados_compra['email']}", styles['Normal']))
    story.append(Paragraph(f"Número do Cliente: {dados_compra['num_cliente']}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Tabela de Itens Comprados
    tabela_dados = [
        ["Referência", "Produto / Serviço", "Qtd", "Preço Unit.", "Total", "Código Barras"]
    ]

    total_fatura = 0

    for item in dados_compra['itens']:
        total_item = item["preco_total"]
        total_fatura += total_item

        codigo_barras_bytes = gerar_conteudo_svg_barcode(item['referencia'], item['quantidade'])
        ficheiro_virtual_svg = io.BytesIO(codigo_barras_bytes)
        desenho_reportlab = svg2rlg(ficheiro_virtual_svg)

        # Reduzir tamanho do barcode
        desenho_reportlab.scale(0.60, 0.50)

        nome_produto = Paragraph(
            item["nome_produto"],
            styles["BodyText"]
        )

        tabela_dados.append([
            item['referencia'],
            nome_produto,
            str(item['quantidade']),
            f"€ {item['preco']:.2f}",
            f"€ {total_item:.2f}",
            desenho_reportlab
        ])

    # Linha do total
    tabela_dados.append([
        "",
        "",
        "",
        "",
        "Total Geral:",
        f"€ {total_fatura:.2f}"
    ])

    tabela_itens = Table(
        tabela_dados,
        colWidths=[60, 210, 35, 70, 70, 140]
    )

    tabela_itens.setStyle(TableStyle([

        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),

        # Grelha
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # Alinhamento vertical
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Referência
        ('ALIGN', (0, 1), (0, -2), 'CENTER'),

        # Nome produto
        ('ALIGN', (1, 1), (1, -2), 'LEFT'),

        # Quantidade
        ('ALIGN', (2, 1), (2, -2), 'CENTER'),

        # Preços
        ('ALIGN', (3, 1), (4, -2), 'RIGHT'),

        # Barcode
        ('ALIGN', (5, 1), (5, -2), 'CENTER'),

        # Linha total
        ('LINEABOVE', (4, -1), (5, -1), 1.5, colors.black),
        ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
        ('ALIGN', (4, -1), (5, -1), 'RIGHT'),
    ]))
    
    story.append(tabela_itens)
    doc.build(story)

def obter_info(id):

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
                produtos_modelo(
                    nome_catalogo       
                )
            ),

            pedido(
                id_cliente,
                cliente(
                    nome,
                    email
                )
            )
        
        """)
        .eq("id_pedido", id)
        .execute()
    )

    if not response.data:
        return None

    info = {}
    itens=[]

    ped = response.data[0].get("pedido")
    cli = ped.get("cliente")

    info.update({
        "empresa": "Dataeme",
        "id": "2026-9482",
        "data": date.today(),
        "nome_cliente": cli["nome"],
        "email": cli["email"],
        "num_cliente": ped["id_cliente"]
    })

    for r in response.data or []:

        prod = r.get("produtos")
        model = prod.get("produtos_modelo")

        itens.append({
            "referencia": str(r["produto_referencia"]),
            "preco": prod["preco_base"],
            "nome_produto": model["nome_catalogo"],
            "quantidade": r["quantidade"],
            "preco_total": r["valor_linha"]
        })

    info.update({"itens": itens})
    gerar_fatura_pdf(info, "generated/fatura_b.pdf")

obter_info(1)