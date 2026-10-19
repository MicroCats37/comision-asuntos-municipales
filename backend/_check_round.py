import os, re
imports_with = []
for root, _, files in os.walk(r'C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\modules'):
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        try:
            content = open(p, encoding='utf-8').read()
        except:
            continue
        for m in re.finditer(r'ROUND_HALF_UP', content):
            start = m.start()
            before = content[max(0,start-3):start]
            after = content[m.end():m.end()+3]
            is_string = ('"' in before or '"' in after)
            if not is_string:
                imports_with.append((p, content[max(0,start-50):m.end()+50].replace(chr(10),' | ')))
print('Archivos usando ROUND_HALF_UP como variable:')
seen = set()
for p, ctx in imports_with:
    if p not in seen:
        seen.add(p)
        print('  ' + p)
        print('    CTX:', ctx[:120])
