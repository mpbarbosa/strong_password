#!/bin/sh
# Recorta index.html para o formato de artifact do Claude.
#
# O arquivo do repositório é um documento completo (doctype, <html>, <head>,
# <body>). O host do artifact fornece esse esqueleto por conta própria, mais
# charset, viewport e a própria política de segurança, então publicar o
# documento inteiro aninharia um dentro do outro. Este script remove exatamente
# essas linhas e deixa o resto intacto — <title>, <meta name="claude:...">,
# <link>, <style> e o conteúdo.
#
# As tags de SEO também saem: descrição, canonical, Open Graph e Twitter card
# falam com buscadores sobre a página publicada no GitHub Pages, e o artifact
# é outra publicação, privada. Pelo mesmo motivo o <title> volta a ser só o
# nome do site (lido de og:site_name): o título longo é para o resultado de
# busca, e o artifact é nomeado pelo <title>.
#
#   bin/build-artifact.sh              # gera dist/artifact.html
#   bin/build-artifact.sh -o -         # escreve na saída padrão
#   bin/build-artifact.sh -o /tmp/a.html index.html
#
# dist/ é ignorado pelo git: a saída é derivada, não se commita.

set -eu

src=""
out=""

while [ $# -gt 0 ]; do
  case "$1" in
    -o) [ $# -ge 2 ] || { echo "build-artifact: -o exige um caminho" >&2; exit 2; }
        out="$2"; shift 2 ;;
    -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "build-artifact: opção desconhecida: $1" >&2; exit 2 ;;
    *)  [ -z "$src" ] || { echo "build-artifact: só um arquivo de entrada" >&2; exit 2; }
        src="$1"; shift ;;
  esac
done

raiz=$(cd "$(dirname "$0")/.." && pwd)
[ -n "$src" ] || src="$raiz/index.html"
[ -n "$out" ] || out="$raiz/dist/artifact.html"
[ -f "$src" ] || { echo "build-artifact: não encontrei $src" >&2; exit 1; }

# Casa só as linhas que são a tag inteira, então <header> e <meta name="claude:...">
# sobrevivem. tolower() porque o doctype costuma vir em maiúsculas.
recorta() {
  awk '
    { l = tolower($0); sub(/^[ \t]+/, "", l); sub(/[ \t]+$/, "", l) }
    l ~ /^<!doctype[^>]*>$/            { next }
    l ~ /^<html([ >]|$)/ || l == "</html>" { next }
    l ~ /^<head([ >]|$)/ || l == "</head>" { next }
    l ~ /^<body([ >]|$)/ || l == "</body>" { next }
    l ~ /^<meta[^>]*charset/           { next }
    l ~ /^<meta[^>]*name="viewport"/   { next }
    # A CSP da página vale para o arquivo standalone. Dentro do artifact ela
    # ficaria fora do <head> (ignorada) ou valeria contra o host, cujo runtime
    # ela não conhece — e o host já impõe a própria política.
    l ~ /^<meta[^>]*http-equiv=[^>]*content-security-policy/ { next }
    # SEO: vale para a página publicada, não para o artifact. O nome do site
    # é guardado antes de a linha sair, para virar o <title> do recorte.
    l ~ /^<meta[^>]*property="og:site_name"/ {
      if (match($0, /content="[^"]*"/)) nome = substr($0, RSTART + 9, RLENGTH - 10)
      next
    }
    l ~ /^<meta[^>]*name="description"/ { next }
    l ~ /^<link[^>]*rel="canonical"/    { next }
    l ~ /^<meta[^>]*property="og:/      { next }
    l ~ /^<meta[^>]*name="twitter:/     { next }
    l ~ /^<title>.*<\/title>$/          { titulo = n + 0; tem_titulo = 1 }
    { linhas[n++] = $0 }
    END {
      if (nome != "" && tem_titulo) linhas[titulo] = "<title>" nome "</title>"
      inicio = 0; fim = n - 1
      while (inicio <= fim && linhas[inicio] ~ /^[ \t]*$/) inicio++
      while (fim >= inicio && linhas[fim] ~ /^[ \t]*$/) fim--
      for (i = inicio; i <= fim; i++) print linhas[i]
    }
  ' "$src"
}

if [ "$out" = "-" ]; then
  recorta
  exit 0
fi

mkdir -p "$(dirname "$out")"
recorta > "$out"

# Confere o que saiu: sem tags de documento, com <title>, não vazio.
sobrou=$(awk '
  { l = tolower($0); sub(/^[ \t]+/, "", l); sub(/[ \t]+$/, "", l) }
  l ~ /^<!doctype/ || l ~ /^<\/?html([ >]|$)/ || l ~ /^<\/?head([ >]|$)/ || l ~ /^<\/?body([ >]|$)/ \
    || l ~ /^<meta[^>]*http-equiv=[^>]*content-security-policy/ \
    { print FILENAME ":" FNR ": " $0 }
' "$out")

if [ -n "$sobrou" ]; then
  echo "build-artifact: sobraram tags de documento no recorte:" >&2
  echo "$sobrou" >&2
  exit 1
fi
if ! grep -qi '<title>' "$out"; then
  echo "build-artifact: o recorte ficou sem <title> — o artifact precisa dele" >&2
  exit 1
fi
if [ ! -s "$out" ]; then
  echo "build-artifact: o recorte ficou vazio" >&2
  exit 1
fi

printf '%s — %s linhas, %s bytes\n' "$out" "$(wc -l < "$out" | tr -d ' ')" "$(wc -c < "$out" | tr -d ' ')" >&2
