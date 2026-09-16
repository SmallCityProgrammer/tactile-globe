# Carentan, 12 de junho de 1944

> O mapa de Carentan no QGIS, no estilo *The Operations Room*, e um estúdio de
> cena que anda com soldados top-down por cima dele e sai com um mp4.
>
> É o trecho **9:00–11:00** do vídeo: às 6h a Easy Company do 2/506 sobe do
> sudoeste, a MG 42 do entroncamento prende o 1º Pelotão na estrada, Welsh
> contorna e silencia a metralhadora com granada, e às 7h a cidade é americana.

```
fetch.mjs ─► osm.json ─► convert.mjs ─► *.geojson ─► carentan.py ─► qgis/*.jpg + *.json
                                              │            ▲              (a placa desenhada)
                                              │   textura, estilo,              │
                                              │   arvores, telhado ─────────────┘
                                              │
                                              ├─► malha.mjs ─► data/malha.json   (ruas + prédios)
                                              │
                  IGN BD ORTHO ─► orto.py ─► orto/*.jpg + *.json   (a placa de FOTO — ganha)
                                                        │
                            data/sprites/*.png ─────────┼─► pack.mjs ─► carentan.html
                                   cenas/*.json ────────┘                     │
                                                                    render.mjs ─► render/*.mp4
```

```bash
py -3 tools/orto.py                   # as placas de ortofoto (o padrão)
node tools/pack.mjs --desenho         # ...ou force as do QGIS
```

```powershell
cd 'C:\Users\eliez\OneDrive\Desktop\Globe Studio\Carentan 1944\qgis'
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' carentan.py --camadas               # o quadro largo
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' carentan.py holgate 8192 --camadas  # o fechado, em alta
```

```bash
py -3 tools/pincel.py                 # (o --camadas ja chama isto no fim) repinta as ruas -> qgis/*.png + *.jpg, ~2 min a 8192 px
```

```bash
cd "Carentan 1944"
node tools/malha.mjs                              # o grafo das ruas + a máscara de prédio
node tools/pack.mjs                               # -> carentan.html
node tools/render.mjs --check                     # o que renderizaria, sem desenhar
node tools/render.mjs --from=93 --secs=3          # render de janela
npm run render                                    # o filme -> render/carentan-easy-2min.mp4
```

---

# 1. O mapa

Copiado do **`Ardenas 1944/qgis`** do repo dos mapas detalhados, que é o caso
geral: terra firme, sem linha de costa, onde quem desenha o mapa é o talhão. Vêm
de lá o telhado em SVG escolhido por classe, a copa em PNG com alfa, a ondulação
do talhão e a colcha de tons por tipo. As armadilhas de PyQGIS estão catalogadas
no **guia de orientação** daquele repositório; não se repetem aqui.

Três coisas mudaram, e as três porque **Carentan não é Bastogne**.

## O bocage, porque o OSM não tem os talhões

Bastogne tem 2340 talhões de campo mapeados, e a colcha de tons por tipo desenha
a paisagem sozinha. O recorte de Carentan tem **cinquenta**, e nenhum
`landuse=farmland`: o campo francês em volta não está mapeado talhão por talhão.
Copiar o chão de Bastogne deixaria a metade rural do mapa como um lençol de oliva
liso — e aí o mapa contaria a história errada, porque o bocage é a razão de essa
batalha ter durado seis dias.

A saída é textura: ruído celular com métrica misturada euclidiana/Chebyshev (a
euclidiana pura dá favo de mel; o campo normando é de quadriláteros), peso
aditivo por célula para os talhões terem tamanhos diferentes, e três ladrilhos —
tom, lavoura e sebe. A sebe e a lavoura carregam **cor**, porque matiz não se
consegue empurrando o que está embaixo para mais claro.

**É textura, não cadastro**, e a diferença importa: ela diz "este chão era
dividido assim", que é verdade, sem afirmar onde ficava cada divisa — que seria
mentir com precisão. E é a **única coisa do mapa medida em metros de chão** e não
em milímetros de tela, porque o talhão normando tinha uns 140 m e isso é um fato
sobre o lugar, não sobre o desenho.

