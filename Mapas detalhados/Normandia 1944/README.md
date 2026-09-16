# Carentan, 12 de junho de 1944

> O mapa de Carentan no estilo Operations Room, feito inteiro no QGIS a partir
> do OpenStreetMap — e um estúdio de cena para andar com assets top-down por
> cima dele e sair com um mp4.
>
> É o trecho **9:00–11:00** do vídeo: às 6h da manhã a Easy Company do 2/506
> sobe do sudoeste, a MG 42 do entroncamento prende o 1º Pelotão na estrada,
> Welsh contorna e silencia a metralhadora com granada, e às 7h a cidade é
> americana.

```
fetch.mjs ─► osm.json ─► convert.mjs ─► *.geojson ─► carentan.py ─► *.jpg + *.json + .qgz
                                                          ▲
                                     textura.py ─► texturas/*.png ─┤
                                     estilo.py ───────────────────┘

carentan.py ──► qgis/*.jpg + qgis/*.json ─┐
                     data/sprites/*.png ──┼─► pack.mjs ─► carentan.html
                          cenas/*.json ───┘                    │
                                                        render.mjs ─► render/*.mp4
```

| arquivo | o que faz |
|---|---|
| `qgis/fetch.mjs` | baixa o retângulo do Overpass (precisa de `User-Agent`, e de espelho) |
| `qgis/convert.mjs` | `osm.json` → `agua rio brejo mata campo via trilho predio cais sebe.geojson` |
| `qgis/textura.py` | os ladrilhos procedurais emendáveis |
| `qgis/estilo.py` | a paleta e todos os símbolos — **o estilo não existe em outro lugar** |
| `qgis/carentan.py` | monta o projeto, renderiza a placa e grava onde ela cai no mundo |
| `src/template.html` | o estúdio de cena: o mapa como palco, a cena como dado |
| `tools/pack.mjs` | junta tudo num `carentan.html` de um arquivo só, offline |
| `tools/render.mjs` | a cena, quadro a quadro, como mp4 |
| `cenas/*.json` | as cenas prontas |

## Rodar

```powershell
# o mapa (uma vez, ~90 s por quadro)
cd 'C:\Users\eliez\OneDrive\Desktop\Mapa\Mapas detalhados\Normandia 1944\qgis'
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' carentan.py
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' carentan.py holgate
```

```bash
cd "Mapas detalhados/Normandia 1944"
node tools/pack.mjs                          # -> carentan.html (obrigatório depois de mexer no template)
node tools/render.mjs --check                # o que renderizaria, sem desenhar
node tools/render.mjs --from=21.5 --secs=3   # render de janela, para conferir o movimento
npm run render                               # o filme inteiro -> render/carentan-0600.mp4
```

Para abrir na mão: duplo clique no `carentan.html`. São 7 MB e o `file://` dá
conta; se der problema, `py -3 -m http.server 8791 --bind 127.0.0.1`.

---

# Parte 1 — o mapa

## A terra é o retângulo

Em Pearl Harbor o passo mais frágil do pipeline era deduzir a terra: o OSM não
tem o porto como polígono de água, só a linha de costa, e a terra saía
poligonizando costa + moldura e ficando com as faces que tinham densidade de
prédio. Uma heurística, com um corte em 0,15 que custou a achar.

Aqui esse passo **não existe**. Carentan é cidade de rio: a Douve, a Taute, o
canal e a bacia do porto são polígonos no OSM, e não há linha de costa dentro do
recorte. Então a terra é o retângulo inteiro e a água é recortada por cima dele.

Isso inverte uma coisa e vale dizer: em Pearl Harbor a terra era a figura e o
mar era o fundo, então a sombra era **projetada** a partir da terra. Aqui a
terra é o fundo e a água é o recorte — sombra projetada faria o canal parecer
flutuar *acima* do campo. A sombra é **interna** (`QgsInnerShadowEffect`): nasce
na margem e cai para dentro do rio, que é o que a margem faz.

## O bocage

O OSM tem **duas** sebes no recorte inteiro, e zero `landuse=farmland`. O campo
francês não está mapeado talhão por talhão. Um mapa de Carentan que aceite isso
sai com o campo aberto chapado de canto a canto — e aí conta a história errada,
porque o bocage é metade da razão de essa batalha ter durado seis dias.

