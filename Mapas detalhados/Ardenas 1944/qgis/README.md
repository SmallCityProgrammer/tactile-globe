# Bastogne e o Bois Jacques — o banco de provas

Irmão do mapa de Pearl Harbor, e existe para poder ser **quebrado sem medo**.
Mesma máquina, paisagem oposta: lá era água com uma base no meio, aqui é terra
firme com aldeia, campo e mata.

```powershell
cd 'C:\Users\eliez\OneDrive\Desktop\Mapa\Mapas detalhados\Ardenas 1944\qgis'
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' ardenas.py
```

Com enquadramento próprio — sul, oeste, norte, leste, nome:

```powershell
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' ardenas.py 50.020 5.700 50.050 5.745 foy
```

| arquivo | o que faz |
|---|---|
| `fetch.mjs` | baixa o retângulo do Overpass (precisa de `User-Agent`, senão 406) |
| `convert.mjs` | `osm.json` → campo, mata, urbano, via, ferro, predio, agua, rio, sebe |
| `ardenas.py` | monta o projeto, grava `bastogne.qgz` e renderiza |
| `estilo.py` | a paleta e todos os símbolos deste mapa |
| `textura.py`, `sinuoso.py`, `arvores.py`, `exporta.py`, `pos.py` | cópias do mapa irmão |

O que veio do OSM: **6681 prédios**, 2340 talhões de campo, 783 de mata, 1822
vias, 168 sebes, 234 cursos d'água.

---

## O que muda em relação ao Pearl Harbor

**A terra não é deduzida.** Lá o OSM não tem o porto como polígono de água — só
existe a linha de costa — e a terra saía de poligonizar a costa contra a moldura
e ficar com as faces onde havia densidade de prédio. Aqui não há costa nenhuma:
a terra é o quadro inteiro. O passo mais delicado do outro mapa simplesmente
desaparece.

**A ondulação muda de dono.** Lá era a *terra* que ondulava, e o mar e o pátio se
refaziam a partir dela, porque partilhavam contorno. Aqui a terra **é** a
moldura: ondulá-la serrilharia a aresta do quadro. Quem ondula é o campo e a
mata, que não partilham aresta com ninguém — um vão de um metro entre dois
talhões não aparece.

**O que desenha a paisagem é o talhão.** Cada uso ganha a sua família de tons, e
dentro da família cada talhão sorteia o seu (`paleta_por_tipo`). É essa colcha
que faz as Ardenas; sem ela o mapa vira um tapete verde chapado.

**A sebe** é o detalhe que diz *bocage* em vez de divisa administrativa: um traço
escuro por baixo fecha os vãos e uma fila de copas por cima faz o volume.

---

## Uma armadilha que já mordeu duas vezes no mapa irmão

Aqui as camadas se chamam `campo`, `mata`, `via`, `sebe` — **exatamente** os
nomes das funções de estilo. Com `from estilo import *`, a variável tapa a função
e o erro só aparece na hora da chamada, não no import.

Por isso este mapa usa `import estilo as ST`. No Pearl Harbor a mesma coisa
aconteceu com `agua` e com `predios`, e das duas vezes custou uma rodada para
achar.

---

## O resto

Tudo o mais — texturas de sobrepor, telhado em SVG por escala, exportação em
camadas para o After Effects, acabamento — funciona igual e está documentado no
**[README do Pacífico WW2](../../Pacífico%20WW2/qgis/README.md)**, que é onde as
armadilhas de PyQGIS estão catalogadas.
