# Sessões concorrentes — convenções deste repo

**Importado do repo `linkedin` em 2026-11-15** (o `CONCORRENCIA.md` de lá), onde as regras nasceram de
dano medido. **As medições citadas aqui são de lá, não daqui** — este repo ainda não produziu incidente
próprio. O que foi trazido é o que vale para **qualquer** repo escrito por mais de uma sessão; o que era
específico de lá (numeração de seções, contador de envios, tabela de índice, n8n, saldo de API, geração
de CV, o painel de guardas) ficou de fora. **O que foi adaptado ou escrito para este repo, em vez de
copiado, está marcado com 🏠.** Os trechos copiados ficaram como estavam: a primeira pessoa é da sessão
que mediu, e *"aqui"* / *"este repo"* dentro deles é o `linkedin`.

> 🗂️ **Estado vivo — quem está com qual worktree agora — NÃO fica aqui.** Fica no ledger
> `.claude/worktrees/COORDENACAO.md` **do checkout raiz**, que é **gitignored** e existe **só lá**.
> ⚠️ **De dentro de um worktree esse caminho não existe** — resolva-o a partir do checkout raiz (a
> primeira linha de `git worktree list`), ou vai concluir que foi apagado. **Este arquivo é a
> convenção; o ledger é o estado.**

---

## Por que a regra existe

No `linkedin`, várias sessões do Claude escrevem ao mesmo tempo: **42 commits em 2026-09-30, 22 deles
tocando o mesmo arquivo**. Três sessões se danificaram naquele dia — uma **truncou um arquivo a 0 bytes**
e o commit passou, e duas **engoliram as edições de uma terceira** em commits sem relação.

**Qualquer sessão que vá escrever neste repo chama `EnterWorktree` primeiro**, antes da primeira edição,
não depois. Sessão só de leitura (responder pergunta, abrir o `index.html` no navegador) pode ficar no
checkout principal.

- 🏠 **O ref base é `head`, não `origin/main`** — fixado em
  [`.claude/settings.json`](.claude/settings.json) (`worktree.baseRef`), como no `linkedin`. O `origin`
  fica rotineiramente vários commits atrás, e o default do harness (`fresh`) tira o worktree de
  `origin/<branch padrão>`: ele começaria de um repo velho, **em silêncio**.
  ⚠️ **O arquivo foi criado em 2026-11-15 e o efeito ainda não foi medido aqui.** Uma sessão aberta
  antes disso pode não o ter carregado, e `head` protege a **criação** do worktree, não os minutos
  seguintes. ⇒ ao entrar no worktree, compare `git log --oneline -1` com o `main` local e, se estiver
  atrás, `git merge main` antes da primeira edição.
- **O worktree envelhece enquanto você trabalha — e ref base certo não protege disso.** Medido no
  `linkedin` em 2026-10-05: um worktree criado às **20:55** estava **8 commits atrás** às 21:1x, porque
  duas outras sessões aterraram no intervalo. ⇒ **antes de escrever depois de um trecho longo,
  `git merge main` para dentro do worktree.** Quanto mais tempo entre criar o worktree e escrever, mais
  provável a colisão.
- **Nomeie o worktree pelo trabalho**: `EnterWorktree(name: "frase-secreta")`, `"tema-contraste"`. O
  nome vira o branch, e é o que o usuário vê na lista de sessões.
- **Ninguém edita o checkout principal.** Ele é o alvo do merge: se estiver sujo, nenhuma sessão aterra.
- **Registre o worktree no ledger ao criar e ao adotar.** Um worktree limpo e quieto é
  **indistinguível de um já mesclado** por qualquer comando — e worktrees já foram varridos por essa
  leitura. Se você adotar o de outra sessão, **renomeie para o branch que você pôs nele**.

## 🏠 O ponto de colisão deste repo — derivado da estrutura, não medido

Este repo é, por desenho, **um arquivo só**: `index.html`, com CSS e JS inline (ver
[`CLAUDE.md`](CLAUDE.md)). No `linkedin` a defesa contra colisão foi dividir o registro em um arquivo
por unidade; **aqui essa defesa não existe e não deve existir** — o arquivo único é o produto.

