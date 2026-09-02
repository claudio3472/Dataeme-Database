import io
import barcode
from barcode.writer import SVGWriter

#
#produtos = (
#    supabase
#    .table("produtos")
#    .select("referencia")
#    .execute()
#)

def gerar_conteudo_svg_barcode(referencia):
    fp = io.BytesIO()
    codigo = barcode.get("code128", referencia, writer=SVGWriter())
    
    codigo.write(fp, options={"module_width": 0.3,"module_height":25, "quiet_zone": 1.5 })
    
    # RETORNAR BYTES diretamente, não string pois estava a dar problema no outro lado
    fp.seek(0)
    return fp.read()