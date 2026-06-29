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

## Usando Supabase em vez dos CSVs

O app usa Supabase automaticamente quando `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` estiverem configurados. Sem essas variaveis, ele continua usando o SQLite local como fallback.

1. Crie um projeto no Supabase.

2. No painel do Supabase, abra **SQL Editor** e execute o arquivo:

```sql
database/schema.sql
```

O schema habilita Row Level Security em todas as tabelas e nao cria policies para `anon`/`authenticated`. Isso e intencional: o app Streamlit acessa o Supabase pelo backend com `SUPABASE_SERVICE_ROLE_KEY`, e usuarios do navegador nao devem acessar as tabelas diretamente.

3. Crie `.streamlit/secrets.toml` a partir de `.streamlit/secrets.toml.example`:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sua-service-role-key"
```

Use a service role key somente no backend/Streamlit. Nao exponha essa chave no navegador.

4. Importe os CSVs uma unica vez para popular o Supabase:

```bash
python scripts/import_csv_to_supabase.py --replace
```

O importador tambem le `.streamlit/secrets.toml`; se preferir, voce pode passar as credenciais por linha de comando com `--url` e `--key`.

Depois disso, o app le e grava em Supabase. Os arquivos CSV ficam apenas como fonte de importacao inicial ou backup manual, nao como dados hardcoded da aplicacao.

## Funcionalidades

- Monta o grafo hierarquico automaticamente usando `MAT` e `LIDER`
- Visualizacao vertical (top-down) ou horizontal (left-right) com switch
- Linhas ortogonais (quebras de 90 graus) para leitura mais clara da hierarquia
- Filtro por `POSICAO`
- Busca por nome, cargo ou matricula
- Exibe detalhes por selecao de pessoa
- Exporta os dados filtrados para CSV