⇒ **Duas sessões que escrevem ao mesmo tempo tocam, quase sempre, o mesmo arquivo.** O git mescla limpo
quando os trechos são distintos e conflita quando coincidem — e ⚠️ **mescla limpa não é mescla certa**:
a paleta escura é declarada **duas vezes** (`CLAUDE.md`, *Theme tokens are duplicated*), e uma sessão
que mude uma cópia enquanto outra muda a outra passa sem conflito e deixa os temas divergirem.

- **Diga na coluna de escopo do ledger QUAL parte do `index.html`** você vai mexer (CSS/tema, marcação,
  `generate()`, leitura de força, histórico), não só o nome do arquivo.
- **Depois de trazer o `main` e antes de aterrar, abra a página.** Não há suíte nem linter aqui:
  a única conferência é o navegador, e ela tem de ser feita **depois** do merge, porque o que entra no
  merge é de outras sessões.

## Aterrar o trabalho — nesta ordem, porque o atalho é bloqueado

⚠️ **Sessão em worktree não pode tocar no checkout principal.** O harness recusa
`git -C <checkout-principal> …` e **qualquer forma de git que ele não consiga verificar que fica dentro
do worktree** — inclusive heredoc longo, `$(...)` e pipeline complexo (verificado no `linkedin` em
2026-09-30 e de novo em 2026-10-01). Então o merge é o último passo, não algo feito de dentro:

0. 🏠 **Traga o `main` para dentro do worktree (`git merge main`) e confira a página DEPOIS disso**,
   não antes. No `linkedin` este passo é um painel de guardas que não existe aqui; o que foi trazido é
   a ordem — o que entra no merge é de outras sessões, e é aí que a divergência aparece.
1. Commite no worktree como de hábito.
2. `ExitWorktree(action: "keep")` — a sessão volta para o checkout raiz e o isolamento cai. **Keep, não
   remove**: o branch ainda tem a única cópia do trabalho.
3. Do checkout principal: `git merge --no-ff <branch>` (o branch é `worktree-<nome>`).
4. Limpe: `git worktree remove .claude/worktrees/<nome>` e depois `git branch -d <branch>`.
   🏠 No `linkedin` o comando leva `--force`, por causa de um symlink não rastreado que este repo não
   tem. **Se o git recusar aqui, leia o motivo antes de forçar** — recusa de `worktree remove` e de
   `branch -d` é o git dizendo que há trabalho sem cópia.
5. 🏠 **Marque a linha do worktree no ledger como `⛔ ATERRADO` — não apague.** O texto original mandava
   apagar; a medição de 2026-11-07, mais abaixo, mostrou que essa linha é o único registro de
   `branch → sessão` que sobra depois que a worktree morre.
6. 🏠 **`push origin main` — só com o OK dele neste repo.** No `linkedin` há decisão dele (2026-10-22)
   de empurrar o `main` ao fim de **cada** aterragem, sem perguntar. **Essa autorização não foi
   trazida:** ela é de um repo e não viaja. O que vale em qualquer lugar é a forma.
   ⚠️ **O comando é `push origin main`, com o remoto e a ref escritos** — nunca `push` nu, que consulta
   o `HEAD` e **já publicou o branch de OUTRA sessão saindo 0 com linha de sucesso** (§8 da skill
   `commit-in-shared-checkout`).
   ⛔ **Nunca `--force`:** é a única falha deste documento que nenhum comando posterior desfaz.

   ⚠️ **Se o push responder `Everything up-to-date` sem enviar objeto nenhum, outra sessão empurrou o
   seu merge no intervalo.** Isso **não** é falso positivo: a linha é contra o SERVIDOR, logo prova que
   o `origin/main` já contém o `main` local, e com ele os seus commits. 🔑 **O que a linha NÃO diz é
   QUEM empurrou** ⇒ ⛔ **não relate *"empurrei N objetos"* quando o comando não enviou nada**; relate
   que **o trabalho está no servidor**, que é o que foi verificado. Para ver o conteúdo em vez do
   comando: `rev-list --left-right --count origin/main...main` (quer `0  0`) e
   `cat-file -e origin/main:<arquivo que você criou>`.
   📌 **A pergunta certa é *"o meu commit está lá?"*, não *"o push passou?"***

### 🩸 O commit pode sair `0`, imprimir o resumo e gravar objetos de ZERO BYTE

