import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from svglib.svglib import svg2rlg

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
    story.append(Paragraph(f"Número da Fatura: #{dados_compra['id']}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Dados do Cliente
    story.append(Paragraph("<b>Dados do Cliente:</b>", styles['Heading3']))
    story.append(Paragraph(f"Nome: {dados_compra['cliente_nome']}", styles['Normal']))
    story.append(Paragraph(f"E-mail: {dados_compra['cliente_email']}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Tabela de Itens Comprados
    tabela_dados = [["Produto / Serviço", "Qtd", "Preço Unit.", "Total", "Código Barras"]]
    total_fatura = 0

    for item in dados_compra['itens']:
        total_item = item['qtd'] * item['preco']
        total_fatura += total_item
        
        codigo_barras_bytes = gerar_conteudo_svg_barcode(item['referencia'])
        ficheiro_virtual_svg = io.BytesIO(codigo_barras_bytes)
        desenho_reportlab = svg2rlg(ficheiro_virtual_svg)
        # Ajustar escala do barcode para caber
        desenho_reportlab.scale(0.5, 0.5)
        tabela_dados.append([item['nome'], str(item['qtd']), f"€ {item['preco']:.2f}", f"€ {total_item:.2f}", desenho_reportlab])

    # Linha do total — 5 colunas para corresponder ao cabeçalho
    tabela_dados.append(["", "", "", "Total Geral:", f"€ {total_fatura:.2f}"])
    
    # Larguras das colunas — 5 valores para 5 colunas
    tabela_itens = Table(tabela_dados, colWidths=[150, 40, 80, 80, 170])
    
    tabela_itens.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Alinhamentos
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Qtd centrada
        ('ALIGN', (-2, -1), (-1, -1), 'RIGHT'),  # Total alinhado à direita
        
        # Grelha
        ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
        
        # Linha do total
        ('LINEABOVE', (-2, -1), (-1, -1), 1.5, colors.black),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(tabela_itens)
    doc.build(story)


dados_da_base_de_dados = {
    "empresa": "LOJA",
    "id": "2026-9482",
    "data": "02/09/2026",
    "cliente_nome": "Claudio Catarino",
    "cliente_email": "claudio@exemplo.pt",
    "itens": [
        {"nome": "Cabo HDMI", "qtd": 1, "preco": 29.90, "referencia": "cabo1234"},
        {"nome": "Portátil MSI Katana 15 B13V", "qtd": 1, "preco": 1990, "referencia": "Monitor15B13V"}
    ],
}

gerar_fatura_pdf(dados_da_base_de_dados, "generated/fatura_b.pdf")