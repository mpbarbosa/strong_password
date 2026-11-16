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

# O endereço público da página. Só pode aparecer nestas duas tags, escritas
# exatamente assim: elas declaram o endereço aos buscadores e o navegador não
# busca nenhuma das duas. Em qualquer outro lugar a guarda `urls` o reprova.
SITE_URL = "https://mpbarbosa.github.io/strong_password/"
SELF_REFERENCES = (
    '<link rel="canonical" href="%s">' % SITE_URL,
    '<meta property="og:url" content="%s">' % SITE_URL,
)

# O que os buscadores mostram: acima disto o resultado sai cortado.
TITLE_MAX = 60
DESCRIPTION_RANGE = (70, 160)
# Metas que precisam existir uma vez só e com conteúdo.
SEO_METAS = ("description", "og:type", "og:site_name", "og:locale", "og:title",
             "og:description", "og:url", "twitter:card")

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
    # Uma vez cada: uma segunda cópia da tag sobra no texto e é reprovada.
    for ref in SELF_REFERENCES:
        html = html.replace(ref, "", 1)
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


class _Head(HTMLParser):
    """Recolhe o que um buscador lê: lang, <title>, metas, canonical e <h1>."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.langs = []
        self.titles = []
        self.metas = {}
        self.canonicals = []
        self.h1 = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.langs.append(a.get("lang"))
        elif tag == "title":
            self._in_title = True
            self.titles.append("")
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.metas.setdefault(key.lower(), []).append(a.get("content") or "")
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonicals.append(a.get("href") or "")
        elif tag == "h1":
            self.h1 += 1

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.titles[-1] += data


def check_seo(html):
    head = _Head()
    head.feed(html)
    errors = []
    if head.langs != ["pt-BR"]:
        errors.append('esperado <html lang="pt-BR">')
    if len(head.titles) != 1 or not head.titles[0].strip():
        errors.append("esperado exatamente 1 <title> com texto")
    elif len(head.titles[0].strip()) > TITLE_MAX:
        errors.append("<title> com %d caracteres: o buscador corta acima de %d"
                      % (len(head.titles[0].strip()), TITLE_MAX))
    if head.h1 != 1:
        errors.append("esperado exatamente 1 <h1>, encontrados %d" % head.h1)
    for key in SEO_METAS:
        values = head.metas.get(key, [])
        if len(values) != 1:
            errors.append("esperada exatamente 1 meta %s, encontradas %d" % (key, len(values)))
        elif not values[0].strip():
            errors.append("meta %s sem conteúdo" % key)
    description = head.metas.get("description", [])
    if len(description) == 1 and description[0].strip():
        low, high = DESCRIPTION_RANGE
        if not low <= len(description[0]) <= high:
            errors.append("meta description com %d caracteres: o esperado é de %d a %d"
                          % (len(description[0]), low, high))
        # O mesmo texto em dois lugares: quem muda um e esquece o outro deixa
        # o buscador e as redes sociais descrevendo a página de formas diferentes.
        if head.metas.get("og:description", []) not in ([], description):
            errors.append("og:description diverge da meta description")
    if head.canonicals != [SITE_URL]:
        errors.append("esperado exatamente 1 <link rel=\"canonical\"> para %s (tem: %s)"
                      % (SITE_URL, ", ".join(head.canonicals) or "nenhum"))
    if head.metas.get("og:url", []) not in ([], [SITE_URL]):
        errors.append("og:url diverge do endereço canônico %s" % SITE_URL)
    for key in ("robots", "googlebot"):
        for value in head.metas.get(key, []):
            if re.search(r"\b(noindex|none)\b", value, re.I):
                errors.append('meta %s="%s" tira a página dos buscadores' % (key, value))
    return errors


GUARDS = [
    ("structure", check_structure),
    ("syntax", check_syntax),
    ("csp", check_csp),
    ("random", check_random),
    ("network", check_network),
    ("urls", check_urls),
    ("storage", check_storage),
    ("theme", check_theme),
    ("seo", check_seo),
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