## O bege preso ao quarteirão

Em Bastogne o `landuse=residential` é justo, cola no casario. Em Carentan os seis
polígonos de residential cobrem a comuna inteira, e o mapa saía com uma **chapa
bege de canto a canto** onde devia haver quintal, horta e campo entre os
quarteirões.

O urbano passou a ser cruzado com onde há prédio de verdade: engorda cada prédio
22 m, funde, encolhe 14 (isso fecha os vãos e arredonda os cantos) e corta o
urbano por dentro disso. Os 85 m do pátio de Pearl Harbor não servem — lá eram
galpões soltos num campo, aqui o quarteirão normando é denso e 85 m juntaria a
cidade num borrão redondo.

## O brejo

Carentan é uma ilha de chão seco entre os vales alagados da Douve e da Taute. Os
alemães abriram as comportas em maio de 44, e é por isso que os paraquedistas só
tinham a calçada exposta para descer. Não é cenário: é a explicação da batalha.

Duas coisas: boa parte do pântano vem como **relação** no OSM, e sem tratar
`members` o vale inteiro some; e a **borda tem que desmanchar**, porque o
polígono é uma linha firme e brejo não termina numa reta — shapeburst
transparente na divisa, cheio lá dentro.

## A rua estava em milímetros de tela, e esse era o bug

A regra da casa é "tudo em milímetros", e ela está certa para **trama**: a
granulação do papel, a mancha do campo, o grão. Essas não têm tamanho no mundo,
então têm que ter tamanho na tela.

Mas a **rua tem**. Uma estrada rural normanda tem cinco metros e meio, e isso é
um fato sobre o lugar, não sobre o desenho. Com a via em milímetros ela saía com
**3,6 px em qualquer placa**: na placa larga passava, mas na de 8192 px sobre
1,1 km a casa tinha trezentos pixels e a rua continuava com 3,6 — um fio.
Fechar o zoom aumentava tudo menos justamente o que precisava aumentar, e a cena
ficava com soldados maiores que a rua por onde andavam.

Passaram para **metros de chão** (`RenderMetersInMapUnits`) todos os que têm
largura no mundo:

| | largura |
|---|---|
| via, por classe | 9 / 7 / 5,5 / 3,2 m de pista, com acostamento |
| curso d'água | rio e canal 8 m, córrego 3, vala 1,5 |
| trilho | 4,5 m de lastro |
| copa | 6 a 12 m de diâmetro |

A **densidade da mata foi junto**, e tinha que ir: se a copa cresce com o zoom e
a contagem continua por área de tela, o quadro fechado põe o mesmo número de
árvores num pedaço muito menor de terreno, cada uma agora enorme — o bosque vira
um tapete verde sem uma árvore dentro. 40 por hectare é mata de bocage.

E o **chão da cidade deixou de ser laje**. O `apron` das Ardenas veio do pátio de
Pearl Harbor, que é concreto lançado por baia; num quadro largo lê como chão
batido, mas a 0,063 m/px mostra o que é: uma malha de placas de dois metros,
piso de garagem por cima da cidade inteira. O bege daqui é quintal, horta e
calçada de uma cidade de mil anos — `mancha`, que é irregular e sem período.

## As ruas, pintadas por cima

A via como **símbolo de linha** do QGIS tinha um teto, e ele apareceu no quadro
fechado: faixa cinza chapada, contorno de espessura uniforme, ponta em
semicírculo. Isso é um mapa rodoviário; com um pelotão andando em cima, é
desenho animado. O que a referência tem é uma **estrada**: piso com o desgaste
das rodas, beiral mais escuro e irregular, capim batido no acostamento, vala no
campo, meio-fio e calçada na cidade, sebe com sombra ao longo da estrada rural.
Nada disso cabe num símbolo de linha, e não vale a pena forçar.