**Medido 2026-10-22, `n = 1`, causa NÃO estabelecida.** O commit `4a05ec7` saiu **0**, o
`log --oneline -3` imprimiu a linha dele, e os **cinco** objetos — o commit, a árvore e os três
blobs — estavam no disco com **0 byte**, todos com o mesmo mtime (`12:10:28`). Nada mais no
repositório foi atingido (`fsck`).

🔑 **Isto é um andar ABAIXO do *"commit não é backup"* da §8 da skill `commit-in-shared-checkout`.**
Lá o commit existe e o `push` é que engana; aqui **o commit não existe** e as duas leituras seguintes
dizem que existe. ⛔ **Logo `log --oneline -1 <branch>` depois de commitar NÃO testa isto** — foi
exatamente o comando que rodei, e ele imprimiu o commit morto.

⏱️ **O repo só acusou 12 minutos depois**, no `status` da verificação de encerramento:
`fatal: bad object HEAD`. ⇒ 📌 **entre o commit e a próxima leitura de objeto, o trabalho parece
salvo e não está** — e nesse intervalo um `worktree remove` levaria tudo.

✅ **A defesa é a que já está escrita, cumprida CEDO: empurrar.** O `push` precisa LER os objetos
para empacotá-los, logo ele falha alto onde o `log` cala. ⇒ **não deixe o push só para o passo 6:
quanto mais tempo entre o commit e a primeira leitura real dos objetos, maior a janela.**
⚠️ **Isto é inferência sobre o mecanismo do push, não medição desta ocorrência** — eu não cheguei a
empurrar o `4a05ec7`.

#### A recuperação, na ordem que FUNCIONA

🔻 **A ordem que eu prescrevi primeiro estava errada, e falhou na hora:** mandei resetar e depois
apagar. O `reset` morre com `fatal: unable to read <sha>`, porque o **`cache-tree` do índice**
referencia os objetos mortos. As peças estavam certas e a **dependência entre elas**, não.

1. **apague os arquivos de 0 byte** — `find .git/objects -type f -empty` os lista;
2. o `reset` **ainda falha**, pelo índice ⇒ **mova o índice do worktree para fora**
   (`.git/worktrees/<nome>/index`);
3. `update-ref refs/heads/<branch> <commit bom>` — mexe só no ref, não lê o índice;
4. `reset --mixed` reconstrói o índice e devolve os arquivos como **modificados**, com o
   conteúdo intacto — **o working tree nunca foi tocado**, e é ele que salva o trabalho.

🔴 **E apagar ANTES do recommit não é higiene, é obrigatório:** o conteúdo é o mesmo, logo os blobs
novos têm **exatamente os mesmos SHAs**. Com os arquivos vazios no lugar, o git vê "objeto já
existe" e **não reescreve** ⇒ **a corrupção sobrevive ao conserto, em silêncio.**

🧪 **Conferido depois:** `fsck` limpo, 0 objetos vazios, e os quatro SHAs de conteúdo voltaram a ser
`blob`/`tree` válidos — recriados pelo recommit. Só o commit morto não voltou, que é o certo.
⚠️ **E o comando de limpeza VENCE:** aquele `rm` era inofensivo às 12:24 e **destrutivo às 12:27**,
quando os mesmos SHAs já eram objetos de que o `main` dependia. **Não guarde essa linha para depois.**

---

### 🗂️ O ledger é REGISTRO, não aviso — e isso tem custo medido

**No `linkedin`, 2026-10-22:** duas sessões mediram **o mesmo** achado em paralelo, sem saber uma da
outra, e gastaram **a mesma meia hora**. Uma só viu a linha da outra **ao aterrar**; a outra só viu
**ao conflitar**.
✅ **O git fez o que devia:** conflito em **seis** arquivos em vez de duplicata silenciosa — *prefira o
conflito barulhento*.
📌 **Mas o ledger só evita o retrabalho se for lido ANTES de começar**, e nenhuma das duas o leu.
⇒ **leia o ledger ao ESCOLHER a tarefa, não ao registrar o worktree.**

### 🕵️ O git NÃO responde *"qual sessão fez X"* — medido no `linkedin` em 2026-11-07