A saída é a mesma do resto do estilo: **textura**. Ela diz "este chão era
dividido assim", que é verdade, sem afirmar onde ficava cada divisa — que seria
mentir com precisão.

### A matemática, e a forma

Ruído celular: distância ao ponto mais perto (F1) e ao segundo (F2). O tom vem
do dono, F1; a sebe é onde `F2 - F1` é pequeno, que é exatamente a crista entre
dois talhões vizinhos. A busca varre as nove células ao redor **módulo** a
grade, e é isso que fecha a emenda — o talhão cortado pela borda direita
continua na esquerda.

Duas correções foram o que tirou aquilo da cara de ruído:

**A métrica decide a forma.** Euclidiana pura dá favo de mel: seis lados, tudo do
mesmo tamanho, e o olho acha em um segundo que aquilo é ruído celular. O campo
normando é de quadriláteros. Chebyshev (`max(|dx|,|dy|)`) dá retângulos; a
mistura das duas, pesada por `quadrado=0.62`, dá o retângulo de canto
arredondado da foto aérea.

**Os talhões precisam de tamanhos diferentes.** Sem isso todo campo sai com a
mesma área, o que nenhuma paisagem tem. Um peso aditivo por célula — subtrair
`w_i` da distância — empurra a divisa para longe dos talhões grandes e para
perto dos pequenos, como o vizinho que comprou o pedaço do lado.

### São três ladrilhos, e a razão é matiz

| ladrilho | o que é | por quê |
|---|---|---|
| `bocage` | o tom de cada talhão | modulação de sobrepor, como todo o resto |
| `bocage_cultura` | os talhões que não estavam verdes | **cor**: feno, cereal e terra arada não são "mais claro" |
| `bocage_sebe` | a sebe, com sombra própria | **cor**: um aterro com árvores é outra coisa em cima do campo, não o campo mais escuro |

A primeira versão fazia tudo num ladrilho só de modulação preto-e-branco. A sebe
saía cinza-carvão e grossa, e o mapa inteiro lia como vitral. E o campo, variando
só de claro, virava um lençol de oliva — em 12 de junho parte era pasto, parte
feno de corte, parte cereal amarelando e parte já arada.

A sebe carrega a **sombra dentro do próprio ladrilho**, tirada da própria
máscara deslocada *módulo* o ladrilho (deslocar módulo é o que mantém a emenda).
Sem ela a sebe fica achatada no chão; com ela o campo ganha relevo e se lê que
aquilo tem altura — que é justamente o que importava para quem estava embaixo.

### A única coisa medida no chão

A regra da casa é milímetro de **tela**, e ela existe por um bom motivo: uma
trama de material tem que ter a mesma cara em qualquer zoom.

O bocage é a exceção declarada, porque ele não é material, é **feição**. O
talhão normando tinha uns 140 m, e isso é um fato sobre o lugar. Em milímetro
fixo o mesmo campo sairia com 300 m num enquadramento e 80 m no outro, e duas
cenas do mesmo filme mostrariam campos de tamanhos diferentes. Então a escala
vem do render: `estilo.malha_bocage()` recebe quantos metros cabem num milímetro
de tela e ajusta o ladrilho.

É por isso, também, que o deslocamento da sombra da sebe está em **pixels do
ladrilho** e não em milímetros: como o ladrilho é ancorado no chão, um pixel
dele vale sempre os mesmos ~1,3 m.

### Quantos talhões por ladrilho

Vale a regra de bolso da água de Pearl Harbor: quanto mais cabe dentro, menos a
repetição se denuncia. Com 4 células o ladrilho media 560 m e se repetia quase
seis vezes na largura do quadro — dava para achar o mesmo talhão marchando pelo
campo. Com 6 são 840 m e menos de quatro repetições.

## O brejo

Os alemães abriram as comportas da Douve em maio de 44 e deixaram o vale inteiro
alagado. É por isso que os paraquedistas não tinham por onde ir a não ser pela
calçada exposta, em fila, e é de onde vem o apelido Purple Heart Lane. O mapa
mostra Carentan pelo que ela era: uma ilha de chão seco entre dois pântanos.