Então a rua saiu do QGIS e passou a ser **pintada em raster por cima**, em
`tools/pincel.py`. É o "Photoshop por cima", só que em código, pelo mesmo motivo
do `pos.py`: o que se pinta à mão se perde no próximo render; o que está em
código volta em dois minutos.

**Como entra na pilha.** `carentan.py --camadas` grava três fatias registradas
ao pixel: o chão **sem** a via (opaco), a via sozinha (só para conferir o
registro) e o que fica **acima** da via — prédios com a própria sombra, sebe do
OSM e o grão do papel — com alfa. O pincel pinta a rua entre as duas. É por isso
que a sombra do prédio continua caindo na rua e o grão continua cobrindo tudo:
nada disso é refeito. A ferrovia é a exceção: saiu da fatia de cima e é pintada
pelo pincel (lastro de brita e os dois trilhos, e na passagem de nível o lastro
some e só o trilho atravessa o piso), porque a faixa chapada dela tinha o
mesmo defeito.

**O registro é conferido, não prometido.** O pincel rasteriza o eixo de cada via
a partir do `via.geojson` e da ficha da placa, e mede quanto desse eixo cai
dentro da via que o QGIS desenhou: 100% nas três placas.

**Uma medida que mudou o tamanho da rua.** Comparando o eixo com a borda da via
do QGIS, a "meia-largura de 3,75 m" da classe 3 saía com **2,35 m de chão** — e
a de 2,3 m com 1,43. Fator 0,63, em todas as classes e nas duas placas: é o
`cos(49,3°)`. Sem elipsoide no `QgsMapSettings`, o `RenderMetersInMapUnits`
converte o metro na **unidade de mapa** do 3857, que nesta latitude está
esticada em 1/cos. Ou seja: a tabela acima diz 5,5 m, o desenho tinha 3,6. O
pincel mede em metros de chão de verdade (pela `larguraKm` da ficha, como o
próprio `carentan.py`), então a rua sai uns 50% mais larga do que saía — e do
tamanho que tem. A copa, o rio e o trilho do `estilo.py` continuam com o mesmo
fator; está aqui para quem for mexer neles.

**O que é dado e o que é inventado.** Posição, classe e tag vêm do OSM. O piso é
deduzido da tag — asfalto na nacional e na secundária, macadame nas vicinais,
cascalho no caminho de serviço, terra com dois sulcos na trilha — e a textura é
ruído sem período. A **sebe ao longo da estrada rural** segue o contrato do
bocage: havia sebe na beira de quase toda estrada normanda, e isso é um fato
sobre o lugar; onde cada uma tinha um vão é sorteio, de baixa frequência (45 m)
para não sair em pedacinhos. Só a mais de 60 m da cidade, nunca em caminho de
serviço nem sobre água. A fila de árvores que o OSM mapeou (`sebe.geojson`)
passa pelo mesmo pincel, sem vão. `SEBES = False` desliga a sorteada.

**O que o painel de juízes mudou.** Três olhares independentes sobre recortes
cru | pintado | ortofoto, e o que ficou: o piso **claro e neutro** (vista de
cima a estrada é a superfície mais clara do terreno; a primeira versão, escura,
virava vala entre as casas); o beiral como **linha fina e escura**, não como
gradiente (a rua ficava fora de foco ao lado dos telhados de vetor); nada
escuro e simétrico em volta da rua — o escuro só vem da sombra da sebe, de um
lado; a pista como **união** dos polígonos, fechada em 2 m, para o toco morrer
na borda da rua larga em vez de atravessá-la em bico e o canto de dentro do
cruzamento sair arredondado; e a grade do ruído nunca mais fina que 5 px, que
era o que punha tracinhos periódicos na sebe da placa larga.

