import requests
import re


def autofill_portugal_address(zip_code: str):
    """
    Obtém informação de um código postal português (CP7).

    Retorna:
        - street: rua/artéria
        - city: localidade
        - municipality: concelho
        - district_region: distrito
        - country: Portugal
        - postal_code: código postal
        - latitude: latitude
        - longitude: longitude
    """

    # Limpar o código postal
    clean_zip = re.sub(r"\D", "", zip_code)

    if len(clean_zip) != 7:
        return {
            "error": "Código postal inválido. Deve ter 7 dígitos."
        }

    formatted_zip = f"{clean_zip[:4]}-{clean_zip[4:]}"

    url = f"https://json.geoapi.pt/codigo_postal/{formatted_zip}"

    try:
        response = requests.get(
            url,
            params={"json": "true"},
            timeout=10
        )

        if response.status_code == 404:
            return {
                "error": f"Código postal {formatted_zip} não encontrado."
            }

        response.raise_for_status()

        data = response.json()

        # A API pode devolver informação sobre várias ruas
        ruas = data.get("ruas", [])

        # Se houver várias ruas, devolvemos todas
        if isinstance(ruas, list):
            streets = ruas
        else:
            streets = [ruas] if ruas else []

        return {
            "streets": streets,
            "city": data.get("Localidade", ""),
            "municipality": data.get("Concelho", ""),
            "district_region": data.get("Distrito", ""),
            "country": "Portugal",
            "postal_code": formatted_zip,

            # Coordenadas do código postal
            "latitude": (
                data.get("centro", [None, None])[0]
                if data.get("centro")
                else None
            ),
            "longitude": (
                data.get("centro", [None, None])[1]
                if data.get("centro")
                else None
            ),

            # Informação original, caso precises dela
            "raw": data
        }

    except requests.RequestException as e:
        return {
            "error": f"Erro ao contactar a API: {str(e)}"
        }


# Teste
zip_input = "2720-233"

form_data = autofill_portugal_address(zip_input)

print(f"Resultados para {zip_input}:")

for field, value in form_data.items():
    if field != "raw":
        print(f"  {field}: {value}")