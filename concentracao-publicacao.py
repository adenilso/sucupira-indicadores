#!/usr/bin/python3

from fileinput import filename
import pandas as pd
import numpy as np
import io
from plotnine import *
import re
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
from collections import Counter

sheetnames = [
  'producoes_lista', 
  'programas', 
  'docentes', 
  'discentes', 
  'tcc'
] 

estratos = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]
estratos.reverse()

estratosRestritos = ["A1", "A2", "A3", "A4"]
estratosRestritos.reverse()

path = './'
sheets = dict([[sn, pd.read_csv(path + 'N-' + sn + '.csv', error_bad_lines=False)] for sn in sheetnames])
pesos = dict({"B4": 0.05,
               "B3": 0.10,
               "B2": 0.20,
               "B1": 0.50,
               "A4": 0.625,
               "A3": 0.75, 
               "A2": 0.875,
               "A1": 1.0,
               "C": 0
              })
cat_map = dict(
    [('DISCENTE BACHARELADO', 'GRAD'),
     ('DISCENTE DOUTORADO', 'DISCENTE'),
     ('DISCENTE DOUTORADO PROFISSIONAL', 'DISCENTE'),
     ('DISCENTE MESTRADO', 'DISCENTE'),
     ('DISCENTE MESTRADO PROFISSIONAL', 'DISCENTE'),
     ('DOCENTE COLABORADOR', 'DOCENTE COLABORADOR'),
     ('DOCENTE PERMANENTE', 'DOCENTE PERMANENTE'),
     ('DOCENTE VISITANTE', 'DOCENTE VISITANTE'),
     ('EGRESSO', 'DISCENTE'),
     ('EGRESSO_GERAL_5_ANOS', 'DISCENTE'),
     ('PARTICIPANTE EXTERNO', 'PARTICIPANTE EXTERNO'),
     ('PÓS-DOC', 'PÓS-DOC')
    ]
  )
niveismap = dict({
    "MESTRADO": "M",
    "MESTRADO/DOUTORADO": "MD",
    "MESTRADO PROFISSIONAL": "M",
    "MESTRADO PROFISSIONAL/DOUTORADO PROFISSIONAL": "MD",
    "DOUTORADO": "D"
  })

producoes = sheets['producoes_lista']
docentes = sheets['docentes']
programas = sheets['programas']
campos = ["Cod PPG", "Sigla", "Nome PPG", "Modalidade", "Ano Início Nível", "Nível"]
siglas = programas \
  .rename(columns={"IES Principal Sigla": "Sigla"}) \
  .groupby(campos) \
  .size() \
  .reset_index() \
  [campos]
notas = programas[["Cod PPG", "Nota"]]
notas.loc["Nota"] = notas["Nota"].apply(lambda x: str(x))
siglas = pd.merge(siglas[campos], notas, on="Cod PPG")
siglas['NotaStr'] = siglas['Nota'].apply(lambda x: str(x))
siglas['Modalidade'] = siglas['Modalidade'].apply(lambda x: x[0])
siglas['Ano Início Nível'] = siglas['Ano Início Nível'].apply(lambda x: x[0:4])

for key, value in niveismap.items():
  siglas.loc[siglas['Nível'] == key, ['Nível']] = value

siglas['Acronym'] = siglas['Nome PPG'] \
  .apply(lambda x: ''.join(map(lambda s: s[0], filter(lambda s: len(s) > 5, x.split(' ')))))
siglas['SiglaTmp'] = siglas['Sigla'] +  \
  '-' + siglas['Acronym'] + \
  '-' + siglas['NotaStr'] + \
  ' (' + siglas['Nível'] + '-' + siglas['Modalidade'] + '-' + siglas['Ano Início Nível'] + ')'
siglas['Sigla'] = siglas['SiglaTmp']
siglas=siglas.drop(columns=['Nome PPG', 'Nota', 'NotaStr', 'Acronym', 'SiglaTmp', 'Modalidade', 'Ano Início Nível', 'Nível'])
siglas=siglas.groupby(['Cod PPG', 'Sigla']).sum().reset_index()
anos=programas[['Cod PPG', 'Ano Base']].groupby(['Cod PPG']).size().reset_index().rename(columns={0: 'QteAnos'})

academicos = programas[programas['Modalidade'] == 'ACADÊMICO'][['Cod PPG']].groupby('Cod PPG').count().reset_index()
profissionais = programas[programas['Modalidade'] == 'PROFISSIONAL'][['Cod PPG']].groupby('Cod PPG').count().reset_index()

