#!/usr/bin/env python3
"""Prova por mutação que cada guarda de check.py reprova o que deveria.

Cada caso parte do index.html real, introduz UMA violação e exige que falhe
exatamente o conjunto de guardas esperado. Casos com conjunto vazio são o
limite oposto: edições legítimas que não podem ser reprovadas.

Uso: python3 .github/scripts/test_check.py [index.html]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check  # noqa: E402

SCRIPT_END = "\n})();\n</script>"


def swap(html, old, new, count=1):
    """Substitui e exige que a âncora exista: mutação que não se aplica não testa nada."""
    if html.count(old) < count:
        raise LookupError("âncora não encontrada no index.html: %r" % old)
    return html.replace(old, new, count)


def rehash(html):
    """Põe o hash certo na CSP, para a mutação do script chegar à guarda testada."""
    policy = check.CSP_TEMPLATE.format(hash=check.script_hash(check.inline_script(html)))
    return check.CSP_RE.sub(
        lambda m: '<meta http-equiv="Content-Security-Policy" content="%s">' % policy, html)


def js(statement):
    """Mutação: acrescenta uma instrução ao fim do script, com a CSP em dia."""
    return lambda h: rehash(swap(h, SCRIPT_END, "\n  " + statement + SCRIPT_END))


def csp_meta(html):
    return check.CSP_RE.search(html).group(0)


def move_csp_after_link(html):
    meta = csp_meta(html)
    html = swap(html, meta + "\n", "")
    return swap(html, "<style>", meta + "\n<style>")


def second_dark_block(old, new):
    def mutate(html):
        head, sep, tail = html.partition(':root[data-theme="dark"] {')
        if not sep:
            raise LookupError("bloco [data-theme=dark] não encontrado")
        return head + sep + swap(tail, old, new)
    return mutate


def tag(html, start):
    """A linha inteira da tag que começa com `start`, com a quebra de linha."""
    m = re.search(r"^%s[^\n]*\n" % re.escape(start), html, re.M)
    if not m:
        raise LookupError("tag não encontrada no index.html: %r" % start)
    return m.group(0)


def drop(start):
    return lambda h: swap(h, tag(h, start), "")


def twice(start):
    return lambda h: swap(h, tag(h, start), tag(h, start) * 2)


def attr(start, name, value):
    """Mutação: troca o valor de um atributo na tag que começa com `start`."""
    def mutate(html):
        line = tag(html, start)
        new = re.sub(r'%s="[^"]*"' % name, lambda m: '%s="%s"' % (name, value), line, count=1)
        if new == line:
            raise LookupError("atributo %s não encontrado em %r" % (name, start))
        return swap(html, line, new)
    return mutate


def then(*mutations):
    def mutate(html):
        for m in mutations:
            html = m(html)
        return html
    return mutate


def head_line(line):
    """Mutação: acrescenta uma linha ao <head>, logo antes do <title>."""
    return lambda h: swap(h, "<title>", line + "\n<title>")


def title(text):
    return lambda h: swap(h, tag(h, "<title>"), "<title>%s</title>\n" % text)


def description(text):
    return then(attr('<meta name="description"', "content", text),
                attr('<meta property="og:description"', "content", text))


CASES = [
    # --- limite permissivo: nada disto pode ser reprovado -------------------
    ("página atual passa", lambda h: h, set()),
    ("comentário novo no script, CSP em dia", js("/* nota */"), set()),
    ("paleta escura reformatada sem mudar valores",
     second_dark_block("--bg: #0f1115;", "--bg:   #0f1115 ;"), set()),
    ("descrição reescrita nos dois lugares",
     description("Gerador de senhas aleatórias que roda no navegador e não envia nada a servidor algum."),
     set()),
    ("título no limite de tamanho", title("x" * check.TITLE_MAX), set()),
    ("descrição no limite inferior", description("x" * check.DESCRIPTION_RANGE[0]), set()),
    ("descrição no limite superior", description("x" * check.DESCRIPTION_RANGE[1]), set()),
    ("meta robots que permite indexar",
     head_line('<meta name="robots" content="index, follow">'), set()),

    # --- structure ----------------------------------------------------------
    ("handler inline", lambda h: swap(h, '<button', '<button onclick="x()"'), {"structure"}),
    ("script externo",
     lambda h: swap(h, "</body>", '<script src="x.js"></script>\n</body>'),
     {"structure", "syntax", "csp", "storage"}),

    # --- syntax -------------------------------------------------------------
    ("erro de sintaxe", js("var = ;"), {"syntax"}),

    # --- csp ----------------------------------------------------------------
    ("script alterado sem atualizar o hash",
     lambda h: swap(h, SCRIPT_END, "\n  var zz = 1;" + SCRIPT_END), {"csp"}),
    ("default-src afrouxado",
     lambda h: swap(h, "default-src 'none'", "default-src *"), {"csp"}),
    ("connect-src liberado",
     lambda h: swap(h, "; base-uri 'none'", "; connect-src *; base-uri 'none'"), {"csp"}),
    ("script-src com unsafe-inline",
     lambda h: swap(h, "script-src 'sha256-", "script-src 'unsafe-inline' 'sha256-"), {"csp"}),
    ("meta da CSP depois do <link>", move_csp_after_link, {"csp"}),
    ("meta da CSP removida", lambda h: swap(h, csp_meta(h) + "\n", ""), {"csp"}),

    # --- random -------------------------------------------------------------
    ("Math.random no lugar de crypto",
     lambda h: rehash(swap(h, "crypto.getRandomValues(buf); v = buf[0];",
                           "v = Math.floor(Math.random() * 4294967296);")),
     {"random"}),

    # --- network ------------------------------------------------------------
    ("fetch", js('fetch("/x", { method: "POST", body: current });'), {"network"}),
    ("XMLHttpRequest", js("new XMLHttpRequest();"), {"network"}),
    ("sendBeacon", js('navigator.sendBeacon("/x", current);'), {"network"}),
    ("WebSocket", js('new WebSocket("/x");'), {"network"}),
    ("EventSource", js('new EventSource("/x");'), {"network"}),
    ("new Image", js('new Image().src = "/x?p=" + current;'), {"network"}),
    ("import dinâmico", js('import("/x.js");'), {"network"}),
    ("navegação com a senha", js('location.href = "/?p=" + current;'), {"network"}),
    ("window.open", js('window.open("/?p=" + current);'), {"network"}),
    ("RTCPeerConnection", js("new RTCPeerConnection();"), {"network"}),
    ("serviceWorker", js('navigator.serviceWorker.register("/sw.js");'), {"network"}),
    ("importScripts", js('importScripts("/x.js");'), {"network"}),

    # --- urls ---------------------------------------------------------------
    ("imagem de outro domínio",
     lambda h: swap(h, "</body>", '<img src="https://evil.example/p.gif" alt="">\n</body>'),
     {"urls"}),
    ("folha de estilo protocol-relative",
     lambda h: swap(h, "<style>", '<link rel="stylesheet" href="//cdn.example.com/x.css">\n<style>'),
     {"urls"}),
    ("URL externa dentro do script", js('var u = "https://evil.example.com/";'), {"urls"}),
    ("host parecido com o permitido",
     lambda h: swap(h, "https://fonts.gstatic.com\" crossorigin",
                    "https://fonts.gstatic.com.evil.example\" crossorigin"),
     {"urls"}),
    # O endereço do próprio site só vale nas duas tags que o declaram.
    ("endereço do site dentro do script", js('var u = "%s";' % check.SITE_URL), {"urls"}),
    ("imagem servida do próprio site",
     lambda h: swap(h, "</body>", '<img src="%sp.gif" alt="">\n</body>' % check.SITE_URL),
     {"urls"}),

    # --- storage ------------------------------------------------------------
    ("senha gravada em outra chave", js('localStorage.setItem("senha", current);'), {"storage"}),
    ("localStorage por índice", js('localStorage["x"] = current;'), {"storage"}),
    ("sessionStorage", js("sessionStorage.setItem(KEY, current);"), {"storage"}),
    ("cookie", js('document.cookie = "p=" + current;'), {"storage"}),
    ("indexedDB", js('indexedDB.open("x");'), {"storage"}),
    ("Cache API", js('caches.open("x");'), {"storage"}),
    ("chave de preferências trocada",
     lambda h: rehash(swap(h, 'var KEY = "senha-forte-prefs";', 'var KEY = "outra";')),
     {"storage"}),
    ("KEY reatribuída", js('KEY = "outra";'), {"storage"}),
    ("senha atual dentro de save()",
     lambda h: rehash(swap(h, "len: el.len.value, up:", "senha: current, len: el.len.value, up:")),
     {"storage"}),
    ("histórico dentro de save()",
     lambda h: rehash(swap(h, "len: el.len.value, up:", "h: history, len: el.len.value, up:")),
     {"storage"}),

    # --- theme --------------------------------------------------------------
    ("cor divergente no segundo bloco",
     second_dark_block("--accent: #9db0ff;", "--accent: #000000;"), {"theme"}),
    ("declaração a menos no primeiro bloco",
     lambda h: swap(h, "      --sym: #f0a268;\n", ""), {"theme"}),

    # --- seo ----------------------------------------------------------------
    # Cada caso aciona UMA recusa da guarda; os valores relativos (href="/")
    # chegam a ela sem esbarrar antes na guarda `urls`.
    ("lang removido", lambda h: swap(h, '<html lang="pt-BR">', "<html>"), {"seo"}),
    ("título removido", drop("<title>"), {"seo"}),
    ("título vazio", title(" "), {"seo"}),
    ("título acima do limite", title("x" * (check.TITLE_MAX + 1)), {"seo"}),
    ("segundo h1", twice("    <h1>"), {"seo"}),
    ("descrição removida", drop('<meta name="description"'), {"seo"}),
    ("descrição abaixo do limite",
     description("x" * (check.DESCRIPTION_RANGE[0] - 1)), {"seo"}),
    ("descrição acima do limite",
     description("x" * (check.DESCRIPTION_RANGE[1] + 1)), {"seo"}),
    ("og:description diverge da descrição",
     attr('<meta property="og:description"', "content", "Outra descrição da mesma página."),
     {"seo"}),
    ("og:title sem conteúdo", attr('<meta property="og:title"', "content", ""), {"seo"}),
    ("og:locale duplicado", twice('<meta property="og:locale"'), {"seo"}),
    ("twitter:card removido", drop('<meta name="twitter:card"'), {"seo"}),
    ("canonical removido", drop('<link rel="canonical"'), {"seo"}),
    ("canonical relativo", attr('<link rel="canonical"', "href", "/"), {"seo"}),
    ("og:url diferente do canônico", attr('<meta property="og:url"', "content", "/outra/"),
     {"seo"}),
    ("noindex", head_line('<meta name="robots" content="noindex, follow">'), {"seo"}),
    ("googlebot none", head_line('<meta name="googlebot" content="none">'), {"seo"}),
    # Estes dois também quebram a exceção da guarda `urls`, e têm de quebrar.
    ("canonical para outro domínio",
     attr('<link rel="canonical"', "href", "https://evil.example/"), {"urls", "seo"}),
    ("segunda tag canonical", twice('<link rel="canonical"'), {"urls", "seo"}),
]


def main(argv):
    path = argv[0] if argv else "index.html"
    with open(path, encoding="utf-8", newline="") as f:
        base = f.read()
    failures = 0
    for name, mutate, expected in CASES:
        try:
            got = set(check.run(mutate(base)))
        except LookupError as e:
            got = "mutação não aplicada: %s" % e
        if got == expected:
            print("PASS  %s" % name)
        else:
            failures += 1
            print("FAIL  %s\n        esperado %s, obtido %s"
                  % (name, sorted(expected), sorted(got) if isinstance(got, set) else got))
    print("%d casos, %d falhas" % (len(CASES), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