**A borda tem que desmanchar.** O polígono de pântano do OSM é uma linha firme, e
desenhado com cor chapada ele corta o mapa numa diagonal dura que lê como erro
de recorte — brejo não termina numa reta, ele vai ficando seco. O shapeburst
resolve: transparente na divisa, cheio lá dentro. É a mesma ferramenta do raso
de Pearl Harbor usada ao contrário — lá para clarear a água junto da praia, aqui
para sumir com a própria camada na borda.

**A poça é medida.** Na primeira versão o limiar era 0,40 e o vale inteiro virava
lago. Aquilo era pasto alagado com água parada nas partes baixas, do tipo que se
atravessa com água pela canela, não uma lâmina navegável. 0,26 e alfa 128.

## O bege é a cidade, não a base

Mesmo truque do pátio de Pearl Harbor, com outro número e outra textura.

Lá o bege saía engordando cada prédio 85 m, porque a base tem galpões soltos num
campo. Aqui o quarteirão normando é denso: com 85 m a cidade inteira virava um
borrão redondo e as ruas sumiam. **22 m para fora e 14 de volta** fecha os
quarteirões, traz os quintais junto e deixa as ruas largas abertas.

E a textura mudou de `laje` para `mancha`. A `laje` está certa para o pátio de
uma base militar — aquilo é concreto lançado por baia, e o
[commit que a arrumou](../Pacífico%20WW2/qgis/README.md) empilha três escalas
justamente para isso. Mas o bege daqui é quintal, horta, calçada e pátio de
pedra de uma cidade de mil anos: a malha de placas aparecia como piso de
garagem por cima da cidade inteira.

## Um arquivo que o OSM tem e o Pacífico não usava

O `campo.geojson` traz duas coisas diferentes com o mesmo nome, e elas não podem
ir na mesma altura da pilha: o **prado aberto** tem que ficar debaixo das sebes
do bocage, e o **parque e o cemitério** têm que ficar por cima do chão da
cidade, senão somem no bege. Mesmo arquivo, dois subconjuntos, via
`setSubsetString`.

E o prado mapeado usa o **mesmo ladrilho de tom** do campo aberto, só com outra
cor de base. Não é preguiça: é o que o modo Viewport compra. Como todas as
camadas ancoram o ladrilho na tela, e não cada uma no próprio retângulo, a malha
de talhões atravessa a divisa do polígono sem emenda. O maior prado do recorte
tem 3,7 × 6,3 km — chapado, ele sozinho apagaria metade do mapa.

## O que é de hoje, e não de 1944

O mapa é desenhado a partir do OpenStreetMap de hoje, como o de Pearl Harbor. O
traçado que importa é o mesmo — a Route de Périers, o entroncamento em T, a Rue
Holgate, a igreja, o canal, a ferrovia — mas o recorte também tem coisa do pós-
guerra, e vale saber qual:

- os **conjuntos habitacionais** do sudoeste e do sul, aquelas fileiras regulares
  de casas pequenas;
- a **zona comercial** do noroeste, os galpões grandes;
- a **N13 de hoje**, via expressa de quatro pistas — essa fica de fora: o quadro
  padrão corta em 49,311 N e ela passa mais ao norte. O campo `h` do
  `via.geojson` guarda a tag do OSM justamente para poder tirá-la de um quadro
  mais largo.

Isto é um mapa ilustrado de um lugar, não uma reconstituição cadastral de 1944.

---

# Parte 2 — o estúdio

## A placa, e o arquivo que a torna um mapa

O `carentan.py` grava, junto do render, um `.json` com os limites em graus, a
extensão em 3857, a largura no chão e a resolução. **Sem ele o PNG é só um
desenho bonito.** Com ele é um mapa: o estúdio converte lon/lat em pixel, e é
isso que deixa um soldado andar pela Rue Holgate de verdade em vez de por uma
reta inventada.

Há duas placas, e o estúdio escolhe **uma por quadro**: a mais fina que cabe
inteira no que a câmera vê.

