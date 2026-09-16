# telhado.py — uma BIBLIOTECA de telhados, e a regra que escolhe qual usar.
#
# A IDEIA, QUE NAO FOI MINHA
# Eu tinha argumentado que asset pronto nao servia: sprite tem proporcao fixa,
# predio do OSM tem forma arbitraria, logo deformaria. O argumento so vale se a
# saida for ESTICAR UM sprite para caber em tudo. Se em vez disso se ESCOLHE qual
# sprite, deixa de ser deformacao e vira classificacao — e ai funciona.
#
# Uma casa de aldeia, um celeiro comprido, um galpao industrial e um anexo de
# fundo de quintal sao coisas diferentes vistas de cima, e o OSM ja diz qual e
# qual, indiretamente: pelo tamanho e pelo alongamento da caixa minima orientada.
#
# O QUE TORNA ISSO POSSIVEL NO QGIS
# Property.Name troca o ARQUIVO SVG por feicao. (Property.File existe, aparece na
# lista de propriedades como "Symbol file path", e e um no-op silencioso — o
# render ignora. Isso foi medido, nao lido.)
#
# POR QUE CADA UM TEM O SEU viewBox
# Width e Height vao data-defined e SEPARADOS, entao o SVG e esticado para
# exatamente comp x larg, seja qual for o viewBox. O viewBox decide QUANTO
# estica: um celeiro 4:1 desenhado num quadro 4:1 chega esticado de ~1. E esse o
# ganho de escolher por classe em vez de esticar um so.
#
# REGRA DO DESENHO: tudo que e fino tem que ser HORIZONTAL. O esticao em x e
# quase sempre maior que o em y, entao um traco vertical engorda e um horizontal
# guarda a espessura. Cumeeira, beiral e clarabóia correm todos em x.
import os

# --------------------------------------------------------------- as pecas
def _corpo(w, h):
    return ('<rect x="0" y="0" width="{w}" height="{h}" fill="param(fill) #565b5f"/>'
            .format(w=w, h=h))

def _duas_aguas(w, h, claro=0.11, escuro=0.15):
    """Duas aguas com cumeeira no meio: a de cima pega luz, a de baixo nao."""
    m = h / 2.0
    return (
        '<rect x="0" y="0" width="{w}" height="{a}" fill="#ffffff" fill-opacity="{c}"/>'
        '<rect x="0" y="{b}" width="{w}" height="{a}" fill="#000000" fill-opacity="{e}"/>'
        '<rect x="0" y="{r}" width="{w}" height="{rh}" fill="param(outline) #23271f" fill-opacity="0.50"/>'
        .format(w=w, a=m - 1, b=m + 1, c=claro, e=escuro, r=m - 1.5, rh=3)
    )

def _oitoes(w, h, prof=None):
    """Os oitoes: a agua morre num triangulo em cada ponta."""
    p = prof if prof else w * 0.11
    return ('<polygon points="0,0 {p},{m} 0,{h}" fill="#000000" fill-opacity="0.10"/>'
            '<polygon points="{w},0 {q},{m} {w},{h}" fill="#000000" fill-opacity="0.10"/>'
            .format(p=p, q=w - p, m=h / 2.0, w=w, h=h))

def _beiral(w, h):
    """O beiral: fio de luz em cima, sombra grossa embaixo. E o que assenta o
    predio no chao — sem ele o telhado flutua."""
    return ('<rect x="0" y="0" width="{w}" height="3" fill="#ffffff" fill-opacity="0.22"/>'
            '<rect x="0" y="{y}" width="{w}" height="{e}" fill="#000000" fill-opacity="0.30"/>'
            .format(w=w, y=h - h * 0.07, e=h * 0.07))

def _svg(w, h, miolo):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            'viewBox="0 0 {w} {h}">\n  {m}\n</svg>\n'.format(w=w, h=h, m=miolo))

# --------------------------------------------------------------- a biblioteca
def _casa():
    w, h = 200, 100
    return _svg(w, h, _corpo(w, h) + _duas_aguas(w, h) + _oitoes(w, h) + _beiral(w, h))