Custou **quatro atribuições erradas entre três sessões** numa noite: um bloco foi atribuído, por
escrito, a uma sessão que naquele dia só havia **lido** o repo — e a "perda" que motivou o resgate
**não existia**; só passou a existir quando a sessão que a denunciou reescreveu a seção por cima.
⛔ **Antes de reescrever uma seção inteira, `grep` o que você está prestes a sobrescrever.**

| Candidato | O que dá |
|---|---|
| `git log --author` | **200 de 200** commits recentes são do mesmo autor ⇒ **discrimina zero** |
| o nome do branch | não carrega quem o criou; e **todas** as sessões leem os branches das outras |
| a mensagem de commit | **56 de 60 (93%)** não nomeiam worktree nem branch |
| a lista de worktrees | diz quem está **com** uma worktree **agora**; ausência **não prova** não-autoria, porque se pode commitar do checkout principal |
| o ledger | **é o único que responde** — worktree + branch + descrição |

- 🔑 **O que falta no git não é o BRANCH: é o mapa `branch → sessão`.** Nome de branch descreve o
  **trabalho**; nenhuma convenção de mensagem diz **qual sessão** o criou. ⇒ as linhas `⛔ ATERRADO` do
  ledger **são essa tabela**, e é por isso que apagá-las e não escrevê-las têm o **mesmo** efeito.
  ⚠️ O ledger é gitignored: **resolve o caso e morre no clone.**
- 💡 **Nomeie a própria worktree no corpo do commit.** Custa uma linha e sobrevive no git para sempre.
  É a guarda do caminho **local** (o `merge --no-ff` do passo 3), em que o nome do branch se perde se
  nenhum corpo o citar; onde se aterra por PR, o GitHub já o grava na mensagem do merge. ⚠️ Lá era
  prática de **uma** sessão só ⇒ não é evidência de que funciona para as outras, e ⛔ **não substitui o
  ledger**, que é o que diz *quem está escrevendo agora*.
- 📌 ***"Qual sessão fez X"* se PERGUNTA, não se deduz** — e, se for preciso deduzir, o que se afirma é
  o **trabalho** (branch + horário + diff), nunca o **autor**. 🔑 **Atribuição errada não é erro
  barato: ela acusa alguém.**
- 📌 **Declare a ref ao medir.** `git log` sem ref mede onde você está parado, não o repositório;
  `git fetch` move a ref remota e **não** move a sua. Lá, no mesmo minuto, `git log --grep=<x>` devolveu
  **8** e `git log origin/main --grep=<x>` devolveu **13**.
- ⚖️ **Autocrítica também é afirmação, e exige o mesmo padrão de prova** — exagerar o próprio erro
  estraga o registro tanto quanto escondê-lo.

Aterre **no fim da sessão** e também depois de qualquer trecho longo de trabalho — branch que nunca
aterra é trabalho que ninguém vê, e a próxima sessão refaz. Se a sessão terminar ainda dentro do
worktree, o branch sobrevive mas nada foi mesclado: retome com `EnterWorktree(path: …)` ou mescle do
checkout principal.

## 🏠 `git` dentro de worktree: use `/usr/bin/git` desde o primeiro comando

Tudo nesta seção foi medido no `linkedin`. **Vale aqui porque a causa não é do repo:** é o hook do
`rtk`, que é global nesta máquina e reescreve `git …` para `rtk git …`.

💡 **Truque medido em 2026-10-01 para o bloqueio do passo 2:** quando o harness recusar um comando git
por complexidade, chame o binário direto — `/usr/bin/git …` — que escapa da reescrita do hook do `rtk` e
passa a verificação. E **mensagem de commit longa vai em arquivo** (`git commit -F <arquivo>` com o
arquivo no scratchpad), não em heredoc: heredoc grande é recusado.