| placa | largura | resolução |
|---|---|---|
| `carentan` | 3,18 km | 0,78 m/px |
| `holgate` | 1,10 km | 0,27 m/px |

Empilhar as duas seria mais suave na transição, mas as texturas do QGIS estão em
milímetros de **tela** e mudam de escala entre um recorte e outro — a emenda
apareceria como um degrau de granulação no meio do campo. A cena pode fixar qual
usar em `camera.placa`.

O JPEG é 92 com croma inteiro (4:4:4): 2,9 MB contra 13 MB do PNG, com erro
médio de 1,4 em 255, **medido**. O croma não pode ser reduzido — a textura do
mapa é justamente o que o JPEG faz pior, e com 4:2:0 a sebe verde-escura sangra
nos talhões.

## A cena é dado

Mesmo contrato do Globe Studio: um JSON descreve a câmera, o relógio, as
unidades, as rotas e os tiros, e é a única coisa que o renderizador lê.

```json
{
  "camera": { "lon": -1.2483, "lat": 49.30235, "larguraM": 900 },
  "time": 0, "scale": 1,
  "sprites": [ { "id": "welsh-1pel", "type": "pelotao", "sizeM": 30, "…": "" } ]
}
```

Três diferenças em relação ao globo, e as três são a mesma ideia levada a sério:

**`sizeM`, não `sizeKm`.** O tamanho continua sendo a largura da imagem **no
chão**, o que faz a unidade crescer quando a câmera desce. A unidade muda porque
lá cabia um oceano e aqui cabe uma rua.

**`camera.larguraM`, não uma altura em raios terrestres.** "A câmera enxerga
900 m" é uma frase que se confere olhando o mapa. Um fator de zoom não é.

**A rota é uma agenda, não uma curva.** Cada passo é uma de duas coisas:

```json
"route": [
  { "points": [ … ], "duration": 9 },   // andar por aqui, levando 9 s
  { "esperar": 16 },                     // ficar onde está, 16 s
  { "points": [ … ], "duration": 16 }    // e seguir
]
```

e o passo seguinte começa quando o anterior acaba. Isso é o que torna uma cena de
dois minutos **escrevível**: com `start` explícito em cada perna, o primeiro
ajuste no meio — "a MG abre fogo dois segundos antes" — obriga a somar tudo de
novo na mão. Mexendo num `esperar`, o resto da fila anda sozinho.

`start` continua valendo, como **cravo**: um passo que traz `start` começa
naquele segundo e não no fim do anterior, e a fila passa a contar dali. É o que
prende uma unidade a um instante da narração — "às 7h a ligação é feita" — sem
depender do que veio antes.

Esperar **não é um estado guardado**: é o que a função devolve quando `t` cai
dentro de um passo sem pontos. Continua sendo função pura de `t`.

E o desenho do parado é outro. `imgEspera` é o par de `img`: o motor troca de um
para o outro quando o relógio cai numa espera, então o pelotão que sobe a estrada
em pé é o mesmo que fica **de bruços na vala** durante os quarenta segundos em
que a narração fala de outra coisa. Um campo, e a cena não precisa saber que
existem duas imagens.

**Um grupo é uma unidade com uma rota e n homens.**

```json
"grupo": { "n": 26, "espalhoM": 17, "formacao": "coluna" }
```

Um pelotão não é um boneco: são trinta homens, e desenhar um ícone só onde havia
trinta é a diferença entre um mapa de tática e um mapa de videogame. Mas trinta
unidades independentes são trinta rotas para escrever e trinta para corrigir
quando o tempo muda. A formação (`coluna`, `linha`, `cunha`, `nuvem`) é calculada
no referencial da unidade — `+y` é para onde ela vai — e depois girada pelo rumo,
então a coluna **vira junto na esquina**. O deslocamento de cada homem é função
pura do índice e da semente; sorteado a cada quadro, a tropa tremeria como
estática de televisão no vídeo.

**A câmera é uma lista de chaves.**

```json
"camera": { "chaves": [
  { "t": 0,  "lon": -1.2480, "lat": 49.3030, "larguraM": 2400 },
  { "t": 19, "lon": -1.2523, "lat": 49.2995, "larguraM": 900 }
] }
```

