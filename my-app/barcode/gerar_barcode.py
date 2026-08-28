
import barcode
from barcode.writer import SVGWriter

#
#produtos = (
#    supabase
#    .table("produtos")
#    .select("referencia")
#    .execute()
#)

referencia = "Teste123"

# a usar code128 porque não sei se querem usar outro
codigo = barcode.get("code128",referencia,writer=SVGWriter())

#module_width,module_height,font_size,text_distance,quiet_zone
codigo.save("barcode",options={ "module_width": 1,"module_height": 60})

print(f"Código de barras criado para: {referencia}")