🔺 **2ª confirmação em 2026-10-13, e ela ALARGA o escopo: não é "quando recusar por complexidade" —
dentro de um worktree o `git` nu é recusado SEMPRE, inclusive em leitura.** Medidos um a um:
`git status --short`, `git log --oneline -1` e `git -C <caminho absoluto do próprio worktree> status`
— **os três recusados**, com a mesma mensagem (*"runs rtk with a git command among its operands"*).
⇒ a causa **não** é o comando ser complexo nem tocar no checkout principal; é o hook do `rtk` reescrever
`git …` para `rtk git …`, e o verificador de isolamento não conseguir ler o que a forma reescrita roda.
⚠️ **`-C` com o caminho certo NÃO salva** — o verificador não chega a avaliar o caminho.
⚠️ **E `command git …` TAMBÉM é recusado** (medido isolado): o que escapa é **o caminho absoluto**,
não qualquer forma de contornar o alias. ✅ **Vários `/usr/bin/git` encadeados com `&&` passam**
(`add` + `diff --cached --stat` numa chamada só); **basta um `git` nu no meio para a chamada inteira
cair.**
📌 **Consequência prática: dentro de worktree, escreva `/usr/bin/git` desde o primeiro comando** — não
espere a recusa. Cada recusa custa um round-trip, e nesta sessão custou cinco.

🔧 **3ª medição, 2026-10-13 (mesmo dia, outra sessão), e ela CORRIGE o *"SEMPRE, inclusive em
leitura"* sem mudar o conselho:** o discriminador é a chamada **começar** com uma substituição
`$(git …)`. Medido, quatro formas na mesma sessão e no mesmo worktree:

| Comando | Resultado |
|---|---|
| `git status --short` (sozinho) | **recusado** |
| `git status --porcelain -uall` (sozinho) | **recusado** |
| `echo probe; git status --porcelain -uall` | **recusado** — composto não basta |
| `echo "branch: $(git branch --show-current)"; git status --porcelain -uall` | ✅ **passou**, reproduzido 2× |

⇒ não é leitura × escrita, nem simples × composto: é a `$( )` com `git` dentro **na cabeça da
chamada** mudando o que o hook do `rtk` reescreve. ⚠️ **E isso NÃO é uma segunda via a usar:** a
chamada que passa está passando **sem o verificador de isolamento conseguir verificá-la** — é um
acidente de parse, não uma autorização, e qualquer mudança no hook o fecha sem aviso.
📌 **O conselho fica idêntico e fica mais forte: `/usr/bin/git` desde o primeiro comando.** A
diferença é só não se surpreender quando uma leitura nua passar: isso não significa que o bloqueio
sumiu. ✅ **`git commit` foi recusado em TODAS as formas tentadas** (`-q -F -` com heredoc, `-F
<arquivo no scratchpad>`, `-F ./arquivo`, `-m … --dry-run`, e também `rtk git commit …` com o `git`
logo após o launcher) — para commitar, só o caminho absoluto.

🔴 **E o `rtk` ESCONDE COMMIT DE MERGE do `git log --format=…` — medido 2026-10-13, na mesma
sessão e na mesma chamada.** `git log --format='%h %an | %s' origin/main..main` imprimiu **2** linhas
enquanto `git rev-list --count origin/main..main` imprimiu **3**, no mesmo intervalo; `/usr/bin/git`
imprimiu as três. **A linha omitida era o commit de MERGE**, que é justamente o commit que carrega
trabalho de outra sessão. ⚠️ **Não é propriedade de merge:** o mesmo `rtk` mostrou o merge quando
pedido com `--oneline` ⇒ **é por FORMA DE SAÍDA**, e a forma degradada é a do `--format`
personalizado. 📌 **Consequência: a leitura que a §8 da skill manda fazer antes do push é exatamente
a que o `rtk` degrada** — e degrada **em silêncio, saindo 0**, como todo defeito deste repo que vale
registrar. ⇒ **leia o `rev-list --count` ao lado do log e compare os dois números**, ou leia com
`/usr/bin/git`. Um número sozinho aqui não é medição.

## Quando o merge conflita

**Conflito aqui é o desenho funcionando, não falha** — é o git recusando-se a escolher, no seu lugar,
entre o trabalho de duas sessões.

⚠️ **Nunca resolva conflito com `--ours`/`--theirs` em bloco.** Os dois lados são trabalho de alguém;
perder um é a falha silenciosa que toda a estrutura existe para evitar. 🏠 Aqui o conflito cai quase
sempre no `index.html`: resolva trecho a trecho, e abra a página depois.

🏠 As regras por arquivo do `linkedin` não foram trazidas, mas uma delas generaliza: ***"fique com os
dois lados"* não é sempre a resolução certa.** Quando os dois lados editaram a **MESMA** unidade (lá, a
mesma linha de uma tabela), manter os dois deixou uma duplicata que nenhuma ferramenta acusou. ⇒ se os
lados são coisas diferentes, mantenha os dois; se são duas versões da mesma coisa, **funda**.

