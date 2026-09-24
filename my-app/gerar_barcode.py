import io
import barcode
from barcode.writer import SVGWriter

from config import supabase, ph

def gerar_conteudo_svg_barcode(referencia, quantidade):
    fp = io.BytesIO()
    lista = f"{referencia} | {quantidade}"

    codigo = barcode.get("code128", lista, writer=SVGWriter())  # já é str, ok
    codigo.write(fp, options={"module_width": 0.3, "module_height": 25, "quiet_zone": 1.5})

    fp.seek(0)
    return fp.read()


def gerar_conteudo_svg_bar(referencia):
    fp = io.BytesIO()

    codigo = barcode.get("code128", str(referencia), writer=SVGWriter())  # <- fix
    codigo.write(fp, options={"module_width": 0.3, "module_height": 25, "quiet_zone": 1.5})

    fp.seek(0)
    return fp.read()

def barcode_text(referencia):
    """
    Devolve o valor de texto do código de barras (sem gerar imagem).
    """
    codigo = barcode.get("code128", str(referencia))
    return codigo.get_fullcode()