Tudo está em **metros de chão**: pista por tag (8 / 6,5 / 6 / 5,5 / 5 / 3,2 /
3 m), beiral 0,3 m, orla clara 0,35 m, capim 0,9 m, calçada 1,8 m, sebe a 1 m
do beiral com 1,5 a 4,5 m de largura e sombra de 2,4 m para sudeste, lastro
4,5 m por via com bitola de 1,435. A mesma rua sai com a mesma largura na
placa larga e na fechada, que é o que deixa o estúdio trocar de placa no meio
de um movimento de câmera sem a rua mudar de tamanho.

Um número do `estilo.py` mudou junto: a sebe do ladrilho do bocage passou de
0,030 para 0,020 de talhão (4 m → 2,8 m) e a sombra de 3 para 2 px (4 m →
2,6 m). Com os valores antigos a faixa escura chegava a 8 m e, no quadro
fechado, lia como dedo sujo em vez de fila de árvores.

## A placa é ortofoto, não desenho

O mapa vetorial chega a 0,063 m/px e ali fica **sem o que dizer**, não sem
pixel: o OSM sabe onde está cada prédio e cada rua, e mais nada — não sabe do
muro do quintal, da horta, do rastro de trator no campo, da sombra que a árvore
joga na estrada. Fechar mais o zoom só fazia mancha chapada maior.

A referência do Operations Room, no enquadramento fechado, não é desenho: é foto
aérea. A diferença não era de escala, era de **fonte**. Então a fonte mudou.

`tools/orto.py` monta a placa a partir da **BD ORTHO do IGN** francês, servida
pela Géoplateforme em WMTS, licença aberta Etalab com atribuição. Resolução
nativa 20 cm/px — o z19 do xadrez de tiles. **O z20 não existe: devolve 404,
medido.** Então 0,195 m/px na latitude de Carentan é o teto do dado, e um quadro
mais fechado que uns 375 m num vídeo de 1920 px está ampliando pixel.

O que **não** muda: a ficha `.json` ao lado da imagem é a mesma que o
`carentan.py` grava — mesmos limites, mesma extensão em 3857, mesmos metros por
pixel. Por isso a cena, o grafo de ruas, a máscara de prédio e o estúdio inteiro
continuam funcionando sem uma linha de diferença. A placa é só a imagem que fica
embaixo, e `node tools/pack.mjs --desenho` traz o desenho de volta.

> **O recorte tem que ser exato.** O xadrez de tiles não cai nos limites do
> quadro. Recortar no pixel certo é o que mantém a ficha válida, e um erro de
> meio tile aqui põe todo soldado da cena dez metros fora do lugar sem que nada
> denuncie.

O pipeline do QGIS **continua inteiro** e não foi desligado: ele é quem produz o
`via.geojson` e o `predio.geojson` de onde saem o grafo de ruas e a máscara de
prédio, e quem desenha a placa ilustrada para quando se quiser a carta larga em
vez da foto.

## A etiqueta, e o tamanho de um homem

A pílula de fundo claro saiu. Sobre foto aérea ela vira um adesivo opaco tapando
justamente o terreno que a foto foi buscar. O que a referência faz é mais
simples e mais forte: **versalete branco com contorno escuro**, sem caixa, e uma
**haste** fina descendo até um ponto no lugar da unidade. O contorno é o que faz
o texto ler sobre telhado claro e sobre sombra de árvore com a mesma facilidade —
uma cor só nunca consegue as duas. E a haste é o que diz a qual unidade a
etiqueta pertence depois que o desempilhamento empurrou o texto três linhas
acima.

O versalete é desenhado à mão: o canvas não respeita `font-variant`.

E o soldado encolheu para o tamanho de um soldado. O tamanho de um homem no
grupo era **derivado** — `sizeM / raiz(n)`, o que dava 8,6 m por homem num
pelotão de 26. Sobre desenho passava; sobre ortofoto de 20 cm/px vira um boneco
do tamanho de uma casa em cima de uma rua de cinco metros. Agora é
`grupo.homemM`, explícito, 2,6 m — e `minPx` segura o mínimo em pixels para o
plano largo, onde 2,6 m são dois pixels.

## As placas

