#!/usr/bin/python3

import pandas as pd
import numpy as np
import io
from plotnine import *
import re
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
from collections import Counter

filename = 'Produção.xlsx'
sheets = dict()
#sheets['tcc'] = pd.read_excel(filename, sheet_name='tcc', skiprows=6)
sheets['producoes_lista'] = pd.read_excel(filename, sheet_name='producoes_lista', skiprows=5)
sheets['programas'] = pd.read_excel(filename, sheet_name='programas', skiprows=4)
sheets['docentes'] = pd.read_excel(filename, sheet_name='docentes', skiprows=6)
sheets['discentes'] = pd.read_excel(filename, sheet_name='discentes', skiprows=6)
sheets['ProdRemoverPPSPPJ'] = pd.read_excel(filename, sheet_name='ProdRemoverPPSPPJ')
for k in sheets.keys():
  print(k)
  sheets[k].to_csv('N-' + k + '.csv')
  print("Done\n")