def sumarizar_autores(prod):
  wd = prod
  wd = wd[
                (wd['Subtipo'].isin(["ARTIGO EM PERIÓDICO", "TRABALHO EM ANAIS"])) &
                (wd['Natureza'] == "TRABALHO COMPLETO")
      ]
  wd = wd[wd['ID_ADD_PRODUCAO_INTELECTUAL'].notnull()]
  wd = wd[['Cod PPG', 'ID_ADD_PRODUCAO_INTELECTUAL', 'NM_AUTORES']]
  idsProd = wd['ID_ADD_PRODUCAO_INTELECTUAL'].values.tolist()
  wdsplt = [str(l).split(' | ') for l in wd['NM_AUTORES'].values]
  cols = ['ID_ADD_PRODUCAO_INTELECTUAL'] + list(range(max([len(x) for x in wdsplt])))
  wdsplt = [[idsProd[i]] + wdsplt[i] for i in range(len(wdsplt))]
  wdsplt = pd.DataFrame(wdsplt, columns=cols)
  wd = wd.merge(wdsplt, on='ID_ADD_PRODUCAO_INTELECTUAL', how='left')
  wd = wd.melt(id_vars=['Cod PPG', 'ID_ADD_PRODUCAO_INTELECTUAL', 'NM_AUTORES'], var_name="Pos", value_name="NomeCat")
  wd = wd[wd["NomeCat"].notnull()]
  wd.loc[:, ['NomeRe']] = wd['NomeCat'].apply(lambda x: re.search('(.*) \((.*)\)', x))
  wd.loc[wd['NomeRe'].isnull(), ['Nome']] = wd.loc[wd['NomeRe'].isnull(), ['NM_AUTORES']]
  wd.loc[wd['NomeRe'].isnull(), ['Cat']] = 'NOCAT'
  wd.loc[wd['NomeRe'].notnull(), ['Nome', 'Cat']] = wd[wd['NomeRe'].notnull()]['NomeRe'].apply(lambda x: x.group(1))
  wd.loc[wd['NomeRe'].notnull(), ['Cat']] = wd[wd['NomeRe'].notnull()]['NomeRe'].apply(lambda x: cat_map[x.group(2)])
  wd = wd.drop(columns=["NM_AUTORES", "NomeCat", "NomeRe"])
  wd['Pos'] = wd['Pos'] + 1
  wd = prod[['Cod PPG', 'Estrato', 'ID_ADD_PRODUCAO_INTELECTUAL', 'Subtipo', 'Natureza', 'Ano base']].merge(wd, on=['Cod PPG', 'ID_ADD_PRODUCAO_INTELECTUAL'], how='right')
  wd = wd.rename(columns={'ID_ADD_PRODUCAO_INTELECTUAL': 'idProd', 'Nome': 'Nome do docente'})

  return wd

def juntar_dados_gini(data, dqte, nome='Nome do docente', qte="Qte"):
  d = pd.DataFrame(data.loc[:, ['Cod PPG', nome]].groupby(['Cod PPG', nome]).size().reset_index().values, columns=['Cod PPG', nome, 'dummy'])
  qte_pub = pd.DataFrame(pd.DataFrame(dqte.groupby([nome, 'Cod PPG']).size()).reset_index().values, columns=[nome, "Cod PPG", qte])
  res = pd.merge(d, qte_pub, on=[nome, 'Cod PPG'], how="left")
  res = res.fillna(0.0)
  res = res.groupby(['Cod PPG']).apply(lambda x: gini(np.array(x['Qte']))).reset_index().rename(columns={0: 'Gini'})
  return res

def juntar_dados_hist(data, autores, nome='Nome do docente', qte="Qte"):
  d = pd.DataFrame(data.loc[:, ['Cod PPG', nome]].groupby(['Cod PPG', nome]).size().reset_index().values, columns=['Cod PPG', nome, 'dummy'])
  qte_pub = pd.DataFrame(pd.DataFrame(autores.groupby([nome, 'Cod PPG']).size()).reset_index().values, columns=[nome, "Cod PPG", qte])
  res = pd.merge(d, qte_pub, on=[nome, 'Cod PPG'], how="left")
  res[qte] = res[qte].fillna(0.0)
  return res

sumario_autores = sumarizar_autores(producoes)

def plotCapela(data, nome='Nome do docente', qte='Qte'):
  d = data.loc[:, ['Cod PPG', 'Nome do docente', 'Qte']].groupby(['Cod PPG', 'Nome do docente']).sum().reset_index().sort_values(by=["Cod PPG", "Qte"], ascending=True)
  r = pd.merge(d, siglas, on=['Cod PPG'], how="left").sort_values(by="Sigla", kind="stable")
  r = r.assign(idx=range(len(r.index)))
  idxgrp = r.loc[:, ['Sigla', 'idx']].groupby('Sigla')
  idxmin = idxgrp.min().reset_index().rename({'idx': 'min'})
  idxmax = idxgrp.max().reset_index().rename({'idx': 'max'})
  breaks = pd.merge(idxmin, idxmax, on="Sigla")
  breaks = breaks.assign(pos=(breaks['idx_x'] + breaks['idx_y']) / 2)
  labels = breaks['Sigla'].values.tolist()
  xbreaks = breaks['pos'].values.tolist()
  gg = (
    ggplot(r)
    + aes(x='idx', y='Qte')
    + theme(figure_size=(16.0, 9.0))
    + geom_area(fill='blue')
    + theme(axis_text_x=element_text(angle=90, size=6))    
    + scale_x_continuous(labels=labels, breaks=xbreaks)
  )
  return gg

