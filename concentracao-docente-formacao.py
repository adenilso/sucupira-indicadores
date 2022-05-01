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
notas["Nota"] = notas["Nota"].apply(lambda x: str(x))
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

docs = sheets['docentes']

wd = docs
wd = wd[wd['Categoria'] == 'PERMANENTE']
wd = wd[wd['Ano Base'] == 2020]
docsAno = wd[['Cod PPG', 'Categoria']].groupby(['Cod PPG']).count().reset_index() \
  .rename(columns={'Categoria': 'PERMANENTE'})

numinst = 2

wd = wd[['Cod PPG', 'IES', 'Nome do docente', 'Ano Base']] \
  .groupby(['Cod PPG', 'IES', 'Nome do docente']).count().reset_index() \
  .drop(columns=['Ano Base']) \
  .groupby(['Cod PPG', 'IES']).count().reset_index() \
  .sort_values(by=['Cod PPG', 'Nome do docente'], ascending=False).groupby(['Cod PPG']).head(numinst) \
  .rename(columns={'Nome do docente': 'Qte'})

wd = wd.merge(academicos, on='Cod PPG', how='inner')


numppgs = wd[['Cod PPG']].groupby('Cod PPG').count().reset_index().count()['Cod PPG']

wd = wd.sort_values(['Cod PPG', 'Qte'], ascending=False)

wd = wd.assign(IES=[i + 1 for i in range(numinst)] * numppgs)

wd = wd.merge(docsAno, on='Cod PPG')

wd = wd.merge(siglas, on=['Cod PPG'], how='left')

wd = wd.assign(Porcentagem = 100 * wd['Qte'] / wd['PERMANENTE'])

#res = wd

order = wd[wd['IES'] == 1].sort_values('Porcentagem')['Sigla'].values

wd['Sigla'] = pd.Categorical(wd['Sigla'], categories=order)

gg = (
    ggplot(wd)
    + aes(x='Sigla', y='Porcentagem', fill='IES')
    + geom_bar(stat="identity", position=position_stack(), show_legend=False)
    + theme(axis_text_x=element_text(angle=90, size=10))
    + theme(figure_size=(16.0, 9.0))
    + scale_y_continuous(limits=(0, 100))
    + labs(x="Programas", y="% Porcentagem dos Orientadores Permanentes")
    + ggtitle('Porcentagem dos Docentes Permanentes Formados nas ' + str(numinst) + ' Principais Instituições')
)

gg.save(filename='charts/concentracao-formacao.pdf')