"""
Uso (na raiz do projeto):
    python adicionar_csrf_templates.py            # pasta templates/
    python adicionar_csrf_templates.py outra/pasta
"""
import pathlib
import re
import sys

PASTA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "templates")
TOKEN = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'

FORM = re.compile(r'<form\b[^>]*\bmethod\s*=\s*["\']?post["\']?[^>]*>', re.IGNORECASE)

total = 0

for ficheiro in sorted(PASTA.rglob("*.html")):
    texto = ficheiro.read_bytes().decode("utf-8")
    crlf = "\r\n" in texto

    def inserir(m):
        global total
        depois = texto[m.end(): m.end() + 250]
        if "csrf_token" in depois:
            return m.group(0)
        total += 1
        return m.group(0) + "\n" + TOKEN

    novo = FORM.sub(inserir, texto)

    if novo != texto:
        if crlf:
            novo = novo.replace("\r\n", "\n").replace("\n", "\r\n")
        ficheiro.write_bytes(novo.encode("utf-8"))
        print("atualizado:", ficheiro)

print(f"{total} formulário(s) atualizado(s).")
print()
print("ATENÇÃO: pedidos POST feitos por JavaScript (fetch/XMLHttpRequest) também precisam do token.")
print('Adicione ao <head>:  <meta name="csrf-token" content="{{ csrf_token() }}">')
print("e envie o cabeçalho:  headers: {'X-CSRFToken': document.querySelector('meta[name=csrf-token]').content}")