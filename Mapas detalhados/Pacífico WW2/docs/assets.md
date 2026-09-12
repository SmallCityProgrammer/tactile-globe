# Os assets do mapa

Tudo o que a carta desenha passa por um **slot**, e todo slot aceita um PNG seu.
São **194** deles. Não existe nada desenhado fora desta tabela — nem
a água, nem a textura do convés, nem a linha internacional de data.

> Esta página é gerada por `node tools/asset-doc.mjs` a partir da tabela
> `ASSETS` do `src/template.html`. Não edite à mão.

---

## Como um slot vira imagem

Toda marca do mapa chama `glyph()`, `tile()` ou `stamp()`, e essas três
resolvem o slot **nesta ordem**:

1. **o PNG que você soltou** — guardado no IndexedDB do navegador, sobrevive a
   recarregar a página, funciona até em `file://`;
2. **o PNG embutido no arquivo** — o que estava em `data/assets.json` na hora
   do `node tools/pack.mjs`;
3. **o desenho em código** — o fallback em `DRAW[id]`, que nunca some.

O botão `imagem` (tecla `I`) desliga 1 e 2 de uma vez, então dá para comparar
a sua arte com o desenho em código a qualquer momento.

---

## Trocar um asset

Abra `assets.html`, ou `pacifico.html#assets`, ou aperte `A` no mapa.

| ação | efeito |
|---|---|
| arrastar um PNG **para cima de um quadro** | troca aquele slot |
| soltar **vários PNG** em qualquer lugar da página | cada arquivo vai para o slot de mesmo nome (`dd.png` → contratorpedeiro) |
| **clicar no quadro** | baixa o desenho atual em PNG, no tamanho e na proporção certos, para pintar por cima |
| `↺` no canto do quadro | devolve aquele slot ao desenho em código |
| `exportar assets.json` | gera o arquivo que o `pack.mjs` embute |
| `importar assets.json` | carrega um conjunto inteiro de uma vez |
| `restaurar tudo` | limpa o IndexedDB |

Para que a troca entre no arquivo final:

```
# exporte assets.json pela página, salve em data/, e:
node tools/pack.mjs
```

---

## As três espécies de slot

| espécie | o que é | como o mapa usa |
|---|---|---|
| **glyph** | um carimbo num ponto | desenha centrado em (x, y), na largura pedida, girado se o slot girar |
| **tile** | uma textura | vira `createPattern(..., 'repeat')`; **tem que ladrilhar sem costura** |
| **line** | um carimbo repetido | plantado ao longo de uma polilinha, girado para a tangente |

### Convenções que a sua arte tem que respeitar

- **Proa/frente para a ESQUERDA.** Tudo que gira é desenhado apontando para −x:
  um navio com a proa em −x, um avião com o nariz em −x, uma seta apontando
  para −x. Um PNG com a proa para cima vai aparecer navegando de lado.
- **Âncora.** Quase tudo é ancorado pelo centro. Os slots marcados *base* na
  tabela (monte, vulcão) crescem a partir do chão: o ponto de ancoragem é o
  meio da borda de baixo.
- **Fundo transparente.** O mapa desenha o mar debaixo.
- **A coluna `tamanho`** é o tamanho real que aquilo tem no mundo, em metros.
  O mapa divide pelo metros-por-pixel da vista para saber de quantos pixels
  precisa. Num *tile* é o lado de uma repetição.
- **Resolução.** O gabarito que o botão baixa tem 256 px de largura; qualquer
  coisa entre 128 e 512 px serve. Acima disso só engorda o arquivo — o mapa
  raramente desenha um glifo com mais de 300 px.

---

## O catálogo


### o mar — 8 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `mar.png` | água aberta | textura que se repete | 120 km | — | 256 × 256 |
| `mar_raso.png` | água rasa (plataforma) | textura que se repete | 60 km | — | 256 × 256 |
| `vaga.png` | vaga / ondulação | carimbo num ponto | 900 m | sim | 256 × 256 |
| `carneiro.png` | carneiro (crista branca) | carimbo num ponto | 260 m | sim | 256 × 256 |
| `rebentacao.png` | rebentação na costa | carimbo repetido ao longo de uma linha | 700 m | — | 256 × 102 |
| `corrente.png` | corrente marinha | carimbo repetido ao longo de uma linha | 40 km | — | 256 × 102 |
| `isobata.png` | isóbata | carimbo repetido ao longo de uma linha | 30 km | — | 256 × 102 |
| `sonda.png` | sonda (número de profundidade) | carimbo num ponto | 9 km | — | 256 × 256 |