| placa | largura | saída | fonte |
|---|---|---|---|
| `carentan` | 3,18 km | 4096 px, 0,776 m/px | ortofoto z18 |
| `holgate` | 1,10 km | 5632 px, **0,195 m/px** (nativo) | ortofoto z19 |
| `entroncamento` | 0,26 km | 1400 px, 0,186 m/px | ortofoto z19 |

O estúdio escolhe **uma por quadro**: a mais fina que cabe inteira no que a
câmera vê. A de 0,134 m/px é o que deixa a câmera fechar a 200 m sem a rua virar
papa — a pergunta que ficou em aberto na versão anterior, quando a placa fechada
tinha 0,27 m/px. Empilhar as duas seria mais suave na transição, mas as texturas
do QGIS estão em milímetros de **tela** e mudam de escala entre um recorte e
outro; a emenda apareceria como um degrau de granulação no meio do campo.

Junto de cada PNG vai um `.json` com os limites em graus e a extensão em 3857.
**Sem ele o render é só um desenho bonito**; com ele o estúdio converte lon/lat
em pixel, e é isso que deixa um soldado andar pela Rue Holgate de verdade.

---

# 2. Andar na rua, e não por cima dela

Uma rota desenhada à mão passa por cima de tudo: o pelotão atravessa o quarteirão
em diagonal, entra num prédio e sai do outro lado. Num mapa onde se lê cada
telhado, é a primeira coisa que o olho pega.

O `tools/malha.mjs` tira duas coisas do OSM, e as duas são **dado**:

**A malha** — o grafo das ruas: 3680 nós, 4025 arestas, **99% num pedaço só**. Um
passo de rota com `"naRua": true` deixa de interpolar entre dois pontos e passa a
andar: acha o nó mais perto de cada ponto e procura o caminho mais curto por ruas,
com A\* e heurística de linha reta. O pelotão dobra a esquina porque a esquina
existe.

> A **colagem** é o que faz o grafo ser um grafo. No OSM duas ruas que se cruzam
> quase sempre partilham o nó — mas "quase". Um fim de rua a 30 cm do começo da
> outra fica sendo duas ilhas, e o caminho entre elas não existe. Colar a 4 m
> uniu 50 pares e levou o maior pedaço a 99% dos nós.

**O bloqueio** — um bit por célula de 3,11 m dizendo onde há prédio, em 72 KB de
base64. Máscara de bit e não polígono: os 3365 prédios em GeoJSON são 1,5 MB e
cada teste seria um ponto-em-polígono contra todos; aqui a mesma pergunta é um
índice num array. O que importa é "há parede neste metro quadrado", não qual
parede.

> Testar só o **centro** da célula perdia 90 de 400 prédios — todo anexo mais
> estreito que 3,1 m, e todo prédio em L, cujo centroide cai fora do L. Andar
> pelas **arestas** do polígono fecha o contorno e levou a cobertura de 9,0%
> para 12,9%.

## O critério de reprovação, e o erro que eu cometi nele

A primeira versão reprovava qualquer trecho com 20 m contínuos dentro de parede —
e reprovou **os caminhos de rua**. Na cidade normanda a casa dá para a calçada, o
eixo da via passa a três metros da fachada, e a célula de 3,1 m não sabe separar
as duas.