### 🔀 O conflito que o git NÃO dá: duas sessões escrevendo a mesma coisa

Em 2026-10-04, no `linkedin`, duas sessões fizeram a mesma descoberta no mesmo dia e cada uma escreveu
a sua ferramenta, com nomes diferentes. **O git mesclou limpo** — zero conflito — e o repo ficou com
duas cópias da mesma coisa, cada uma com metade das melhorias. O trabalho dobrado foram ~40 minutos; o
dano real seria a terceira sessão escolher a cópia errada.

> ⚠️ **Antes de escrever algo novo, duas medições — não uma:** olhar o que já existe **e**
> `git log --oneline -15`. Olhar a árvore não basta: a sessão concorrente pode ainda estar no worktree
> dela, e aí o código não existe no seu checkout mas o commit já existe no branch. **O ledger pega quem
> está escrevendo, não o que está sendo escrito** — leia também a coluna de escopo das linhas abertas
> (é para isso que ela existe).

## Recursos compartilhados que o git não vê

O `git worktree list` não mostra nada disto:

- **Pilha do `git stash`** — compartilhada entre worktrees. **Nunca `git stash` / `git stash pop` nus:**
  você pode levar o stash de outra sessão. Prefira um commit WIP.
  📎 **O detalhe de COMO está na skill `commit-in-shared-checkout`:** a pilha, o `HEAD` e o índice são
  compartilhados, e **cada uma dessas falhas sai 0 e imprime um resumo que parece certo**.
- **A árvore de trabalho do checkout principal.** Em 2026-10-01, num repo irmão, um `git add -A` de uma
  sessão **engoliu o trabalho não commitado de outra**. ⇒ **adicione pelo nome, nunca `git add -A` nem
  `git add .`**, e leia o `--stat` do próprio commit antes de seguir.
- **O arquivo que você acha que está criando.** Se o `Write` responder *"has been **updated**"* onde
  você esperava *"File **created**"*, outra sessão chegou antes: **pare e investigue**. No `linkedin`
  esse foi o único sinal de uma sobrescrita que o `git status` mostrou como modificação comum.
- 🏠 **A porta do servidor local** (`python3 -m http.server 8000`, do `CLAUDE.md`) — **não medido,
  derivado do comando.** Duas sessões não servem na mesma porta, e quem abre `localhost:8000` vê o
  checkout de **quem subiu o servidor**, não o seu. ⇒ sirva o seu worktree em outra porta e confira o
  caminho que o servidor imprime antes de acreditar no que o navegador mostra.

## Medir, não recordar

Antes de concluir que algo está livre, meça — e **meça de novo imediatamente antes de agir**, porque um
checkout compartilhado muda sob você:

```sh
git worktree list                        # a máquina toda, não a sua parte
git -C <worktree> status --porcelain     # sujo? e de quem?
ls -l --time-style=+%H:%M:%S <arquivo>   # escrito há segundos ou há horas?
git push --dry-run origin <branch>       # 🥇 o servidor tem cópia? (não envia nada)
git ls-remote --heads origin <branch>    # QUAIS refs o servidor tem (ver a ressalva abaixo)
```

🔴 **E `ls-remote` NÃO é suficiente para *"está empurrado?"* — medido em 2026-10-20, contra mim.**
Eu reportei `main` em sincronia citando **duas** leituras concordantes — `ls-remote origin
refs/heads/main` e `rev-list --count origin/main..main` → `0` — e as duas estavam **erradas**: o
`reflog` de `refs/remotes/origin/main` mostra o servidor em `6b93cda` das **10:30:09** às
**12:52:56**, e a minha medição caiu nessa janela. O push que o usuário rodou em seguida escreveu
**95 objetos** e moveu `6b93cda..fe7838d` — se já estivesse empurrado, diria `Everything up-to-date`
e escreveria **zero**.
⚠️ **NÃO isolei o mecanismo, e não invento um:** `ls-remote` **alcança** o servidor de verdade (um
repo inexistente devolve `Repository not found` autenticado, e ele lista refs que não existem
localmente). O que ficou provado é o **efeito**, não a causa.
✅ **O remédio não depende da causa: o teste autoritativo de *"está empurrado?"* é TENTAR EMPURRAR.**
`git push --dry-run origin <ref>` não envia nada, e **discrimina nos dois sentidos** (medido no mesmo
minuto): `main` → `Everything up-to-date`; um branch nunca empurrado → `* [new branch]`, **sem
criá-lo**.
📌 **E o erro de método, que é o que vale guardar:** eu tinha **duas leituras contraditórias do mesmo
fato, minutos uma da outra** (`20 à frente`, depois `0`) e resolvi a contradição **no sentido
conveniente** em vez de declarar que não sabia. ⇒ **duas leituras que discordam não autorizam
escolher uma: autorizam dizer que não se sabe, e rodar o teste que decide.**