### a terra — 10 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `praia.png` | praia | carimbo repetido ao longo de uma linha | 1,2 km | — | 256 × 102 |
| `recife.png` | recife de coral | textura que se repete | 2,6 km | — | 256 × 256 |
| `selva.png` | selva | textura que se repete | 1,8 km | — | 256 × 256 |
| `palmeira.png` | coqueiro | carimbo num ponto | 14 m | sim | 256 × 256 |
| `arvore.png` | árvore da mata | carimbo num ponto | 22 m | sim | 256 × 256 |
| `monte.png` | monte / serra | carimbo num ponto | 9 km *(base)* | — | 256 × 179 |
| `vulcao.png` | vulcão | carimbo num ponto | 11 km *(base)* | — | 256 × 179 |
| `pista.png` | pista de pouso | carimbo num ponto | 1,8 km | sim | 256 × 256 |
| `vila.png` | povoado | carimbo num ponto | 900 m | — | 256 × 256 |
| `cais.png` | cais e molhe | carimbo num ponto | 600 m | sim | 256 × 256 |

### navios — 22 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `cv.png` | porta-aviões de esquadra | carimbo num ponto | 260 m | sim | 256 × 256 |
| `cvl.png` | porta-aviões leve | carimbo num ponto | 190 m | sim | 256 × 256 |
| `cve.png` | porta-aviões de escolta | carimbo num ponto | 150 m | sim | 256 × 256 |
| `bb.png` | encouraçado | carimbo num ponto | 240 m | sim | 256 × 256 |
| `bc.png` | cruzador de batalha | carimbo num ponto | 240 m | sim | 256 × 256 |
| `ca.png` | cruzador pesado | carimbo num ponto | 190 m | sim | 256 × 256 |
| `cl.png` | cruzador leve | carimbo num ponto | 160 m | sim | 256 × 256 |
| `claa.png` | cruzador antiaéreo | carimbo num ponto | 160 m | sim | 256 × 256 |
| `dd.png` | contratorpedeiro | carimbo num ponto | 115 m | sim | 256 × 256 |
| `de.png` | escolta | carimbo num ponto | 95 m | sim | 256 × 256 |
| `ss.png` | submarino | carimbo num ponto | 95 m | sim | 256 × 256 |
| `pt.png` | lancha torpedeira | carimbo num ponto | 24 m | sim | 256 × 256 |
| `ap.png` | transporte | carimbo num ponto | 135 m | sim | 256 × 256 |
| `ao.png` | petroleiro de esquadra | carimbo num ponto | 165 m | sim | 256 × 256 |
| `av.png` | navio-base de hidroaviões | carimbo num ponto | 185 m | sim | 256 × 256 |
| `lst.png` | navio de desembarque | carimbo num ponto | 100 m | sim | 256 × 256 |
| `lc.png` | barcaça de desembarque | carimbo num ponto | 15 m | sim | 256 × 256 |
| `esteira.png` | esteira | carimbo repetido ao longo de uma linha | 400 m | — | 256 × 102 |
| `fumaca.png` | fumaça de chaminé | carimbo num ponto | 300 m | sim | 256 × 256 |
| `incendio.png` | incêndio a bordo | carimbo num ponto | 60 m | — | 256 × 256 |
| `adernado.png` | navio adernado | carimbo num ponto | 160 m | sim | 256 × 256 |
| `naufragio.png` | naufrágio (mancha de óleo) | carimbo num ponto | 700 m | — | 256 × 256 |

