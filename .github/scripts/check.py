#!/usr/bin/env python3
"""Guardas do index.html: o que a página promete, verificado antes do deploy.

Uso:
    python3 .github/scripts/check.py [arquivo]        verifica (sai com 1 se falhar)
    python3 .github/scripts/check.py --fix [arquivo]  regrava o hash da CSP

Só biblioteca padrão; a guarda de sintaxe usa o `node` do PATH.
Cada guarda tem um nome, e test_check.py prova por mutação que cada uma
realmente reprova o que deveria.
"""
import base64
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
PREFS_KEY = "senha-forte-prefs"

# A política inteira é comparada por igualdade: afrouxar a CSP exige mexer aqui.
CSP_TEMPLATE = (
    "default-src 'none'; "
    "script-src 'sha256-{hash}'; "
    "style-src 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "base-uri 'none'; "
    "form-action 'none'"
)

SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
CSP_RE = re.compile(
    r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"\s*/?>', re.I
)

# APIs que tiram dados da página (rede, navegação) ou carregam código de fora.
NETWORK_PATTERNS = [
    (r"\bfetch\s*\(", "fetch("),
    (r"XMLHttpRequest", "XMLHttpRequest"),
    (r"sendBeacon", "sendBeacon"),
    (r"WebSocket", "WebSocket"),
    (r"EventSource", "EventSource"),
    (r"RTCPeerConnection", "RTCPeerConnection"),
    (r"serviceWorker", "serviceWorker"),
    (r"importScripts", "importScripts"),
    (r"\bimport\s*\(", "import("),
    (r"\bnew\s+Image\b", "new Image"),
    (r"\bwindow\.open\b", "window.open"),
    (r"\blocation\b", "location"),
]

STORAGE_FORBIDDEN = ["sessionStorage", "indexedDB", "document.cookie", "caches."]
# Estado em memória que guarda senhas: não pode aparecer em save().
SECRET_NAMES = ["current", "history"]


def scripts(html):
    return [(m.group(1).strip(), m.group(2)) for m in SCRIPT_RE.finditer(html)]


def inline_script(html):
    found = scripts(html)
    return found[0][1] if len(found) == 1 else None


def script_hash(js):
    # O parser de HTML normaliza CRLF para LF antes de o navegador calcular o hash.
    data = js.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