Quando o assunto é uma metralhadora numa esquina, 3 km de mapa na tela não
mostram nada; quando é "a cidade é americana", 300 m não mostram a cidade. Duas
decisões que valem a explicação:

- **o zoom interpola em log.** Ir de 1600 m a 200 m pelo meio linear passa metade
  do tempo entre 1600 e 900 e a outra metade entre 900 e 200 — na tela isso é uma
  aproximação que começa devagar e despenca no fim. Em log, cada segundo
  multiplica a escala pelo mesmo fator, que é como o olho lê zoom.
- **o padrão é suave.** Interpolação linear faz a câmera arrancar e parar de
  supetão em cada chave; o smoothstep tira a derivada nas pontas. Uma chave com
  `corte: true` pula, para quando a troca de assunto fica melhor cortada do que
  viajada.

Com chaves na cena, o relógio manda na câmera. Arrastar ou dar zoom **solta**
sozinho (as chaves ficam guardadas, intactas), e o botão `câmera` ou a tecla `c`
prendem de volta. Sem um dono explícito, arrastar o mapa durante a reprodução é
uma briga em que a mão perde a cada quadro.

**`entra` e `sai`** dizem em que segundo a unidade aparece e some, com uma
esmaecida curta. Numa cena de dois minutos, sem isso toda unidade fica plantada
no mapa desde o segundo zero — inclusive a que só chega às 7h.

**As legendas** são conteúdo, não auxílio de edição, e por isso têm chave própria
(`legendas`, tecla `l`) em vez de sumirem junto com as rotas e os waypoints.
`marcos` põe nomes de lugar e marcadores de objetivo no mapa, com hora de entrar
e de sair; `rotulo` põe o nome da unidade; e `relogio: "05:46"` põe **a hora da
manhã** no canto — não o segundo do filme, que é o que a barra de baixo já conta.

No plano de 260 m três etiquetas caem no mesmo punhado de pixels, então cada uma
sobe até achar espaço livre antes de ser desenhada. É guloso, resolve na ordem de
desenho, e as caixas zeram a cada quadro.

**`escalaDoTempo`** é quantos segundos de história cabem num segundo de filme —
41, nesta cena. Não é enfeite de documentação: **dois pedaços do motor dependem
dele**, o relógio da manhã e a validação de velocidade. Um pelotão que anda 535 m
em 9 s de filme está a 214 km/h na tela e a 7 km/h na história; as duas leituras
são verdadeiras, mas só a segunda diz alguma coisa. Um número só, servindo para
as duas coisas, é um número que não pode ficar desatualizado.

## Efeito é função pura de (semente, idade)

Traçador, clarão e baixa são calculados do instante do tiro e de mais nada. Nem
a morte de uma unidade acumula: `mapaDeBaixas()` deriva da cena, a cada quadro,
quando cada uma morre — uma unidade destruída é uma unidade cujo instante já
passou, e essa é uma pergunta que se responde com `t`. Volte para o segundo 3 e
o segundo 3 tem exatamente os mesmos pixels.

## A arte pode chegar depois

Uma unidade sem PNG não some e não vira um quadrado vermelho: vira uma **ficha
desenhada em código**, com a cor do lado e um traço apontando o rumo. É o que
deixa a cena inteira ser montada e cronometrada antes de a arte existir — que é
metade do motivo de a cena ser dado e não código. O `validaCena` avisa quais
imagens faltam, como aviso e não como erro.

Para trocar por arte de verdade: ponha os PNGs top-down em `data/sprites/` com
os nomes que o catálogo pede (`us-pelotao`, `us-para`, `us-bazuca`,
`us-granada`, `de-para`, `de-mg42`, `de-morteiro`, `marco`), **com o nariz para
cima**, e rode `node tools/pack.mjs`. Nenhum tempo de nenhuma cena muda.

## O que a validação pega

Roda em milissegundos e reprova a cena antes de qualquer pixel — é ela que
deixa conferir o filme sem assistir ao filme. Além do que o globo já checava
(id repetido, tiro sem instante, `at` fora da rota, alvo inexistente):