Reprovar ali seria a validação discutindo com o próprio dado: se o OSM diz que há
rua, há rua. Então um passo `naRua` vira **nota** ("passa rente a 33 m de
fachada — é rua estreita, não atalho"), e a reprovação fica para o traçado à mão,
que é onde o atalho por dentro do quarteirão realmente acontece. Foi o que sobrou
depois: um só, o arranque final de Welsh, que atravessava 30 m do próprio Bar du
Stade.

---

# 3. A cena

Mesmo contrato do Globe Studio — a cena é um JSON e é a única coisa que o
renderizador lê. O que este estúdio tem a mais está em
`cenas/carentan-easy-2min.json`, comentado linha a linha:

| campo | o que faz |
|---|---|
| `route: [ {points…}, {esperar: 46}, {points…} ]` | a rota é uma **agenda**; o passo seguinte começa quando o anterior acaba |
| `"naRua": true` | o passo anda pelo grafo das ruas em vez de reta |
| `grupo: {n, espalhoM, formacao}` | n homens numa rota só (`coluna`, `linha`, `cunha`, `nuvem`) |
| `imgEspera` | o desenho do parado: em pé andando, de bruços na vala |
| `camera: {chaves: [...]}` | a câmera por tempo; zoom interpola em log, suave por padrão, `corte: true` pula |
| `entra` / `sai` | em que segundo a unidade aparece e some |
| `marcos`, `rotulo`, `relogio` | nomes de lugar, objetivos e **a hora da manhã** |
| `escalaDoTempo: 41` | quantos segundos de história cabem num segundo de filme |

`escalaDoTempo` não é enfeite de documentação: **dois pedaços do motor dependem
dele**, o relógio no canto e a validação de velocidade. Um pelotão que anda 535 m
em 9 s de filme está a 214 km/h na tela e a 7 km/h na história; só a segunda
leitura diz alguma coisa.

O relógio começa em **05:46** para que t=20 caia em 06:00 ("às 6h lançam o
ataque") e t=108 em 07:00 ("às 7h fazem a ligação") — os dois instantes que a
narração crava.

---

# 4. O render

**7 quadros/s** a 1920×1080: 120 s de filme em ~8,5 minutos.

Era **0,82** — 73 minutos para os mesmos dois minutos. A fatia maior do quadro
não era desenhar, era o Chrome **codificar o PNG** e mandar em base64 de volta.
Capturar em JPEG 92 corta isso para um terço, e o que entra no ffmpeg vai virar
H.264 com quantização muito mais grossa que a do JPEG: o que se perde aqui não
sobrevive ao codec de vídeo de qualquer jeito. `--png` traz o quadro intacto de
volta, para quem precisar.

## Os portões

1. `node tools/pack.mjs` sem erro (ele compila o script embutido);
2. `node tools/render.mjs --check` — valida a cena antes de qualquer pixel;
3. um render de janela do trecho tocado, olhado;
4. se gerou vídeo, a duração medida bate com a da cena (o render falha sozinho).

---

# 5. Os sprites, e uma ressalva

Recortados de quatro fotos em fundo branco com `tools/recorte.py`. **Dois deles
não são alemães**: `de-rifle` e `de-mira` são o mesmo figurante britânico
(capacete Brodie, Lee-Enfield) recolorido para feldgrau, porque não havia asset
alemão nenhum. Na escala do mapa quem diz o lado é a cor, não o capacete — mas é
recoloração, não reconstituição.

Para trocar por arte de verdade: PNG top-down em `data/sprites/` com o nome que o
catálogo pede, **nariz para cima**, e `node tools/pack.mjs`. Nenhum tempo de
nenhuma cena muda.

---

# 6. O que não está feito

**A moldura** de papel rasgado fica desligada de propósito: esta placa é palco e
os soldados andam até a borda. Uma borda desenhada seria parte do mundo.

**`exporta.py` e `pos.py`** vieram na cópia e não foram usados: eles servem para
levar o mapa em camadas para o After Effects, e aqui a animação acontece dentro
do próprio estúdio. Ficam prontos para o dia em que se quiser o caminho de fora.

**O grafo tem 6 pedaços**, e 1% dos nós está nos cinco pequenos. Uma rota que caia
num deles não fecha e o passo volta a ser reta. Nunca aconteceu nesta cena; se
acontecer, o sintoma é uma unidade cortando em diagonal apesar do `naRua`.

**A máscara não conhece muro nem cerca** — só `building`. Um quintal murado é
chão livre para ela.

**A anacronia continua**: o traçado que importa é o mesmo de 1944, mas o recorte
tem conjuntos habitacionais e uma zona comercial do pós-guerra. A N13 nova fica
fora do quadro por escolha do enquadramento.
