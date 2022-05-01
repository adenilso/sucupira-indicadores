#!/usr/bin/python3

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
sheets = carregar_planilhas(sheetnames)