class _Attrs(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.handlers = []

    def handle_starttag(self, tag, attrs):
        for name, _ in attrs:
            if name.lower().startswith("on"):
                self.handlers.append("<%s %s>" % (tag, name))

    handle_startendtag = handle_starttag


def check_structure(html):
    errors = []
    found = scripts(html)
    if len(found) != 1:
        errors.append("esperado exatamente 1 <script>, encontrados %d" % len(found))
    for attrs, _ in found:
        if attrs:
            errors.append("o <script> deve ser inline e sem atributos (tem: %s)" % attrs)
    if len(STYLE_RE.findall(html)) != 1:
        errors.append("esperado exatamente 1 <style>")
    parser = _Attrs()
    parser.feed(html)
    for h in parser.handlers:
        errors.append("handler inline %s: a CSP o bloqueia; use addEventListener" % h)
    return errors


def check_syntax(html):
    js = inline_script(html)
    if js is None:
        return ["sem <script> único para verificar"]
    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(js)
        try:
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        except FileNotFoundError:
            return ["node não encontrado no PATH: a sintaxe não foi verificada"]
        if r.returncode != 0:
            return ["erro de sintaxe no script:\n" + r.stderr.strip()]
    finally:
        os.unlink(path)
    return []


def check_csp(html):
    js = inline_script(html)
    if js is None:
        return ["sem <script> único para calcular o hash"]
    metas = list(CSP_RE.finditer(html))
    if len(metas) != 1:
        return ["esperada exatamente 1 <meta http-equiv=\"Content-Security-Policy\">, "
                "encontradas %d" % len(metas)]
    errors = []
    meta = metas[0]
    # Uma CSP em <meta> só vale para o que vem depois dela no documento.
    first = re.search(r"<(link|style|script)\b", html, re.I)
    if first and first.start() < meta.start():
        errors.append("a <meta> da CSP deve vir antes de qualquer <link>, <style> ou <script>")
    expected = CSP_TEMPLATE.format(hash=script_hash(js))
    if meta.group(1) != expected:
        errors.append(
            "a política não confere com o esperado.\n"
            "    atual:    %s\n"
            "    esperada: %s\n"
            "    se só o script mudou: python3 .github/scripts/check.py --fix"
            % (meta.group(1), expected)
        )
    return errors


def check_random(html):
    if re.search(r"Math\s*\.\s*random", html):
        return ["Math.random encontrado: use randInt(), que usa crypto.getRandomValues"]
    return []


def check_network(html):
    js = inline_script(html) or ""
    return ["API proibida no script: %s" % label
            for pattern, label in NETWORK_PATTERNS if re.search(pattern, js)]


def check_urls(html):
    errors = []
    for m in re.finditer(r"(?:https?:)?//([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)", html):
        host = m.group(1).lower()
        if host not in FONT_HOSTS:
            errors.append("referência externa não permitida: %s" % m.group(0))
    return errors


def check_storage(html):
    js = inline_script(html) or ""
    errors = []
    for token in STORAGE_FORBIDDEN:
        if token in js:
            errors.append("armazenamento proibido: %s" % token)
    if len(re.findall(r'\bvar\s+KEY\s*=\s*"%s"\s*;' % re.escape(PREFS_KEY), js)) != 1:
        errors.append('esperado exatamente um `var KEY = "%s";`' % PREFS_KEY)
    if len(re.findall(r"\bKEY\s*=[^=]", js)) > 1:
        errors.append("KEY é atribuída mais de uma vez")
    for m in re.finditer(r"localStorage(?!\.(?:getItem|setItem)\(KEY\s*[,)])", js):
        line = js.count("\n", 0, m.start()) + 1
        errors.append("uso de localStorage fora de getItem/setItem(KEY) "
                      "(linha %d do script)" % line)
    save = re.search(r"\n  function save\(\) \{\n(.*?)\n  \}\n", js, re.S)
    if not save:
        errors.append("função save() não encontrada: a guarda de senhas não pôde rodar")
    else:
        for name in SECRET_NAMES:
            if re.search(r"\b%s\b" % name, save.group(1)):
                errors.append("save() referencia `%s`: senhas não podem ser persistidas" % name)
    return errors


def _declarations(block):
    return sorted(" ".join(d.split()) for d in block.split(";") if d.strip())


def check_theme(html):
    styles = STYLE_RE.findall(html)
    if len(styles) != 1:
        return ["sem <style> único para comparar os temas"]
    css = styles[0]
    media = re.search(
        r'@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*'
        r':root:not\(\[data-theme="light"\]\)\s*\{([^}]*)\}', css)
    forced = re.search(r':root\[data-theme="dark"\]\s*\{([^}]*)\}', css)
    if not media or not forced:
        return ["blocos da paleta escura não encontrados (@media e [data-theme=\"dark\"])"]
    a, b = _declarations(media.group(1)), _declarations(forced.group(1))
    if a != b:
        diff = sorted(set(a) ^ set(b))
        return ["as duas declarações da paleta escura divergem: " + "; ".join(diff)]
    return []


GUARDS = [
    ("structure", check_structure),
    ("syntax", check_syntax),
    ("csp", check_csp),
    ("random", check_random),
    ("network", check_network),
    ("urls", check_urls),
    ("storage", check_storage),
    ("theme", check_theme),
]


def run(html):
    """Devolve {nome da guarda: [erros]} só para as guardas que reprovaram."""
    failed = {}
    for name, guard in GUARDS:
        errors = guard(html)
        if errors:
            failed[name] = errors
    return failed


def fix(path):
    with open(path, encoding="utf-8", newline="") as f:
        html = f.read()
    js = inline_script(html)
    if js is None or len(CSP_RE.findall(html)) != 1:
        print("--fix precisa de exatamente 1 <script> e 1 <meta> de CSP", file=sys.stderr)
        return 1
    policy = CSP_TEMPLATE.format(hash=script_hash(js))
    new = CSP_RE.sub(
        lambda m: '<meta http-equiv="Content-Security-Policy" content="%s">' % policy, html)
    if new != html:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        print("CSP atualizada em %s" % path)
    else:
        print("CSP já estava em dia")
    return 0


def main(argv):
    args = [a for a in argv if a != "--fix"]
    path = args[0] if args else "index.html"
    if "--fix" in argv:
        return fix(path)
    with open(path, encoding="utf-8", newline="") as f:
        html = f.read()
    failed = run(html)
    for name, _ in GUARDS:
        if name in failed:
            print("FALHOU  %s" % name)
            for e in failed[name]:
                print("    " + e)
        else:
            print("ok      %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