def adicionar_percentis(gg, data, col="Qte", percentis=[0, 0.25, 0.5, 0.75, 1], nomes=["Min", "1Q", "Mediana", "3Q", "Max"]):
    wd = data[["Sigla", col]].groupby(["Sigla"]).sum().reset_index()
    parts = [0, 0.25, 0.5, 0.75, 1]
    mid = wd['Sigla'].count() / 2
    #return mid
    d = []
    for i in range(len(percentis)):
      p = percentis[i]
      n = nomes[i]
      d.append([1, mid, np.round(wd[col].quantile(p), 2), n])
    #return wd
    t = pd.DataFrame(data=d, columns=['x', 'mid', 'y', 'l'])
    color='black'
    ngg = (
        gg
        + geom_hline(t, aes(yintercept = 'y'), color=color)
        + geom_label(t, aes(x='x', y='y', label='l'), fill='white', ha='left', va='top', color=color)
        + geom_label(t, aes(x='mid', y='y', label='y'), fill='white', ha='left', va='top', color=color)
    )
    return ngg

def gini(array):
    """Calculate the Gini coefficient of a numpy array."""
    # based on bottom eq: http://www.statsdirect.com/help/content/image/stat0206_wmf.gif
    # from: http://www.statsdirect.com/help/default.htm#nonparametric_methods/gini.htm
    #array = array.flatten() #all values are treated equally, arrays must be 1d
    if np.amin(array) < 0:
        array -= np.amin(array) #values cannot be negative
    array += 0.0000001 #values cannot be 0
    array = np.sort(array) #values must be sorted
    index = np.arange(1,array.shape[0]+1) #index per array element
    n = array.shape[0]#number of array elements
    return ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array))) #Gini coefficient

def plotHist(data, col='Gini', addmedian=False):
  wd = data
  wd = pd.merge(wd, siglas, on=['Cod PPG'], how='left')
  order=wd[['Sigla', col]].groupby(by='Sigla')[col].max().sort_values().keys().tolist()
  order.reverse()
  sigla_cat = pd.Categorical(wd['Sigla'], categories=order)
  wd = wd.assign(Sigla = sigla_cat)
  gg = (
      ggplot(wd)
      + aes(x='Sigla', y=col)
      + geom_bar(stat='identity', fill='blue', color='blue')
      + theme(figure_size=(16.0, 9.0))
      + theme(axis_text_x=element_text(angle=90, size=10))
  )
  if addmedian:
    gg = adicionar_percentis(gg, wd, col="Gini")
    return gg
    parts = [0, 0.25, 0.5, 0.75, 1]
    m = [r[col].quantile(p) for p in parts]
    t = pd.DataFrame(data=[[1, r[col].quantile(p),'{0:2.0f}%'.format(p*100)] for p in parts], columns=['x', 'y', 'l'])
    color='black'
    #return t
    gg = (
        gg
        + geom_hline(t, aes(yintercept = 'y'), color=color)
        + geom_label(t, aes(x='x', y='y', label='l'), ha='left', va='top', color=color)
    )
  return gg

autores_per = sumario_autores[
  (sumario_autores['Subtipo'].isin(["ARTIGO EM PERIÓDICO"])) & 
  (sumario_autores['Estrato'].isin(estratos)) &
  (sumario_autores['Natureza'] == 'TRABALHO COMPLETO')
]

docs = docentes \
         [docentes['Categoria'] == 'PERMANENTE'] \
         .merge(academicos, on='Cod PPG', how='inner')
auts = sumario_autores[
         (sumario_autores['Subtipo'].isin(["ARTIGO EM PERIÓDICO"])) & 
         (sumario_autores['Estrato'].isin(estratosRestritos)) &
         (sumario_autores['Natureza'] == 'TRABALHO COMPLETO')
       ]

gg = plotCapela( juntar_dados_hist(docs, auts)) \
     + labs(x="Programas", y="Quantidade de Artigos em Periódicos em Estrato Restrito") \
     + ggtitle('Distribuição Interna da Publicações dos Programas entre os Docentes Permanentes')

gg.save(filename='charts/concentracao-producacao.pdf')

gg = plotHist(juntar_dados_gini(
       docs, 
       auts
     ), addmedian=True) \
     + labs(x="Programas", y="Gini da Quantidade de Artigos em Periódicos em Estrato Restrito") \
     + ggtitle('Gini da Distribuição Interna da Publicações dos Programas entre os Docentes Permanentes') \
     + scale_y_continuous(limits=(0, 1))
    
gg.save(filename='charts/concentracao-producacao-gini.pdf')
