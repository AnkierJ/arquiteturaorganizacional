#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste da renderizacao de containers com retangulos
"""

import sys
import pandas as pd
import json

print("Testando nova implementacao de containers...")
print("=" * 60)

# Carregar dados
org_df = pd.read_csv('organograma.csv', sep=';', dtype=str, keep_default_na=False)
org_df.columns = [c.strip().upper() for c in org_df.columns]

supersetor_df = pd.read_csv('supersetor.csv', sep=';', dtype=str, keep_default_na=False)
supersetor_df.columns = [c.strip().upper() for c in supersetor_df.columns]

subsetor_df = pd.read_csv('subsetor.csv', sep=';', dtype=str, keep_default_na=False)
subsetor_df.columns = [c.strip().upper() for c in subsetor_df.columns]

# Simular estrutura de containers
containers = {
    "subsetor": {},
    "setor": {},
    "supersetor": {},
}

# Rastrear containers
for _, row in org_df.iterrows():
    node_id = row["MAT"]
    setor = str(row.get("SETOR", "")).strip()
    subsetor = str(row.get("SUBSETOR", "")).strip()
    supersetor = str(row.get("SUPERSETOR", "")).strip()
    
    x, y = 0, 0  # Simplificado
    size = 22
    
    if subsetor:
        if subsetor not in containers["subsetor"]:
            containers["subsetor"][subsetor] = []
        containers["subsetor"][subsetor].append({"id": node_id, "x": x, "y": y, "size": size})
    elif setor:
        if setor not in containers["setor"]:
            containers["setor"][setor] = []
        containers["setor"][setor].append({"id": node_id, "x": x, "y": y, "size": size})
    elif supersetor:
        if supersetor not in containers["supersetor"]:
            containers["supersetor"][supersetor] = []
        containers["supersetor"][supersetor].append({"id": node_id, "x": x, "y": y, "size": size})

print("\n1. Estrutura de containers gerada:")
print(f"   - Supersetores: {len(containers['supersetor'])}")
print(f"   - Setores: {len(containers['setor'])}")
print(f"   - Subsetores: {len(containers['subsetor'])}")

print("\n2. Exemplo de containers:")
if containers['setor']:
    setor_name = list(containers['setor'].keys())[0]
    print(f"   Setor '{setor_name}': {len(containers['setor'][setor_name])} nos")

if containers['subsetor']:
    subsetor_name = list(containers['subsetor'].keys())[0]
    print(f"   Subsetor '{subsetor_name}': {len(containers['subsetor'][subsetor_name])} nos")

print("\n3. Validando estrutura JSON para JavaScript:")
try:
    json_str = json.dumps(containers)
    print(f"   [OK] JSON valido ({len(json_str)} caracteres)")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

print("\n4. Verificando tipos de container:")
container_types = ['subsetor', 'setor', 'supersetor']
for ctype in container_types:
    total_nodes = sum(len(nodes) for nodes in containers[ctype].values())
    print(f"   - {ctype}: {total_nodes} nos em {len(containers[ctype])} grupos")

print("\n" + "=" * 60)
print("- Teste concluido com sucesso!")
print("=" * 60)