def _celeiro():
    """Comprido, cumeeira longa, e a porta grande numa das pontas."""
    w, h = 420, 100
    porta = ('<rect x="{x}" y="{y}" width="{pw}" height="{ph}" fill="#000000" fill-opacity="0.22"/>'
             .format(x=w * 0.03, y=h * 0.30, pw=w * 0.07, ph=h * 0.40))
    return _svg(w, h, _corpo(w, h) + _duas_aguas(w, h, 0.13, 0.17)
                + _oitoes(w, h, w * 0.05) + porta + _beiral(w, h))

def _galpao():
    """Agua baixa e clarabóias correndo no comprimento. E o que diz industria."""
    w, h = 260, 100
    luz = ''.join('<rect x="{x}" y="{y}" width="{lw}" height="6" fill="#ffffff" fill-opacity="0.20"/>'
                  .format(x=w * 0.06, y=y, lw=w * 0.88) for y in (20, 47, 74))
    return _svg(w, h, _corpo(w, h)
                + '<rect x="0" y="0" width="{w}" height="{a}" fill="#ffffff" fill-opacity="0.06"/>'
                  .format(w=w, a=h / 2.0)
                + luz + _beiral(w, h))

def _anexo():
    """Agua unica: em vez de cumeeira, quatro faixas caindo de cima para baixo.
    Faixa, e nao gradiente, porque gradiente de SVG e uma aposta a mais no
    renderizador do Qt e aqui nao precisa."""
    w, h = 120, 100
    faixas = ''.join('<rect x="0" y="{y}" width="{w}" height="{fh}" fill="#000000" fill-opacity="{o}"/>'
                     .format(y=i * h / 4.0, w=w, fh=h / 4.0 + 0.5, o=0.02 + i * 0.055)
                     for i in range(4))
    return _svg(w, h, _corpo(w, h) + faixas + _beiral(w, h))

def _bloco():
    """Laje plana com platibanda e duas caixas de maquina em cima."""
    w, h = 150, 100
    poco = ('<rect x="{i}" y="{j}" width="{a}" height="{b}" fill="#000000" fill-opacity="0.13"/>'
            .format(i=w * 0.10, j=h * 0.13, a=w * 0.80, b=h * 0.74))
    maq = ''.join('<rect x="{x}" y="{y}" width="{a}" height="{b}" fill="#000000" fill-opacity="0.20"/>'
                  .format(x=w * fx, y=h * 0.30, a=w * 0.16, b=h * 0.22) for fx in (0.22, 0.56))
    return _svg(w, h, _corpo(w, h) + poco + maq + _beiral(w, h))

BIBLIOTECA = {'casa': _casa, 'celeiro': _celeiro, 'galpao': _galpao,
              'anexo': _anexo, 'bloco': _bloco}

def grava(pasta, grava_svg):
    """Escreve a biblioteca e devolve {nome: caminho}."""
    return {n: grava_svg(pasta, 'tel_' + n, f()) for n, f in BIBLIOTECA.items()}

# --------------------------------------------------------------- a regra
# As faixas sao em METROS, medidas da caixa minima orientada de cada predio.
# 'comp' e o lado longo, 'larg' o curto, 'alonga' a razao entre eles.
#
# A ordem importa: o CASE para no primeiro ramo verdadeiro, e o anexo tem que ser
# testado antes do celeiro, senao um galinheiro comprido e estreito viraria um
# celeiro de 40 metros.
def escolhe(caminhos):
    p = {n: c.replace('\\', '/') for n, c in caminhos.items()}
    return (
        "CASE"
        "  WHEN \"larg\" < 7 OR \"comp\" * \"larg\" < 70 THEN '{anexo}'"
        "  WHEN \"alonga\" > 3.0 AND \"comp\" > 26 THEN '{celeiro}'"
        "  WHEN \"comp\" * \"larg\" > 1100 THEN '{galpao}'"
        "  WHEN \"comp\" > 26 AND \"alonga\" < 1.7 THEN '{bloco}'"
        "  ELSE '{casa}' END".format(**p)
    )
