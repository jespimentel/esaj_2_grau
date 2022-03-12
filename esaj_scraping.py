# This file is part of eSAJ_scraping 1.0.
# Copyright 2022, José Eduardo de Souza Pimentel.

""" Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. """

import requests
import pandas as pd
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from tkinter import filedialog, Tk

print ('\nBem vindo ao eSAJ Scraping 1.0 do Pimentel!')
print ('------------------------------------------\n')

data_e_hora_em_texto = datetime.now().strftime('%Y-%m-%d_%Hh%Mmin')

# Criação das listas vazias
lista_consulta = []
lista_resultados = []
lista_erros = []
lista_inconclusivos = []
lista_arquivos = []

def encontra_processos (linha_de_texto):
    """Encontra os números de processos (CNJ) únicos nas linhas de texto examinadas."""
    resultado = re.findall(r'[0-9]{7}[-][0-9]{2}[.][0-9]{4}[.][8][.][2][6][.][0-9]{4}', 
                           linha_de_texto)
    for r in resultado:
        if r not in lista_arquivos:
            lista_arquivos.append(r) 
            
def ler_arquivo(path_do_arquivo):
    file = open(path_do_arquivo, encoding='latin-1')
    for line in file:
       encontra_processos(line)
    print(f'Encontrei {len(lista_arquivos)} processos únicos.')
    return lista_arquivos

def pesquisa_processo(num_proc):
    """Retorna o html (content) da pesquisa"""
    params = (
    ('conversationId', ''),
    ('paginaConsulta', '0'),
    ('cbPesquisa', 'NUMPROC'),
    ('numeroDigitoAnoUnificado', num_proc),
    ('foroNumeroUnificado', num_proc[-4:]),
    ('dePesquisaNuUnificado', [num_proc, 'UNIFICADO']),
    ('dePesquisa', ''),
    ('tipoNuProcesso', 'UNIFICADO'),)
    return requests.get('https://esaj.tjsp.jus.br/cposg/search.do', params=params).content

def separa_dados(resultado):
    lista=[]
    for n in resultado:
        lista.append(n.text.strip())
    return lista

def extrai_dados(lista_consulta):
    for n_processo in lista_consulta: 
        html = pesquisa_processo(n_processo)
        soup = BeautifulSoup(html, 'html.parser')
        time.sleep(0.2)

        try:
            msg = soup.find(id='mensagemRetorno').text.strip()
            if msg:
                lista_erros.append([n_processo, msg])
                arquivo = open('nao_encontrados.txt', 'a')
                arquivo.write(n_processo + ' - ' + msg + ' - ' + data_e_hora_em_texto + '\n')
                arquivo.close
                
        except:
            try:
                # Número do processo
                numero = soup.find(id='numeroProcesso').text.strip()
                
                # Órgão julgador 
                orgao = soup.find(id='orgaoJulgadorProcesso').text.strip()
                
                # Relator do processo
                relator = soup.find(id='relatorProcesso').text.strip()
                
                # Classe do processo
                classe = soup.find(id='classeProcesso').text.strip()
                
                # Assunto
                assunto = soup.find(id='assuntoProcesso').text.strip()
                
                # Situação do processo
                situacao = soup.find(id='situacaoProcesso').text.strip()
                
                # Parte e advogado
                parte = soup.find(class_='nomeParteEAdvogado').text.strip()
                parte = parte.replace('\n', '')
                parte = parte.replace('\t', '')
                parte = parte.replace('  ', '')
                
                # Resultado final
                resultado =  soup.find_all('table')[-1].find_all('td')
                
                # Inclusão na lista de resultados
                lista_resultados.append([numero, orgao, relator, classe, 
                                         assunto, situacao, parte, separa_dados(resultado)])     

            except:
                try:
                    paginacao = soup.find(class_='resultadoPaginacao').text.strip()
                    lista_inconclusivos.append([n_processo, paginacao])
                    arquivo = open('inconclusivos.txt', 'a')
                    arquivo.write(n_processo + ' - ' + paginacao + ' - ' + data_e_hora_em_texto + '\n')
                    arquivo.close
                    
                except:
                    arquivo = open('nao_encontrados.txt', 'a')
                    arquivo.write(n_processo + ' - ' + data_e_hora_em_texto + '\n')
                    arquivo.close                

# Pesquisa por 'atos.csv' ou equivalente
ano = input('Entre com o ano de referência: ')
nome_pj = input('Entre com o nome do Procurador/PJ/Grupo/Foro/Vara: ')
print ('Selecione o arquivo texto ou csv com os números dos processos')

root = Tk()
root.withdraw() # Oculta a janela raiz
file = filedialog.askopenfilename()
print ('Aguarde o processamento...')
lista_arquivos = ler_arquivo(file)
extrai_dados(lista_arquivos)

columns = ['Número do processo', 'Órgão Julgador', 'Relator', 'Classe',
           'Assunto', 'Situação', 'Recorrente(s)', 'Desfecho']
df = pd.DataFrame(lista_resultados, columns = columns)
df['Data'] = df['Desfecho'].str[0]
df['Status'] = df['Desfecho'].str[1]
df['Resultado'] = df['Desfecho'].str[2]
df = df.drop(columns='Desfecho')

# Processos em "segredo de justiça" ou não existentes em 2o. Grau
columns = ['Número do processo', 'Informação']
df_erros = pd.DataFrame(lista_erros, columns=columns)

columns = ['Número do processo', 'Observações']
df_inconclusivos = pd.DataFrame(lista_inconclusivos, columns=columns)

# Criação de uma planilha Excel com o resultado do trabalho
with pd.ExcelWriter(f'{nome_pj}_{ano}_resultado_dos_recursos_{data_e_hora_em_texto}.xlsx') as writer:  
  df.to_excel(writer, sheet_name='resultados')
  df_erros.to_excel (writer, sheet_name='erros ou não processados')
  df_inconclusivos.to_excel(writer, sheet_name='inconclusivos')

# Criação de um arquivo texto com o resultado do trabalho
with open(f'{nome_pj}_{ano}_resultado_dos_recursos_{data_e_hora_em_texto}.txt', 'w') as arquivo:
    arquivo.write (f'Resultado dos processos recebidos pelo [Procurador/PJ/Grupo/Vara] {nome_pj} no ano {ano} julgados pelo TJSP\n\n\n')
    for l in lista_resultados:
        arquivo.write (f'\nNúmero do processo: {l[0]}\n')
        arquivo.write (f'Órgão Julgador: {l[1]}\n')
        arquivo.write (f'Relator: {l[2]}\n')
        arquivo.write (f'Classe: {l[3]}\n')
        arquivo.write (f'Assunto: {l[4]}\n')
        arquivo.write (f'Situação: {l[5]}\n')
        arquivo.write (f'Recorrente: {l[6]}\n')
        try:
            arquivo.write (f'Data: {l[7][0]}\n')
            arquivo.write (f'Status: {l[7][1]}\n')
            arquivo.write (f'Resultado: {l[7][2]}\n\n')
            arquivo.write ('*' * 40 +'\n')
        except:
            arquivo.write ('*' * 40 +'\n')
    arquivo.write ('\n\n\nRelatório emitido em: '+ data_e_hora_em_texto)
    arquivo.write ('\nDesenvolvido em Python por @jespimentel')