### convés — 10 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `chapeamento.png` | chapeamento do convés | textura que se repete | 12 m | — | 256 × 256 |
| `convoo.png` | convés de voo (marcação) | textura que se repete | 30 m | — | 256 × 256 |
| `torre.png` | torre de artilharia | carimbo num ponto | 22 m | sim | 256 × 256 |
| `superestrutura.png` | superestrutura / ilha | carimbo num ponto | 40 m | sim | 256 × 256 |
| `chamine.png` | chaminé | carimbo num ponto | 12 m | sim | 256 × 256 |
| `aa.png` | reparo antiaéreo | carimbo num ponto | 6 m | sim | 256 × 256 |
| `catapulta.png` | catapulta | carimbo num ponto | 20 m | sim | 256 × 256 |
| `elevador.png` | elevador de aeronaves | carimbo num ponto | 16 m | sim | 256 × 256 |
| `bote.png` | escaler | carimbo num ponto | 9 m | sim | 256 × 256 |
| `marinheiro.png` | marinheiro | carimbo num ponto | 1,8 m | sim | 256 × 256 |

### aeronaves — 11 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `caca_jp.png` | caça japonês (Zero) | carimbo num ponto | 12 m | sim | 256 × 256 |
| `caca_us.png` | caça americano (Hellcat) | carimbo num ponto | 13 m | sim | 256 × 256 |
| `mergulho_jp.png` | bombardeiro de mergulho japonês | carimbo num ponto | 14 m | sim | 256 × 256 |
| `mergulho_us.png` | bombardeiro de mergulho americano | carimbo num ponto | 13 m | sim | 256 × 256 |
| `torpedeiro_jp.png` | torpedeiro japonês (Kate) | carimbo num ponto | 16 m | sim | 256 × 256 |
| `torpedeiro_us.png` | torpedeiro americano (Avenger) | carimbo num ponto | 17 m | sim | 256 × 256 |
| `patrulha.png` | hidroavião de patrulha | carimbo num ponto | 32 m | sim | 256 × 256 |
| `bombardeiro.png` | bombardeiro pesado | carimbo num ponto | 43 m | sim | 256 × 256 |
| `kamikaze.png` | kamikaze | carimbo num ponto | 12 m | sim | 256 × 256 |
| `formacao.png` | formação aérea (símbolo) | carimbo num ponto | 9 km | sim | 256 × 256 |
| `busca.png` | setor de busca aérea | carimbo repetido ao longo de uma linha | 60 km | — | 256 × 102 |

### combate — 7 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `explosao.png` | explosão | carimbo num ponto | 90 m | — | 256 × 256 |
| `coluna.png` | coluna de água (tiro curto) | carimbo num ponto | 70 m | — | 256 × 256 |
| `flak.png` | rebentamento antiaéreo | carimbo num ponto | 50 m | — | 256 × 256 |
| `torpedo.png` | esteira de torpedo | carimbo repetido ao longo de uma linha | 900 m | — | 256 × 102 |
| `fogo.png` | clarão de salva | carimbo num ponto | 45 m | sim | 256 × 256 |
| `holofote.png` | holofote | carimbo num ponto | 4 km | sim | 256 × 256 |
| `bomba.png` | bomba em queda | carimbo num ponto | 8 m | sim | 256 × 256 |

### marcadores — 16 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `batalha.png` | marco de batalha | carimbo num ponto | 90 km | — | 256 × 256 |
| `batalha_ar.png` | marco de ação aérea | carimbo num ponto | 90 km | — | 256 × 256 |
| `batalha_sub.png` | marco de ação submarina | carimbo num ponto | 90 km | — | 256 × 256 |
| `desembarque.png` | marco de desembarque | carimbo num ponto | 90 km | — | 256 × 256 |
| `base_jp.png` | base japonesa | carimbo num ponto | 55 km | — | 256 × 256 |
| `base_us.png` | base americana | carimbo num ponto | 55 km | — | 256 × 256 |
| `base_al.png` | base aliada | carimbo num ponto | 55 km | — | 256 × 256 |
| `ancoradouro.png` | ancoradouro | carimbo num ponto | 55 km | — | 256 × 256 |
| `aerodromo.png` | campo de aviação | carimbo num ponto | 55 km | — | 256 × 256 |
| `arsenal.png` | arsenal | carimbo num ponto | 55 km | — | 256 × 256 |
| `estreito.png` | estreito | carimbo num ponto | 55 km | — | 256 × 256 |
| `bandeira_jp.png` | pavilhão japonês | carimbo num ponto | 40 km | — | 256 × 256 |
| `bandeira_us.png` | pavilhão americano | carimbo num ponto | 40 km | — | 256 × 256 |
| `bandeira_al.png` | pavilhão aliado | carimbo num ponto | 40 km | — | 256 × 256 |
| `seta_jp.png` | ponta de seta japonesa | carimbo num ponto | 60 km | sim | 256 × 256 |
| `seta_us.png` | ponta de seta aliada | carimbo num ponto | 60 km | sim | 256 × 256 |

