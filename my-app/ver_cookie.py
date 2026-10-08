import base64, zlib, sys
c = sys.argv[1]
comprimido = c.startswith(".")
p = c.lstrip(".").split(".")[0]
p += "=" * (-len(p) % 4)
d = base64.urlsafe_b64decode(p)
if comprimido:
    d = zlib.decompress(d)
print(d.decode())