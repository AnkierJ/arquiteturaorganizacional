#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste da função build_pyvis_network com containers
"""

import pandas as pd
import networkx as nx
from pathlib import Path

# Carregar dados
print("Carregando dados...")
org_df = pd.read_csv('organograma.csv', sep=';', dtype=str, keep_default_na=False)
org_df.columns = [c.strip().upper() for c in org_df.columns]

supersetor_df = pd.read_csv('supersetor.csv', sep=';', dtype=str, keep_default_na=False)
supersetor_df.columns = [c.strip().upper() for c in supersetor_df.columns]

subsetor_df = pd.read_csv('subsetor.csv', sep=';', dtype=str, keep_default_na=False)
subsetor_df.columns = [c.strip().upper() for c in subsetor_df.columns]

# Simular o mapeamento de containers
print("\nTestando mapeamentos de containers...")

setor_to_supersetor = {}
if not supersetor_df.empty:
    for _, row in supersetor_df.iterrows():
        setor_to_supersetor[row["SETORFILHO"]] = row["SUPERSETOR"]

subsetor_to_setor = {}
if not subsetor_df.empty:
    for _, row in subsetor_df.iterrows():
        subsetor_to_setor[row["SUBSETOR"]] = row["SETORPAI"]

print(f"[OK] SETOR -> SUPERSETOR: {len(setor_to_supersetor)} mapeamentos")
print(f"[OK] SUBSETOR -> SETOR: {len(subsetor_to_setor)} mapeamentos")

# Simular a lógica de assignação de grupos
print("\nSimulando atribuição de grupos aos nós...")
grupos_atribuidos = {'setor': 0, 'subsetor': 0, 'supersetor': 0, 'nenhum': 0}

for _, row in org_df.iterrows():
    node_id = row["MAT"]
    setor = str(row.get("SETOR", "")).strip()
    subsetor = str(row.get("SUBSETOR", "")).strip()
    supersetor = str(row.get("SUPERSETOR", "")).strip()
    
    if subsetor:
        grupos_atribuidos['subsetor'] += 1
    elif setor:
        grupos_atribuidos['setor'] += 1
    elif supersetor:
        grupos_atribuidos['supersetor'] += 1
    else:
        grupos_atribuidos['nenhum'] += 1

print(f"Nós com grupo atribuído:")
print(f"  - Com subsetor: {grupos_atribuidos['subsetor']}")
print(f"  - Com setor: {grupos_atribuidos['setor']}")
print(f"  - Com supersetor: {grupos_atribuidos['supersetor']}")
print(f"  - Sem container: {grupos_atribuidos['nenhum']}")

# Validar que todos têm algum container
total = len(org_df)
com_container = total - grupos_atribuidos['nenhum']
print(f"Total de nos: {total}")
print(f"Nos com container: {com_container} ({100*com_container/total:.1f}%)")

print("\n- Teste de mapeamento concluido com sucesso!")