- **unidade fora do mapa.** O erro que só apareceria no vídeo: o quadro sai
  vazio e ninguém entende por quê. A checagem é contra a união das placas, e
  vale também para os `marcos` e para cada chave de câmera.
- **passo que teleporta.** Se o passo seguinte começa a mais de 25 m de onde o
  anterior parou, o pelotão pula a rua inteira num quadro. Aviso, com a
  distância em metros.
- **passo fora de ordem**, com `start` anterior ao fim do passo de antes.
- **velocidade impossível**, medida na história e não na tela (veja
  `escalaDoTempo`): acima de 15 km/h ou abaixo de 0,8 quase sempre é uma
  `duration` digitada errada, não a rota.
- **câmera que chicoteia**: mais de 260 m de viagem por segundo entre duas
  chaves. A correção é dar mais tempo ou assumir o corte.
- **zoom além da placa**: abaixo de 60 m a placa mais fina (0,27 m/px) já não
  tem pixel, e acima de 3180 m a borda do dado entra no quadro.

E um que era bug da própria validação: o alvo de um tiro definido **mais abaixo**
no arquivo aparecia como inexistente, porque o conjunto de ids era montado dentro
do mesmo laço que validava. Doze avisos falsos numa cena correta é o mesmo que
nenhum aviso.

## Atalhos

| tecla | o que faz |
|---|---|
| espaço | tocar / pausar |
| `0` | volta ao início |
| `u` | painel de tropas |
| `t` | modo rota: clicar põe ponto, clicar **em cima** de um ponto marca tiro |
| `h` | esconde os trajetos |
| `v` | esconde todos os painéis |
| `[` `]` | tamanho da unidade selecionada |
| `←` `→` | gira a unidade selecionada |

A API inteira está em `window.__mapa` — `seek`, `render`, `loadCena`,
`exportCena`, `validaCena`, `spawn`, `setRoute`, `camera`, `info`.

---

## Portões de qualidade

Não diga que terminou sem estes quatro:

1. `node tools/pack.mjs` rodou sem erro (ele compila o script embutido);
2. a cena passa em `__mapa.validaCena()` sem erros — ou `node tools/render.mjs
   --check`, que faz isso e mais;
3. um render de janela do trecho tocado foi olhado;
4. se gerou vídeo, a duração medida bate com a da cena (o render falha sozinho
   se não bater).

## Esta máquina

| item | valor |
|---|---|
| QGIS | `C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat` |
| Python | `py -3` (o `python` do PATH é o stub da Microsoft Store) |
| Node | v24 — tem `WebSocket` global, que é como o render fala com o Chrome |
| ffmpeg | `C:\Program Files\ffmpeg\bin` |
| Chrome | `C:\Program Files\Google\Chrome\Application` |
| render do mapa | ~90 s por placa a 4096×2304 |
| render do filme | ~1,4 quadros/s a 1920×1080 (52 s de filme ≈ 19 min) |

## Detalhes que mordem

**O Overpass principal vive caindo com 504.** A lista de espelhos é parte do
`fetch.mjs`, não um detalhe de operação; ele tenta um por um até um responder
JSON. Foi o `overpass.private.coffee` que respondeu primeiro, e depois o
principal voltou.

**Reescrever um arquivo com Python no Windows troca `\n` por `\r\n`**, e aí o
`pack.mjs` não achava mais o `<script>` para validar. O `match` agora aceita
`\r?\n`, mas o certo é abrir com `newline=''`.

**Um `<` dentro de uma string da cena fecharia a tag `<script>`** e mataria a
página inteira numa vírgula. O `pack.mjs` escapa para `\u003c`.

**Caminho de PNG inexistente pinta PRETO OPACO** no preenchimento raster do
QGIS, por cima de tudo. O sentinela seguro é a string vazia.

Os outros — expressão quebrada aceita em silêncio, `rand()` sem semente,
`setMaximumRandomDeviationX`, efeito no renderizador e não na camada, sombra com
borrão maior que o deslocamento — valem igual aqui e estão contados em
[`../Pacífico WW2/qgis/README.md`](../Pacífico%20WW2/qgis/README.md).
