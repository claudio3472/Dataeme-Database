"""
Converte os links de "Sair" (GET) em pedidos POST com token CSRF.

Troca  <a href="{{ url_for('logout') }}">Sair</a>  (ou href="/logout")
por    <a href="#" onclick="...submit()">Sair</a> + um <form method="POST"> escondido.
O aspeto do link não muda (continua a ser o mesmo <a>, com as mesmas classes).

Uso (na raiz do projeto):
    python converter_logout_templates.py            # pasta templates/
    python converter_logout_templates.py outra/pasta
É seguro correr mais de uma vez.
"""
import pathlib
import re
import sys

PASTA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "templates")

ANCORA = re.compile(
    r'<a\b(?P<antes>[^>]*?)\bhref\s*=\s*(?P<q>["\'])'
    r'(?P<href>\{\{\s*url_for\(\s*[\'"]logout[\'"]\s*\)\s*\}\}|/logout)(?P=q)'
    r'(?P<depois>[^>]*)>(?P<texto>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

FORM = (
    '<form method="POST" action="{{ url_for(\'logout\') }}" style="display:none">'
    '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
    '</form>'
)

convertidos = 0

for ficheiro in sorted(PASTA.rglob("*.html")):
    texto = ficheiro.read_bytes().decode("utf-8")
    crlf = "\r\n" in texto

    def trocar(m):
        global convertidos
        convertidos += 1
        return (
            f'<a{m.group("antes")}href="#"{m.group("depois")} '
            f'onclick="event.preventDefault(); this.nextElementSibling.submit();">'
            f'{m.group("texto")}</a>{FORM}'
        )

    novo = ANCORA.sub(trocar, texto)

    if novo != texto:
        if crlf:
            novo = novo.replace("\r\n", "\n").replace("\n", "\r\n")
        ficheiro.write_bytes(novo.encode("utf-8"))
        print("atualizado:", ficheiro)

print(f"\n{convertidos} link(s) de logout convertido(s).")

# Referências a logout que o script NÃO converteu (verificar à mão)
restantes = []
for ficheiro in sorted(PASTA.rglob("*.html")):
    for n, linha in enumerate(ficheiro.read_text(encoding="utf-8").splitlines(), 1):
        if "logout" in linha.lower() and "action=\"{{ url_for('logout') }}\"" not in linha:
            restantes.append(f"  {ficheiro}:{n}: {linha.strip()[:110]}")

if restantes:
    print("\nAINDA TÊM 'logout' (verifique à mão; têm de ser POST com csrf_token):")
    print("\n".join(restantes))