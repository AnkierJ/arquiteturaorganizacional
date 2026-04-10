# Organograma Interativo

Aplicativo Streamlit para visualizar o organograma a partir do arquivo `organograma.csv`.

## Requisitos

- Python 3.10+
- Dependencias em `requirements.txt`

## Como executar

1. Instale as dependencias:

```bash
pip install -r requirements.txt
```

2. Rode o app:

```bash
streamlit run app.py
```

3. Abra no navegador o endereco exibido no terminal (normalmente `http://localhost:8501`).

## Funcionalidades

- Monta o grafo hierarquico automaticamente usando `MAT` e `LIDER`
- Visualizacao vertical (top-down) ou horizontal (left-right) com switch
- Linhas ortogonais (quebras de 90 graus) para leitura mais clara da hierarquia
- Filtro por `POSICAO`
- Busca por nome, cargo ou matricula
- Exibe detalhes por selecao de pessoa
- Exporta os dados filtrados para CSV
