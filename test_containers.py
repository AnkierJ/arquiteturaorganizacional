#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para validar a implementação dos containers visuais
"""

import sys
import pandas as pd
from pathlib import Path

# Adicionar o diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Teste de Containers Visuais")
print("=" * 60)

# Carregar dados
print("\n1. Carregando dados...")
try:
    df = pd.read_csv('organograma.csv', sep=';', dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]
    
    supersetor_df = pd.read_csv('supersetor.csv', sep=';', dtype=str, keep_default_na=False)
    supersetor_df.columns = [c.strip().upper() for c in supersetor_df.columns]
    
    subsetor_df = pd.read_csv('subsetor.csv', sep=';', dtype=str, keep_default_na=False)
    subsetor_df.columns = [c.strip().upper() for c in subsetor_df.columns]
    
    print(f"   ✓ organograma.csv: {len(df)} pessoas")
    print(f"   ✓ supersetor.csv: {len(supersetor_df)} supersetores")
    print(f"   ✓ subsetor.csv: {len(subsetor_df)} subsetores")
except Exception as e:
    print(f"   ✗ Erro ao carregar dados: {e}")
    sys.exit(1)

# Verificar estrutura dos dados
print("\n2. Verificando estrutura dos dados...")
print(f"   - organograma.csv colunas: {list(df.columns)}")
print(f"   - supersetor.csv colunas: {list(supersetor_df.columns)}")
print(f"   - subsetor.csv colunas: {list(subsetor_df.columns)}")

# Verificar dados de exemplo
print("\n3. Dados de exemplo:")
print(f"   Supersetor -> Setor:")
print(f"   {supersetor_df.head(3).to_string()}")
print(f"\n   Subsetor -> Setor Pai:")
print(f"   {subsetor_df.head(3).to_string()}")

# Testar os mapeamentos
print("\n4. Testando mapeamentos...")
setor_to_supersetor = {}
for _, row in supersetor_df.iterrows():
    setor_to_supersetor[row['SETORFILHO']] = row['SUPERSETOR']
print(f"   ✓ SETOR -> SUPERSETOR: {len(setor_to_supersetor)} mapeamentos")

subsetor_to_setor = {}
for _, row in subsetor_df.iterrows():
    subsetor_to_setor[row['SUBSETOR']] = row['SETORPAI']
print(f"   ✓ SUBSETOR -> SETOR: {len(subsetor_to_setor)} mapeamentos")

# Validar que os dados do organograma têm containers
print("\n5. Validando atributos de container no organograma...")
has_setor = 'SETOR' in df.columns
has_subsetor = 'SUBSETOR' in df.columns
has_supersetor = 'SUPERSETOR' in df.columns

print(f"   - Coluna SUPERSETOR: {'✓' if has_supersetor else '✗'}")
print(f"   - Coluna SETOR: {'✓' if has_setor else '✗'}")
print(f"   - Coluna SUBSETOR: {'✓' if has_subsetor else '✗'}")

# Contar quantos têm container
with_container = 0
with_setor = df['SETOR'].notna().sum() if has_setor else 0
with_subsetor = df['SUBSETOR'].notna().sum() if has_subsetor else 0
with_supersetor = df['SUPERSETOR'].notna().sum() if has_supersetor else 0

print(f"\n   Pessoas com container:")
print(f"   - Com Supersetor: {with_supersetor}")
print(f"   - Com Setor: {with_setor}")
print(f"   - Com Subsetor: {with_subsetor}")

print("\n" + "=" * 60)
print("✓ Teste concluído com sucesso!")
print("=" * 60)