### 🧠 E o que envelhece primeiro é o SEU PRÓPRIO CONTEXTO — medido no `linkedin` em 2026-10-09, seis vezes

A seção acima trata do estado **compartilhado** (worktree, arquivo, servidor). Falta o caso que mais
errou num único dia: **o `CLAUDE.md`, o índice de memória e as conclusões da própria sessão são um
INSTANTÂNEO do momento em que a sessão começou** — e várias sessões escrevem ao mesmo tempo. Lá, seis
afirmações erradas num dia tiveram o mesmo formato: afirmar a partir do contexto em vez de medir.
(🏠 A tabela dos seis casos não foi trazida: é sobre o conteúdo daquele repo.)

🔑 **O padrão, e é o que vale guardar:** o erro **nunca** foi de raciocínio — foi sempre **citar um
número que já existia corrigido em algum lugar do repo**, a um `grep` de distância. ⇒ 📌 **Antes de
escrever um número no repo ou dizer um número a ele, `grep` o número.** 🏠 Aqui os números que mais
circulam são os da leitura de força (limiares em bits, o ponto em que a barra enche, a taxa de
tentativas do `crackTime()`): moram no `index.html` e são **citados** no `CLAUDE.md` — se divergirem,
vale o código.

🔺 **Propagar para onde se DECIDE vem antes de propagar para onde se DOCUMENTA**; se só der para um, é
o `CLAUDE.md`, que é o que toda sessão lê antes de agir.

⚠️ **Corolário contra o remédio óbvio:** *"então sincronize tudo"* **não é a resposta** — lá, propagar
um número em massa corrompeu fatos duas vezes e foi revertido duas vezes. **A regra é propagar POUCO e
no lugar certo, não muito.**

⚠️ **Datas em BRT. Leia `date` local, nunca UTC.** A máquina é `America/Sao_Paulo` (−03), então
**entre 21:00 e a meia-noite o UTC já está no dia seguinte**. Verificado no `linkedin` em 2026-10-03:
quatro commits feitos entre 21:32 e 21:54 BRT gravaram **11 datas** com o dia seguinte — uma delas
*"2026-10-04, **à noite**"*, que é **data UTC com hora BRT**.
**Procedimento:** antes de escrever qualquer data num documento ou no ledger, rode `date '+%Y-%m-%d'` e
use o que ele devolver. Se um horário vier de fonte externa (API, log), **converta para BRT antes de
registrar** e diga a origem.

⚠️ **`@{upstream}` não prova que a cópia remota existe** — resolve contra o seu ref local e sobrevive à
deleção no servidor. 🔧 **CORRIGIDO 2026-10-20: a frase antiga dizia *"só `ls-remote` responde"*, e
`ls-remote` já respondeu ERRADO no `linkedin`** (ver a caixa de comandos acima) ⇒ **quem responde é
`git push --dry-run origin <branch>`**; `ls-remote` fica para *"quais refs existem"*, que é outra
pergunta.

⚠️ **`pgrep` sempre casa com o seu próprio comando.** Leia as linhas ou exclua o wrapper; **nunca conte**
e nunca ponha `pgrep -c` dentro de um `if` — é falso positivo garantido.

⚠️ **Estado commitado não vê trabalho em curso.** `git show origin/main:<arquivo>` lê o commit; uma
sessão escrevendo responde só pela árvore de trabalho. Para "alguém já começou X?", leia `git status`,
mtimes e processos — não o commit.