### carta — 5 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `papel.png` | fundo / papel da carta | textura que se repete | 400 km | — | 256 × 256 |
| `rosa.png` | rosa dos ventos | carimbo num ponto | 500 km | — | 256 × 256 |
| `meridiano.png` | cruz do meridiano | carimbo num ponto | 60 km | — | 256 × 256 |
| `linha_data.png` | linha internacional de data | carimbo repetido ao longo de uma linha | 200 km | — | 256 × 102 |
| `perimetro.png` | perímetro japonês | carimbo repetido ao longo de uma linha | 150 km | — | 256 × 102 |

### classes — 105 slots

| arquivo | o que é | espécie | tamanho | gira | gabarito |
|---|---|---|---|---|---|
| `navio_yamato.png` | Yamato (BB, 263 m) | carimbo num ponto | 263 m | sim | 256 × 256 |
| `navio_nagato.png` | Nagato (BB, 225 m) | carimbo num ponto | 225 m | sim | 256 × 256 |
| `navio_ise.png` | Ise (BB, 216 m) | carimbo num ponto | 216 m | sim | 256 × 256 |
| `navio_ise-hybrid.png` | Ise (hybrid battleship-carrier, 1943) (BB, 220 m) | carimbo num ponto | 220 m | sim | 256 × 256 |
| `navio_fuso.png` | Fuso (BB, 213 m) | carimbo num ponto | 213 m | sim | 256 × 256 |
| `navio_kongo.png` | Kongo (BB, 222 m) | carimbo num ponto | 222 m | sim | 256 × 256 |
| `navio_akagi.png` | Akagi (CV, 261 m) | carimbo num ponto | 261 m | sim | 256 × 256 |
| `navio_kaga.png` | Kaga (CV, 248 m) | carimbo num ponto | 248 m | sim | 256 × 256 |
| `navio_soryu.png` | Soryu (CV, 228 m) | carimbo num ponto | 228 m | sim | 256 × 256 |
| `navio_hiryu.png` | Hiryu (CV, 227 m) | carimbo num ponto | 227 m | sim | 256 × 256 |
| `navio_shokaku.png` | Shokaku (CV, 258 m) | carimbo num ponto | 258 m | sim | 256 × 256 |
| `navio_zuikaku.png` | Zuikaku (CV, 258 m) | carimbo num ponto | 258 m | sim | 256 × 256 |
| `navio_hiyo.png` | Hiyo (CV, 219 m) | carimbo num ponto | 219 m | sim | 256 × 256 |
| `navio_ryujo.png` | Ryujo (CVL, 180 m) | carimbo num ponto | 180 m | sim | 256 × 256 |
| `navio_zuiho.png` | Zuiho (CVL, 206 m) | carimbo num ponto | 206 m | sim | 256 × 256 |
| `navio_shoho.png` | Shoho (CVL, 206 m) | carimbo num ponto | 206 m | sim | 256 × 256 |
| `navio_taiho.png` | Taiho (CV, 261 m) | carimbo num ponto | 261 m | sim | 256 × 256 |
| `navio_unryu.png` | Unryu (CV, 227 m) | carimbo num ponto | 227 m | sim | 256 × 256 |
| `navio_shinano.png` | Shinano (CV, 266 m) | carimbo num ponto | 266 m | sim | 256 × 256 |
| `navio_chitose-av.png` | Chitose (seaplane tender) (AV, 193 m) | carimbo num ponto | 193 m | sim | 256 × 256 |
| `navio_chitose-cvl.png` | Chitose (light carrier, 1943) (CVL, 193 m) | carimbo num ponto | 193 m | sim | 256 × 256 |
| `navio_takao.png` | Takao (CA, 204 m) | carimbo num ponto | 204 m | sim | 256 × 256 |
| `navio_mogami.png` | Mogami (CA, 201 m) | carimbo num ponto | 201 m | sim | 256 × 256 |
| `navio_mogami-cav.png` | Mogami (aviation cruiser, 1943) (CA, 201 m) | carimbo num ponto | 201 m | sim | 256 × 256 |
| `navio_tone.png` | Tone (CA, 202 m) | carimbo num ponto | 202 m | sim | 256 × 256 |
| `navio_myoko.png` | Myoko (CA, 204 m) | carimbo num ponto | 204 m | sim | 256 × 256 |
| `navio_nachi.png` | Nachi (Myoko class) (CA, 204 m) | carimbo num ponto | 204 m | sim | 256 × 256 |
| `navio_aoba.png` | Aoba (CA, 185 m) | carimbo num ponto | 185 m | sim | 256 × 256 |
| `navio_furutaka.png` | Furutaka (CA, 185 m) | carimbo num ponto | 185 m | sim | 256 × 256 |
| `navio_agano.png` | Agano (CL, 175 m) | carimbo num ponto | 175 m | sim | 256 × 256 |
| `navio_oyodo.png` | Oyodo (CL, 192 m) | carimbo num ponto | 192 m | sim | 256 × 256 |
| `navio_sendai.png` | Sendai (CL, 162 m) | carimbo num ponto | 162 m | sim | 256 × 256 |
| `navio_nagara.png` | Nagara (CL, 162 m) | carimbo num ponto | 162 m | sim | 256 × 256 |
| `navio_kuma.png` | Kuma (CL, 162 m) | carimbo num ponto | 162 m | sim | 256 × 256 |
| `navio_tenryu.png` | Tenryu (CL, 143 m) | carimbo num ponto | 143 m | sim | 256 × 256 |
| `navio_fubuki.png` | Fubuki (DD, 118 m) | carimbo num ponto | 118 m | sim | 256 × 256 |
| `navio_kagero.png` | Kagero (DD, 119 m) | carimbo num ponto | 119 m | sim | 256 × 256 |
| `navio_yugumo.png` | Yugumo (DD, 119 m) | carimbo num ponto | 119 m | sim | 256 × 256 |
| `navio_shimakaze.png` | Shimakaze (DD, 130 m) | carimbo num ponto | 130 m | sim | 256 × 256 |
| `navio_akizuki.png` | Akizuki (DD, 134 m) | carimbo num ponto | 134 m | sim | 256 × 256 |
| `navio_asashio.png` | Asashio (DD, 118 m) | carimbo num ponto | 118 m | sim | 256 × 256 |
| `navio_matsu.png` | Matsu (DE, 100 m) | carimbo num ponto | 100 m | sim | 256 × 256 |
| `navio_i-400.png` | I-400 (Sentoku) (SS, 122 m) | carimbo num ponto | 122 m | sim | 256 × 256 |
| `navio_i-15.png` | I-15 (Type B1) (SS, 109 m) | carimbo num ponto | 109 m | sim | 256 × 256 |
| `navio_i-19.png` | I-19 (Type B1) (SS, 109 m) | carimbo num ponto | 109 m | sim | 256 × 256 |
| `navio_ro-100.png` | Ro-100 (Type KS) (SS, 61 m) | carimbo num ponto | 61 m | sim | 256 × 256 |
| `navio_shinyo-cve.png` | Shinyo (CVE, 198 m) | carimbo num ponto | 198 m | sim | 256 × 256 |
| `navio_shinyo-boat.png` | Shinyo suicide motorboat (PT, 5 m) | carimbo num ponto | 5 m | sim | 256 × 256 |
| `navio_akitsu-maru.png` | Akitsu Maru (LST, 152 m) | carimbo num ponto | 152 m | sim | 256 × 256 |
| `navio_maru-transport.png` | Standard 'Maru' transport (Type 2A) (AP, 133 m) | carimbo num ponto | 133 m | sim | 256 × 256 |
| `navio_daihatsu.png` | Daihatsu landing barge (LC, 15 m) | carimbo num ponto | 15 m | sim | 256 × 256 |
| `navio_iowa.png` | Iowa (BB, 270 m) | carimbo num ponto | 270 m | sim | 256 × 256 |
| `navio_south-dakota.png` | South Dakota (BB, 210 m) | carimbo num ponto | 210 m | sim | 256 × 256 |
| `navio_north-carolina.png` | North Carolina (BB, 222 m) | carimbo num ponto | 222 m | sim | 256 × 256 |
| `navio_colorado.png` | Colorado (BB, 190 m) | carimbo num ponto | 190 m | sim | 256 × 256 |
| `navio_tennessee.png` | Tennessee (BB, 190 m) | carimbo num ponto | 190 m | sim | 256 × 256 |
| `navio_new-mexico.png` | New Mexico (BB, 190 m) | carimbo num ponto | 190 m | sim | 256 × 256 |
| `navio_pennsylvania.png` | Pennsylvania (BB, 185 m) | carimbo num ponto | 185 m | sim | 256 × 256 |
| `navio_nevada.png` | Nevada (BB, 178 m) | carimbo num ponto | 178 m | sim | 256 × 256 |
| `navio_lexington.png` | Lexington (CV, 271 m) | carimbo num ponto | 271 m | sim | 256 × 256 |
| `navio_yorktown.png` | Yorktown (CV, 251 m) | carimbo num ponto | 251 m | sim | 256 × 256 |
| `navio_essex.png` | Essex (CV, 266 m) | carimbo num ponto | 266 m | sim | 256 × 256 |
| `navio_independence.png` | Independence (CVL, 190 m) | carimbo num ponto | 190 m | sim | 256 × 256 |
| `navio_casablanca.png` | Casablanca (CVE) (CVE, 156 m) | carimbo num ponto | 156 m | sim | 256 × 256 |
| `navio_bogue.png` | Bogue (CVE) (CVE, 151 m) | carimbo num ponto | 151 m | sim | 256 × 256 |
| `navio_baltimore.png` | Baltimore (CA, 205 m) | carimbo num ponto | 205 m | sim | 256 × 256 |
| `navio_portland.png` | Portland (CA, 186 m) | carimbo num ponto | 186 m | sim | 256 × 256 |
| `navio_new-orleans.png` | New Orleans (CA, 179 m) | carimbo num ponto | 179 m | sim | 256 × 256 |
| `navio_northampton.png` | Northampton (CA, 183 m) | carimbo num ponto | 183 m | sim | 256 × 256 |
| `navio_pensacola.png` | Pensacola (CA, 179 m) | carimbo num ponto | 179 m | sim | 256 × 256 |
| `navio_brooklyn.png` | Brooklyn (CL, 185 m) | carimbo num ponto | 185 m | sim | 256 × 256 |
| `navio_cleveland.png` | Cleveland (CL, 186 m) | carimbo num ponto | 186 m | sim | 256 × 256 |
| `navio_atlanta.png` | Atlanta (CLAA, 165 m) | carimbo num ponto | 165 m | sim | 256 × 256 |
| `navio_omaha.png` | Omaha (CL, 169 m) | carimbo num ponto | 169 m | sim | 256 × 256 |
| `navio_fletcher.png` | Fletcher (DD, 115 m) | carimbo num ponto | 115 m | sim | 256 × 256 |
| `navio_sumner.png` | Allen M. Sumner (DD, 115 m) | carimbo num ponto | 115 m | sim | 256 × 256 |
| `navio_gearing.png` | Gearing (DD, 119 m) | carimbo num ponto | 119 m | sim | 256 × 256 |
| `navio_benson.png` | Benson (DD, 106 m) | carimbo num ponto | 106 m | sim | 256 × 256 |
| `navio_farragut.png` | Farragut (DD, 104 m) | carimbo num ponto | 104 m | sim | 256 × 256 |
| `navio_porter.png` | Porter (DD, 116 m) | carimbo num ponto | 116 m | sim | 256 × 256 |
| `navio_gato.png` | Gato (SS, 95 m) | carimbo num ponto | 95 m | sim | 256 × 256 |
| `navio_balao.png` | Balao (SS, 95 m) | carimbo num ponto | 95 m | sim | 256 × 256 |
| `navio_tambor.png` | Tambor (SS, 94 m) | carimbo num ponto | 94 m | sim | 256 × 256 |
| `navio_pt-elco80.png` | PT boat (Elco 80 ft) (PT, 24 m) | carimbo num ponto | 24 m | sim | 256 × 256 |
| `navio_lst.png` | LST-1 (LST, 100 m) | carimbo num ponto | 100 m | sim | 256 × 256 |
| `navio_lci.png` | LCI(L) (LC, 48 m) | carimbo num ponto | 48 m | sim | 256 × 256 |
| `navio_lcvp.png` | LCVP (Higgins boat) (LC, 11 m) | carimbo num ponto | 11 m | sim | 256 × 256 |
| `navio_lsm.png` | LSM (LST, 62 m) | carimbo num ponto | 62 m | sim | 256 × 256 |
| `navio_liberty.png` | Liberty ship (EC2-S-C1) (AP, 135 m) | carimbo num ponto | 135 m | sim | 256 × 256 |
| `navio_cimarron.png` | Cimarron (AO) (AO, 169 m) | carimbo num ponto | 169 m | sim | 256 × 256 |
| `navio_prince-of-wales.png` | Prince of Wales (King George V) (BB, 227 m) | carimbo num ponto | 227 m | sim | 256 × 256 |
| `navio_repulse.png` | Repulse (Renown) (BC, 242 m) | carimbo num ponto | 242 m | sim | 256 × 256 |
| `navio_illustrious.png` | Illustrious (CV, 230 m) | carimbo num ponto | 230 m | sim | 256 × 256 |
| `navio_exeter.png` | Exeter (York class) (CA, 175 m) | carimbo num ponto | 175 m | sim | 256 × 256 |
| `navio_perth.png` | HMAS Perth (Leander, Amphion group) (CL, 171 m) | carimbo num ponto | 171 m | sim | 256 × 256 |
| `navio_de-ruyter.png` | HNLMS De Ruyter (CL, 171 m) | carimbo num ponto | 171 m | sim | 256 × 256 |
| `navio_java.png` | HNLMS Java (CL, 155 m) | carimbo num ponto | 155 m | sim | 256 × 256 |
| `navio_mahan.png` | Mahan (DD, 104 m) | carimbo num ponto | 104 m | sim | 256 × 256 |
| `navio_benham.png` | Benham (DD, 104 m) | carimbo num ponto | 104 m | sim | 256 × 256 |
| `navio_sims.png` | Sims (DD, 106 m) | carimbo num ponto | 106 m | sim | 256 × 256 |
| `navio_johncbutler.png` | John C. Butler (DE, 93 m) | carimbo num ponto | 93 m | sim | 256 × 256 |
| `navio_shiratsuyu.png` | Shiratsuyu (DD, 108 m) | carimbo num ponto | 108 m | sim | 256 × 256 |
| `navio_hatsuharu.png` | Hatsuharu (DD, 110 m) | carimbo num ponto | 110 m | sim | 256 × 256 |
| `navio_county.png` | County (CA, 192 m) | carimbo num ponto | 192 m | sim | 256 × 256 |
| `navio_tribal.png` | Tribal (DD, 115 m) | carimbo num ponto | 115 m | sim | 256 × 256 |

---

## O grupo `classes`

Os 105 slots `navio_*` são gerados do banco de classes
(`data/history.json`): um por classe de navio. Eles têm **precedência sobre o
slot de tipo**, então:

- `navio_yamato.png` desenha só o Yamato;
- `bb.png` desenha qualquer encouraçado que não tenha ficha própria;
- sem nenhum dos dois, o código monta o casco em planta a partir das medidas da
  classe (comprimento, boca, disposição das torres, convés de voo).

É por isso que dá para trocar um navio de cada vez sem tocar nos outros.

Para desenhar um casco novo do zero, veja **[design/README.md](../design/README.md)**:
tem um gerador de vistas em planta em SVG, com o Yamato e a Iowa prontos.
