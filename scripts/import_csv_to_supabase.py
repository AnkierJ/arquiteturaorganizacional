import argparse
import os
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"


COLLABORATOR_COLUMNS = ["MAT", "NOME", "CARGO", "SUPERSETOR", "SETOR", "SUBSETOR", "LIDER", "POSICAO", "OBSERVACOES"]
COLLABORATOR_MAP = {
    "MAT": "mat",
    "NOME": "nome",
    "CARGO": "cargo",
    "SUPERSETOR": "supersetor",
    "SETOR": "setor",
    "SUBSETOR": "subsetor",
    "LIDER": "lider",
    "POSICAO": "posicao",
    "OBSERVACOES": "observacoes",
}


def parse_simple_toml_value(value: str) -> str:
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_streamlit_secrets(path: Path = SECRETS_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        import tomllib

        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return {str(key): str(value) for key, value in data.items()}
    except ModuleNotFoundError:
        secrets: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line or line.startswith("["):
                continue
            key, value = line.split("=", 1)
            secrets[key.strip()] = parse_simple_toml_value(value)
        return secrets


def config_value(name: str, secrets: dict[str, str]) -> str:
    return os.getenv(name, "").strip() or str(secrets.get(name, "") or "").strip()


def read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    df.columns = [col.strip().upper() for col in df.columns]
    for col in columns:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df[columns].copy()


def to_rows(df: pd.DataFrame, mapping: dict[str, str], key_column: str, sort_order: bool = False) -> list[dict]:
    rows = []
    clean = df[df[key_column].astype(str).str.strip() != ""].reset_index(drop=True)
    for idx, row in clean.iterrows():
        payload = {db_col: str(row.get(app_col, "") or "").strip() for app_col, db_col in mapping.items()}
        if sort_order:
            payload["sort_order"] = int(idx)
        rows.append(payload)
    return rows


def execute(query):
    return query.execute()


def insert_batches(client, table: str, rows: list[dict], on_conflict: str, batch_size: int = 500) -> None:
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        if batch:
            execute(client.table(table).upsert(batch, on_conflict=on_conflict))


def replace_table(client, table: str, filter_column: str) -> None:
    execute(client.table(table).delete().neq(filter_column, ""))


def main() -> None:
    secrets = load_streamlit_secrets()
    parser = argparse.ArgumentParser(description="Importa os CSVs locais para tabelas do Supabase.")
    parser.add_argument("--url", default=config_value("SUPABASE_URL", secrets), help="URL do projeto Supabase.")
    parser.add_argument(
        "--key",
        default=config_value("SUPABASE_SERVICE_ROLE_KEY", secrets),
        help="Service role key do Supabase.",
    )
    parser.add_argument("--organograma", type=Path, default=BASE_DIR / "organograma.csv")
    parser.add_argument("--setores", type=Path, default=BASE_DIR / "setores.csv")
    parser.add_argument("--supersetor", type=Path, default=BASE_DIR / "supersetor.csv")
    parser.add_argument("--subsetor", type=Path, default=BASE_DIR / "subsetor.csv")
    parser.add_argument("--replace", action="store_true", help="Limpa as tabelas importadas antes de inserir.")
    args = parser.parse_args()

    if not args.url or not args.key:
        raise SystemExit(
            "Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY em .streamlit/secrets.toml, "
            "em variaveis de ambiente, ou passe --url e --key."
        )

    try:
        from supabase import create_client
    except ModuleNotFoundError as exc:
        raise SystemExit("Pacote supabase nao instalado. Rode: pip install -r requirements.txt") from exc

    client = create_client(args.url, args.key)

    colaboradores = read_csv(args.organograma, COLLABORATOR_COLUMNS)
    colaboradores = colaboradores.drop_duplicates(subset=["MAT"], keep="last")

    setores = read_csv(args.setores, ["SETOR", "LIDERMAT"])
    setores = setores[setores["SETOR"] != ""].drop_duplicates(subset=["SETOR"], keep="last")

    supersetores = read_csv(args.supersetor, ["SUPERSETOR", "SETORFILHO", "LIDERMAT"])
    supersetores = supersetores[(supersetores["SUPERSETOR"] != "") & (supersetores["SETORFILHO"] != "")]
    supersetores = supersetores.drop_duplicates(subset=["SETORFILHO"], keep="last")

    subsetores = read_csv(args.subsetor, ["SUBSETOR", "SETORPAI", "LIDERMAT"])
    subsetores = subsetores[(subsetores["SUBSETOR"] != "") & (subsetores["SETORPAI"] != "")]
    subsetores = subsetores.drop_duplicates(subset=["SUBSETOR"], keep="last")

    if args.replace:
        replace_table(client, "colaboradores", "mat")
        replace_table(client, "hierarchy_setores", "setor")
        replace_table(client, "hierarchy_supersetores", "setorfilho")
        replace_table(client, "hierarchy_subsetores", "subsetor")

    insert_batches(client, "colaboradores", to_rows(colaboradores, COLLABORATOR_MAP, "MAT"), "mat")
    insert_batches(
        client,
        "hierarchy_setores",
        to_rows(setores, {"SETOR": "setor", "LIDERMAT": "lidermat"}, "SETOR", sort_order=True),
        "setor",
    )
    insert_batches(
        client,
        "hierarchy_supersetores",
        to_rows(
            supersetores,
            {"SUPERSETOR": "supersetor", "SETORFILHO": "setorfilho", "LIDERMAT": "lidermat"},
            "SETORFILHO",
            sort_order=True,
        ),
        "setorfilho",
    )
    insert_batches(
        client,
        "hierarchy_subsetores",
        to_rows(
            subsetores,
            {"SUBSETOR": "subsetor", "SETORPAI": "setorpai", "LIDERMAT": "lidermat"},
            "SUBSETOR",
            sort_order=True,
        ),
        "subsetor",
    )

    print(f"Importados {len(colaboradores)} colaboradores")
    print(f"Importados {len(setores)} setores")
    print(f"Importados {len(supersetores)} relacoes de supersetor")
    print(f"Importados {len(subsetores)} relacoes de subsetor")


if __name__ == "__main__":
    main()
