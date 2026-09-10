import io
import barcode
from barcode.writer import SVGWriter

from config import supabase, ph

def gerar_conteudo_svg_barcode(referencia, quantidade):
    fp = io.BytesIO()

    lista = f"{referencia} | {quantidade}"

    codigo = barcode.get("code128", lista, writer=SVGWriter())
    
    codigo.write(fp, options={"module_width": 0.3,"module_height":25, "quiet_zone": 1.5 })
    
    # RETORNAR BYTES diretamente, não string pois estava a dar problema no outro lado
    fp.seek(0)
    return fp.read()