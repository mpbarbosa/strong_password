# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A password generator delivered as one self-contained file, `index.html` (inline CSS and JS, no dependencies beyond Google Fonts). The UI and the code comments are in Brazilian Portuguese; the README and commit messages are in English.

## Commands

There is no package manifest, linter or test suite, and nothing to build before opening the page. The `.gitignore` is the stock Node template and does not reflect any tooling.

To run it, open `index.html` in a browser or serve the directory statically:

```bash
python3 -m http.server 8000
```

The only script is `bin/build-artifact.sh`, which cuts `index.html` down to the fragment the Claude artifact host expects. It writes `dist/artifact.html` (gitignored, since it is derived), or to stdout with `-o -`:

```bash
bin/build-artifact.sh
```

## Concurrent sessions

More than one Claude session may write to this repository at the same time. **The conventions are in [`CONCORRENCIA.md`](CONCORRENCIA.md)** (in Portuguese, imported from a sibling repository) — read it before the first edit. What you need before you get there:

- A session that is going to write calls `EnterWorktree` first, before the first edit. Read-only sessions may stay in the main checkout, which is the merge target and is not edited directly.
- Live state — who holds which worktree right now — is in the ledger `.claude/worktrees/COORDENACAO.md` of the **root checkout**. It is gitignored and does not exist inside a worktree, so resolve it from the first line of `git worktree list`. Read it when choosing a task, and add your line when you create the worktree.
- Stage files by name, never `git add -A` or `git add .`, and never a bare `git stash`: the working tree and the stash stack are shared.
- `git push origin main` needs the user's OK in this repository, always with the remote and ref spelled out, and never `--force`.

## Things to know before editing

**`index.html` began as a Claude artifact page fragment.** The `claude:viewport-fit-sides` meta tag is a leftover of that format, where the host supplies the document skeleton. The file is now a complete standalone document (doctype, `lang="pt-BR"`, charset, viewport), but its contents are deliberately not indented under `<head>`/`<body>`. The page is still published as an artifact as well, and that format has not changed: `bin/build-artifact.sh` drops the doctype, `<html>`, `<head>`, `<body>` and the charset/viewport metas — the host supplies them — and keeps everything else, including that meta tag. Republishing means running it and publishing `dist/artifact.html`, never `index.html`.

**Privacy is the product's stated promise.** The page tells the user nothing leaves the device and that passwords are never stored. Concretely:

- Randomness comes only from `crypto.getRandomValues` via `randInt()`, which uses rejection sampling to avoid modulo bias. Never introduce `Math.random` or a plain `% n`.
- `localStorage` (key `senha-forte-prefs`) holds preferences only. Generated passwords live in the in-memory `current` string and `history` array (last 5) and must not be persisted or sent anywhere.
- No network calls other than the font stylesheet.

**Generation rules interact, and they degrade rather than fail** (all in `generate()`):

- "Sem caracteres repetidos" only applies when the length fits the pool (`len <= pool.length`); otherwise it is ignored, its label gets the `.off` class and the `#norepNote` hint is shown.
- "Ao menos um de cada tipo" is silently skipped when there are more active sets than characters requested. When it applies, one character per set is taken first and the result is Fisher-Yates shuffled so positions are not fixed.
- `AMBIGUOUS` removes far more than the `l 1 I O 0` shown in the label (also `5 S 2 Z 8 B` and several punctuation marks), which shrinks the pool and therefore the reported entropy.

**The strength readout is an estimate.** Entropy is `len × log2(pool size)` and ignores the no-repeat and one-of-each constraints. Thresholds are 45 / 65 / 90 bits (Fraca, Razoável, Forte, Excelente), the bar fills at 110 bits, and `crackTime()` assumes 10¹² guesses per second over half the keyspace. Its output is hand-formatted Portuguese (units, plurals, decimal comma), so changes there need pt-BR care.

**History depends on why a password was generated.** `generate(tweak)` is called with `true` from parameter changes and `false` from the "Gerar outra" button and on load. A tweak overwrites the top history entry instead of pushing a new one, unless that password was copied (`topKept`), so dragging the length slider does not flood the "Anteriores" list. New callers must pass the right flag.

**Theme tokens are duplicated.** The dark palette is declared twice — under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. Change both or the themes drift.

**Code style.** The script is a single IIFE in ES5 style (`var`, function expressions, no arrow functions or template literals). DOM nodes are looked up once into the `el` map by id — a new control needs its id added to that list, and to the `save()`/`load()` and change-listener key lists if it is a persisted option. Button text lives in an inner `<span>` next to an SVG icon; change it through `setLabel()`/`flashLabel()`, not `textContent` on the button.
