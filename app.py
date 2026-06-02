import tempfile
import json
import base64
import html
import sqlite3
import statistics
import urllib.parse
from collections import defaultdict, deque
from pathlib import Path

import networkx as nx
import pandas as pd
import streamlit as st
from PIL import Image
from pyvis.network import Network


BRAND_BLUE = "#14315E"
BRAND_GREEN = "#2FD68B"
BRAND_WHITE = "#FFFFFF"
COLLABORATOR_COLUMNS = ["MAT", "NOME", "CARGO", "SUPERSETOR", "SETOR", "SUBSETOR", "LIDER", "POSICAO", "OBSERVACOES"]
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "organograma.db"
COLLABORATORS_CSV_PATH = BASE_DIR / "organograma.csv"
SETORES_CSV_PATH = BASE_DIR / "setores.csv"
SUPERSETORES_CSV_PATH = BASE_DIR / "supersetor.csv"
SUBSETORES_CSV_PATH = BASE_DIR / "subsetor.csv"
KALK_BO_LOGO_PATH = BASE_DIR / "assets/KALK_BO.png"
KALK_BO_ICON_PATH = BASE_DIR / "assets/KALK_BO_icon.png"
KALK_STATUS_COLORS = {
    "pending": "#C8CED8",
    "green": "#15a979",
    "yellow": "#fff32b",
    "red": "#ff3131",
}
ORG_CHART_COMPONENT = st.components.v1.declare_component(
    "org_chart_component",
    path=str((Path(__file__).parent / "components" / "org_chart_component").resolve()),
)


ICON_PATH = BASE_DIR / "assets/logoOrganograma.png"
PAGE_ICON = Image.open(ICON_PATH) if ICON_PATH.exists() else None

st.set_page_config(
    page_title="Organograma Interativo",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF;
    }
    .brand-title {
        color: #14315E;
        font-size: 8.4rem;
        font-weight: 700;
        margin: 0.35rem 0 0 0;
        text-align: center;
        padding: 0 !important;
    }
    .brand-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        align-content: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0 0 1.15rem 0;
        margin-bottom: 0.75rem;
    }
    .brand-logo {
        max-height: 80px;
        max-width: 80px;
        object-fit: contain;
        display: block;
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(20, 49, 94, 0.15);
    }
    .stMetric {
        border: 1px solid rgba(20, 49, 94, 0.12);
        border-radius: 10px;
        padding: 0.35rem 0.5rem;
        background: linear-gradient(180deg, rgba(47,214,139,0.08), rgba(20,49,94,0.03));
    }
    .detail-card {
        border: 1px solid rgba(20, 49, 94, 0.14);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        background: linear-gradient(180deg, rgba(47,214,139,0.08), rgba(20,49,94,0.02));
        margin: 0.4rem 0 0.8rem 0;
    }
    .detail-card-title {
        color: #14315E;
        font-size: 1.08rem;
        font-weight: 800;
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }
    .detail-card-subtitle {
        color: #2b3f66;
        font-size: 0.92rem;
        margin: 0 0 0.7rem 0;
        line-height: 1.35;
    }
    .detail-card-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.45rem 0.75rem;
    }
    .detail-card-field {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(20, 49, 94, 0.08);
        border-radius: 10px;
        padding: 0.45rem 0.6rem;
    }
    .detail-card-label {
        color: #6b7a95;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin: 0;
    }
    .detail-card-value {
        color: #14315E;
        font-size: 0.92rem;
        font-weight: 700;
        margin: 0.1rem 0 0 0;
        line-height: 1.25;
    }
    .filter-card-title {
        color: #14315E;
        font-size: 1.02rem;
        font-weight: 800;
        margin: 0 0 0.3rem 0;
    }
    .filter-card-caption {
        color: #53657f;
        font-size: 0.84rem;
        margin: 0.15rem 0 0 0;
        line-height: 1.35;
    }
    div[data-testid="stToggle"] label p {
        font-size: 0.85rem;
    }
    .visualization-header {
        display: flex;
        align-items: center;
        min-height: 2.4rem;
        text-align: center;
        align-content: center;
    }
    .visualization-header h3 {
        margin: 0;
        line-height: 1.2;
        text-align: center;
        padding: 0;
    }
    div[class*="st-key-horizontal_view"] {
        display: flex;
        align-items: center;
        min-height: 2.4rem;
    }
    div[class*="st-key-horizontal_view"] label {
        margin: 0;
        display: flex;
        align-items: center;
    }
    div[data-testid="stButton"] button img {
        width: 28px;
        height: 28px;
        object-fit: contain;
        margin-right: 0.35rem;
    }
    div[class*="st-key-open_kalk_bo_button"] button {
        min-height: 40px !important;
        height: 40px !important;
        padding: 0 0.75rem !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 0.5rem !important;
        background: #ffffff !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[class*="st-key-open_kalk_bo_button"] button:hover {
        border-color: rgba(20, 49, 94, 0.45) !important;
        background: #ffffff !important;
        box-shadow: none !important;
    }
    div[class*="st-key-open_kalk_bo_button"] button p {
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0;
        line-height: 1.6rem;
        color: #052966;
        font-size: 1rem;
    }
    div[class*="st-key-open_kalk_bo_button"] button img {
        height: 32px !important;
        width: auto !important;
        max-width: 100% !important;
        object-fit: contain;
        margin: 0 0.6rem 0 0.15rem !important;
        display: block;
        vertical-align: middle;
    }
    .kalk-bo-shell {
        border: 1px solid rgba(20, 49, 94, 0.16);
        border-radius: 14px;
        padding: 1rem;
        background: #f7f9fd;
        margin: 0.65rem 0 1rem 0;
    }
    .kalk-bo-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 0.35rem 0 0.6rem 0;
    }
    .kalk-bo-title-wrap {
        display: flex;
        align-items: center;
        gap: 1rem;
        min-width: 0;
    }
    .kalk-bo-logo {
        width: 86px;
        height: 68px;
        object-fit: contain;
        flex: 0 0 auto;
        filter: drop-shadow(0 4px 8px rgba(20, 49, 94, 0.16));
    }
    .kalk-bo-title {
        color: #202653;
        font-size: 2.45rem;
        font-weight: 900;
        margin: 0;
        line-height: 1;
        letter-spacing: 0;
    }
    .kalk-bo-subtitle {
        color: #14315E;
        font-size: 1.08rem;
        font-weight: 700;
        margin: 0.35rem 0 0 0;
        line-height: 1.25;
    }
    .kalk-bo-list {
        display: grid;
        gap: 0.55rem;
        margin-top: 0.35rem;
    }
    .kalk-bo-row {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        gap: 0.7rem;
        border: 2px solid #a9bee7;
        border-radius: 8px;
        padding: 0.65rem 0.75rem;
        background: #ffffff;
    }
    .kalk-bo-row.subsetor {
        background: #edf3fb;
        margin-left: 1.2rem;
    }
    .kalk-bo-dot {
        width: 18px;
        height: 18px;
        border-radius: 999px;
        display: inline-block;
        border: 1px solid rgba(20, 49, 94, 0.08);
    }
    .kalk-bo-name {
        color: #052966;
        font-size: 1.02rem;
        font-weight: 900;
        letter-spacing: 0.02em;
        overflow-wrap: anywhere;
    }
    .kalk-bo-meta {
        color: #53657f;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .kalk-bo-detail-title {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin: 0.25rem 0 0.75rem 0;
    }
    .kalk-bo-detail-title h3 {
        color: #052966;
        font-size: 1.7rem;
        font-weight: 900;
        margin: 0;
        line-height: 1.1;
        overflow-wrap: anywhere;
    }
    .kalk-bo-summary-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.75rem 0;
    }
    .kalk-bo-summary-card {
        border: 2px solid #a9bee7;
        border-radius: 8px;
        padding: 0.65rem 0.8rem;
        background: #ffffff;
    }
    .kalk-bo-summary-label {
        color: #9bb4e4;
        font-size: 0.78rem;
        font-weight: 900;
        text-transform: uppercase;
        margin: 0;
    }
    .kalk-bo-summary-value {
        color: #526487;
        font-size: 1.35rem;
        font-weight: 900;
        margin: 0.1rem 0 0 0;
    }
    .kalk-bo-empty {
        border: 2px dashed #a9bee7;
        border-radius: 8px;
        padding: 1rem;
        background: #ffffff;
        color: #526487;
        font-weight: 700;
        margin: 0.75rem 0;
    }
    .kalk-bo-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.75rem;
        table-layout: fixed;
    }
    .kalk-bo-table th {
        color: #052966;
        background: linear-gradient(180deg, #ffffff, #d8e6fb);
        border-bottom: 3px solid #111111;
        font-size: 0.86rem;
        letter-spacing: 0.02em;
        padding: 0.5rem;
        text-align: center;
    }
    .kalk-bo-table td {
        color: #526487;
        border-bottom: 2px solid #111111;
        padding: 0.55rem 0.5rem;
        text-align: center;
        font-weight: 800;
        overflow-wrap: anywhere;
    }
    .kalk-bo-table td:first-child,
    .kalk-bo-table th:first-child {
        text-align: left;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def app_data_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


def is_primary_db_path(db_path: str | Path) -> bool:
    return app_data_path(db_path).resolve() == DB_PATH.resolve()


def connect_db(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    resolved = app_data_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved), timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    return conn


def atomic_write_dataframe_csv(df: pd.DataFrame, path: str | Path, columns: list[str]) -> None:
    target = app_data_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    work = df.copy()
    for col in columns:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].fillna("").astype(str).str.strip()
    work = work[columns]

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=str(target.parent),
            suffix=".tmp",
            encoding="utf-8",
            newline="",
        ) as handle:
            temp_path = Path(handle.name)
            work.to_csv(handle, index=False, sep=";")
        temp_path.replace(target)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def export_collaborators_to_csv(
    db_path: str | Path = DB_PATH,
    csv_path: str | Path = COLLABORATORS_CSV_PATH,
) -> None:
    atomic_write_dataframe_csv(load_collaborators_from_db(db_path), csv_path, COLLABORATOR_COLUMNS)


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]

    expected = ["MAT", "NOME", "CARGO", "LIDER", "POSICAO"]
    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {', '.join(missing)}")

    for col in expected:
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in COLLABORATOR_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[COLLABORATOR_COLUMNS]
    return df.drop_duplicates(subset=["MAT"], keep="first").reset_index(drop=True)


def init_collaborator_db(csv_path: str | Path, db_path: str | Path = DB_PATH) -> None:
    with connect_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS colaboradores (
                MAT TEXT PRIMARY KEY,
                NOME TEXT NOT NULL,
                CARGO TEXT,
                SUPERSETOR TEXT,
                SETOR TEXT,
                SUBSETOR TEXT,
                LIDER TEXT,
                POSICAO TEXT,
                OBSERVACOES TEXT DEFAULT '',
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {
            str(row[1]).upper()
            for row in conn.execute("PRAGMA table_info(colaboradores)").fetchall()
        }
        if "OBSERVACOES" not in existing_columns:
            conn.execute("ALTER TABLE colaboradores ADD COLUMN OBSERVACOES TEXT DEFAULT ''")
        if "UPDATED_AT" not in existing_columns:
            conn.execute("ALTER TABLE colaboradores ADD COLUMN UPDATED_AT TEXT DEFAULT ''")
        existing_count = conn.execute("SELECT COUNT(*) FROM colaboradores").fetchone()[0]
        if existing_count == 0:
            seed = load_data(csv_path)
            seed.to_sql("colaboradores", conn, if_exists="append", index=False)


def load_collaborators_from_db(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    with connect_db(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT MAT, NOME, CARGO, SUPERSETOR, SETOR, SUBSETOR, LIDER, POSICAO, OBSERVACOES
            FROM colaboradores
            ORDER BY NOME COLLATE NOCASE, MAT
            """,
            conn,
            dtype=str,
        )
    for col in COLLABORATOR_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df[COLLABORATOR_COLUMNS].drop_duplicates(subset=["MAT"], keep="last").reset_index(drop=True)


@st.cache_data
def load_setores(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]

    expected = ["SETOR", "LIDERMAT"]
    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes em setores.csv: {', '.join(missing)}")

    for col in expected:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df[(df["SETOR"] != "") & (df["LIDERMAT"] != "")].drop_duplicates().reset_index(drop=True)


@st.cache_data
def load_supersetores(path: str) -> pd.DataFrame:
    """Carrega dados de supersetores com seus setores filhos."""
    try:
        df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
        df.columns = [c.strip().upper() for c in df.columns]

        expected = ["SUPERSETOR", "SETORFILHO"]
        missing = [col for col in expected if col not in df.columns]
        if missing:
            return pd.DataFrame(columns=expected)

        for col in expected:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df[(df["SUPERSETOR"] != "") & (df["SETORFILHO"] != "")].drop_duplicates().reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["SUPERSETOR", "SETORFILHO", "LIDERMAT"])


@st.cache_data
def load_subsetores(path: str) -> pd.DataFrame:
    """Carrega dados de subsetores com seus setores pai."""
    try:
        df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
        df.columns = [c.strip().upper() for c in df.columns]

        expected = ["SUBSETOR", "SETORPAI"]
        missing = [col for col in expected if col not in df.columns]
        if missing:
            return pd.DataFrame(columns=expected)

        for col in expected:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df[(df["SUBSETOR"] != "") & (df["SETORPAI"] != "")].drop_duplicates().reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["SUBSETOR", "SETORPAI", "LIDERMAT"])


def init_hierarchy_db(
    setores_path: str | Path,
    supersetores_path: str | Path,
    subsetores_path: str | Path,
    db_path: str | Path = DB_PATH,
) -> None:
    with connect_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hierarchy_setores (
                SETOR TEXT PRIMARY KEY,
                LIDERMAT TEXT DEFAULT '',
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hierarchy_supersetores (
                SETORFILHO TEXT PRIMARY KEY,
                SUPERSETOR TEXT NOT NULL,
                LIDERMAT TEXT DEFAULT '',
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hierarchy_subsetores (
                SUBSETOR TEXT PRIMARY KEY,
                SETORPAI TEXT NOT NULL,
                LIDERMAT TEXT DEFAULT '',
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        if conn.execute("SELECT COUNT(*) FROM hierarchy_setores").fetchone()[0] == 0:
            for _, row in load_setores(setores_path).iterrows():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hierarchy_setores (SETOR, LIDERMAT)
                    VALUES (?, ?)
                    """,
                    (str(row.get("SETOR", "")).strip(), str(row.get("LIDERMAT", "")).strip()),
                )

        if conn.execute("SELECT COUNT(*) FROM hierarchy_supersetores").fetchone()[0] == 0:
            for _, row in load_supersetores(supersetores_path).iterrows():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hierarchy_supersetores (SUPERSETOR, SETORFILHO, LIDERMAT)
                    VALUES (?, ?, ?)
                    """,
                    (
                        str(row.get("SUPERSETOR", "")).strip(),
                        str(row.get("SETORFILHO", "")).strip(),
                        str(row.get("LIDERMAT", "")).strip(),
                    ),
                )

        if conn.execute("SELECT COUNT(*) FROM hierarchy_subsetores").fetchone()[0] == 0:
            for _, row in load_subsetores(subsetores_path).iterrows():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hierarchy_subsetores (SUBSETOR, SETORPAI, LIDERMAT)
                    VALUES (?, ?, ?)
                    """,
                    (
                        str(row.get("SUBSETOR", "")).strip(),
                        str(row.get("SETORPAI", "")).strip(),
                        str(row.get("LIDERMAT", "")).strip(),
                    ),
                )
        conn.commit()


def load_hierarchy_from_db(
    db_path: str | Path = DB_PATH,
    setores_path: str | Path = SETORES_CSV_PATH,
    supersetores_path: str | Path = SUPERSETORES_CSV_PATH,
    subsetores_path: str | Path = SUBSETORES_CSV_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with connect_db(db_path) as conn:
        setores_df = pd.read_sql_query(
            """
            SELECT SETOR, LIDERMAT, rowid AS _ROWID
            FROM hierarchy_setores
            WHERE TRIM(SETOR) <> ''
            ORDER BY rowid
            """,
            conn,
            dtype=str,
        )
        supersetores_df = pd.read_sql_query(
            """
            SELECT SUPERSETOR, SETORFILHO, LIDERMAT, rowid AS _ROWID
            FROM hierarchy_supersetores
            WHERE TRIM(SUPERSETOR) <> '' AND TRIM(SETORFILHO) <> ''
            ORDER BY rowid
            """,
            conn,
            dtype=str,
        )
        subsetores_df = pd.read_sql_query(
            """
            SELECT SUBSETOR, SETORPAI, LIDERMAT, rowid AS _ROWID
            FROM hierarchy_subsetores
            WHERE TRIM(SUBSETOR) <> '' AND TRIM(SETORPAI) <> ''
            ORDER BY rowid
            """,
            conn,
            dtype=str,
        )

    frames = [
        (setores_df, ["SETOR", "LIDERMAT"]),
        (supersetores_df, ["SUPERSETOR", "SETORFILHO", "LIDERMAT"]),
        (subsetores_df, ["SUBSETOR", "SETORPAI", "LIDERMAT"]),
    ]
    for frame, columns in frames:
        for col in columns:
            if col not in frame.columns:
                frame[col] = ""
            frame[col] = frame[col].fillna("").astype(str).str.strip()

    def reference_order(path: str | Path, key_columns: list[str]) -> dict[tuple[str, ...], int]:
        try:
            reference = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
            reference.columns = [c.strip().upper() for c in reference.columns]
        except Exception:
            return {}
        order: dict[tuple[str, ...], int] = {}
        for idx, row in reference.iterrows():
            key = tuple(str(row.get(col, "")).strip() for col in key_columns)
            if all(key) and key not in order:
                order[key] = int(idx)
        return order

    def sort_with_reference(frame: pd.DataFrame, key_columns: list[str], path: str | Path) -> pd.DataFrame:
        order = reference_order(path, key_columns)
        work = frame.copy()

        def order_key(row: pd.Series) -> tuple[int, int, str]:
            key = tuple(str(row.get(col, "")).strip() for col in key_columns)
            rowid = int(str(row.get("_ROWID", "0")).strip() or 0)
            label = " ".join(key).casefold()
            return (0, order[key], label) if key in order else (1, rowid, label)

        if not work.empty:
            work["_ORDER_KEY"] = [order_key(row) for _, row in work.iterrows()]
            work = work.sort_values("_ORDER_KEY").drop(columns=["_ORDER_KEY"])
        return work.drop(columns=[col for col in ["_ROWID"] if col in work.columns]).reset_index(drop=True)

    setores_df = sort_with_reference(setores_df, ["SETOR"], setores_path)
    supersetores_df = sort_with_reference(supersetores_df, ["SUPERSETOR", "SETORFILHO"], supersetores_path)
    subsetores_df = sort_with_reference(subsetores_df, ["SUBSETOR", "SETORPAI"], subsetores_path)
    return setores_df, supersetores_df, subsetores_df


def persist_hierarchy_setores(
    setores_df: pd.DataFrame,
    db_path: str | Path = DB_PATH,
    csv_path: str | Path = SETORES_CSV_PATH,
) -> None:
    clean = setores_df.copy()
    for col in ["SETOR", "LIDERMAT"]:
        if col not in clean.columns:
            clean[col] = ""
        clean[col] = clean[col].fillna("").astype(str).str.strip()
    clean = clean[clean["SETOR"] != ""].drop_duplicates(subset=["SETOR"], keep="last")

    with connect_db(db_path) as conn:
        conn.execute("DELETE FROM hierarchy_setores")
        for _, row in clean.iterrows():
            conn.execute(
                """
                INSERT INTO hierarchy_setores (SETOR, LIDERMAT, UPDATED_AT)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (row["SETOR"], row["LIDERMAT"]),
            )
        conn.commit()
    if is_primary_db_path(db_path):
        atomic_write_dataframe_csv(clean, csv_path, ["SETOR", "LIDERMAT"])


def persist_hierarchy_supersetores(
    supersetores_df: pd.DataFrame,
    db_path: str | Path = DB_PATH,
    csv_path: str | Path = SUPERSETORES_CSV_PATH,
) -> None:
    clean = supersetores_df.copy()
    for col in ["SUPERSETOR", "SETORFILHO", "LIDERMAT"]:
        if col not in clean.columns:
            clean[col] = ""
        clean[col] = clean[col].fillna("").astype(str).str.strip()
    clean = clean[(clean["SUPERSETOR"] != "") & (clean["SETORFILHO"] != "")]
    clean = clean.drop_duplicates(subset=["SETORFILHO"], keep="last")

    with connect_db(db_path) as conn:
        conn.execute("DELETE FROM hierarchy_supersetores")
        for _, row in clean.iterrows():
            conn.execute(
                """
                INSERT INTO hierarchy_supersetores (SUPERSETOR, SETORFILHO, LIDERMAT, UPDATED_AT)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (row["SUPERSETOR"], row["SETORFILHO"], row["LIDERMAT"]),
            )
        conn.commit()
    if is_primary_db_path(db_path):
        atomic_write_dataframe_csv(clean, csv_path, ["SUPERSETOR", "SETORFILHO", "LIDERMAT"])


def persist_hierarchy_subsetores(
    subsetores_df: pd.DataFrame,
    db_path: str | Path = DB_PATH,
    csv_path: str | Path = SUBSETORES_CSV_PATH,
) -> None:
    clean = subsetores_df.copy()
    for col in ["SUBSETOR", "SETORPAI", "LIDERMAT"]:
        if col not in clean.columns:
            clean[col] = ""
        clean[col] = clean[col].fillna("").astype(str).str.strip()
    clean = clean[(clean["SUBSETOR"] != "") & (clean["SETORPAI"] != "")]
    clean = clean.drop_duplicates(subset=["SUBSETOR"], keep="last")

    with connect_db(db_path) as conn:
        conn.execute("DELETE FROM hierarchy_subsetores")
        for _, row in clean.iterrows():
            conn.execute(
                """
                INSERT INTO hierarchy_subsetores (SUBSETOR, SETORPAI, LIDERMAT, UPDATED_AT)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (row["SUBSETOR"], row["SETORPAI"], row["LIDERMAT"]),
            )
        conn.commit()
    if is_primary_db_path(db_path):
        atomic_write_dataframe_csv(clean, csv_path, ["SUBSETOR", "SETORPAI", "LIDERMAT"])


def init_kalk_bo_db(db_path: Path = DB_PATH) -> None:
    with connect_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kalk_bo_configs (
                SCOPE_TYPE TEXT NOT NULL,
                SCOPE_KEY TEXT NOT NULL,
                SETOR TEXT DEFAULT '',
                SUBSETOR TEXT DEFAULT '',
                DRIVER_LABEL TEXT DEFAULT '',
                INDICATOR_LABEL TEXT DEFAULT '',
                YELLOW_MIN REAL DEFAULT 3.5,
                GREEN_MIN REAL DEFAULT 4.5,
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SCOPE_TYPE, SCOPE_KEY)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kalk_bo_values (
                SCOPE_TYPE TEXT NOT NULL,
                SCOPE_KEY TEXT NOT NULL,
                MAT TEXT NOT NULL,
                DRIVER_VALUE REAL,
                INDICATOR_VALUE REAL,
                UPDATED_AT TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SCOPE_TYPE, SCOPE_KEY, MAT)
            )
            """
        )
        conn.commit()


def kalk_scope_key(scope_type: str, setor: str, subsetor: str = "") -> str:
    setor = str(setor or "").strip()
    subsetor = str(subsetor or "").strip()
    return f"{setor}||{subsetor}" if scope_type == "subsetor" else setor


def default_kalk_config(scope_type: str, setor: str, subsetor: str = "") -> dict:
    return {
        "SCOPE_TYPE": scope_type,
        "SCOPE_KEY": kalk_scope_key(scope_type, setor, subsetor),
        "SETOR": str(setor or "").strip(),
        "SUBSETOR": str(subsetor or "").strip(),
        "DRIVER_LABEL": "",
        "INDICATOR_LABEL": "",
        "YELLOW_MIN": 3.5,
        "GREEN_MIN": 4.5,
    }


def load_kalk_bo_configs(db_path: Path = DB_PATH) -> dict[tuple[str, str], dict]:
    with connect_db(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT SCOPE_TYPE, SCOPE_KEY, SETOR, SUBSETOR, DRIVER_LABEL, INDICATOR_LABEL,
                   YELLOW_MIN, GREEN_MIN
            FROM kalk_bo_configs
            """,
            conn,
        )
    configs: dict[tuple[str, str], dict] = {}
    for _, row in df.iterrows():
        scope_type = str(row.get("SCOPE_TYPE", "")).strip()
        scope_key = str(row.get("SCOPE_KEY", "")).strip()
        if scope_type and scope_key:
            configs[(scope_type, scope_key)] = row.to_dict()
    return configs


def load_kalk_bo_values(db_path: Path = DB_PATH) -> pd.DataFrame:
    with connect_db(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT SCOPE_TYPE, SCOPE_KEY, MAT, DRIVER_VALUE, INDICATOR_VALUE
            FROM kalk_bo_values
            """,
            conn,
            dtype={"SCOPE_TYPE": str, "SCOPE_KEY": str, "MAT": str},
        )
    for col in ["SCOPE_TYPE", "SCOPE_KEY", "MAT"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df


def persist_kalk_bo_config(config: dict, db_path: Path = DB_PATH) -> None:
    with connect_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO kalk_bo_configs (
                SCOPE_TYPE, SCOPE_KEY, SETOR, SUBSETOR, DRIVER_LABEL, INDICATOR_LABEL,
                YELLOW_MIN, GREEN_MIN, UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(SCOPE_TYPE, SCOPE_KEY) DO UPDATE SET
                SETOR = excluded.SETOR,
                SUBSETOR = excluded.SUBSETOR,
                DRIVER_LABEL = excluded.DRIVER_LABEL,
                INDICATOR_LABEL = excluded.INDICATOR_LABEL,
                YELLOW_MIN = excluded.YELLOW_MIN,
                GREEN_MIN = excluded.GREEN_MIN,
                UPDATED_AT = CURRENT_TIMESTAMP
            """,
            (
                str(config.get("SCOPE_TYPE", "")).strip(),
                str(config.get("SCOPE_KEY", "")).strip(),
                str(config.get("SETOR", "")).strip(),
                str(config.get("SUBSETOR", "")).strip(),
                str(config.get("DRIVER_LABEL", "")).strip(),
                str(config.get("INDICATOR_LABEL", "")).strip(),
                float(config.get("YELLOW_MIN", 3.5) or 3.5),
                float(config.get("GREEN_MIN", 4.5) or 4.5),
            ),
        )
        conn.commit()


def parse_optional_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def persist_kalk_bo_values(scope_type: str, scope_key: str, edited_df: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    scope_type = str(scope_type or "").strip()
    scope_key = str(scope_key or "").strip()
    with connect_db(db_path) as conn:
        conn.execute(
            "DELETE FROM kalk_bo_values WHERE SCOPE_TYPE = ? AND SCOPE_KEY = ?",
            (scope_type, scope_key),
        )
        for _, row in edited_df.iterrows():
            mat = str(row.get("MAT", "")).strip()
            if not mat:
                continue
            driver_value = parse_optional_float(row.get("DRIVER"))
            indicator_value = parse_optional_float(row.get("INDICADOR"))
            if driver_value is None and indicator_value is None:
                continue
            conn.execute(
                """
                INSERT INTO kalk_bo_values (
                    SCOPE_TYPE, SCOPE_KEY, MAT, DRIVER_VALUE, INDICATOR_VALUE, UPDATED_AT
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (scope_type, scope_key, mat, driver_value, indicator_value),
            )
        conn.commit()


def kalk_image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"


def kalk_logo_html(css_class: str = "kalk-bo-logo") -> str:
    data_uri = kalk_image_data_uri(KALK_BO_LOGO_PATH)
    if not data_uri:
        return ""
    return f'<img class="{css_class}" src="{data_uri}" alt="KALK BO" />'


def kalk_button_label() -> str:
    data_uri = kalk_image_data_uri(KALK_BO_ICON_PATH)
    if not data_uri:
        return "KALK BO"
    return f"![KALK BO]({data_uri}) KALK BO"


def kalk_status_for_average(avg: float | None, config: dict, has_collaborators: bool) -> str:
    driver_label = str(config.get("DRIVER_LABEL", "")).strip()
    indicator_label = str(config.get("INDICATOR_LABEL", "")).strip()
    if not has_collaborators or not driver_label or not indicator_label or avg is None:
        return "pending"
    yellow_min = float(config.get("YELLOW_MIN", 3.5) or 3.5)
    green_min = float(config.get("GREEN_MIN", 4.5) or 4.5)
    if avg >= green_min:
        return "green"
    if avg >= yellow_min:
        return "yellow"
    return "red"


def status_dot_html(status: str) -> str:
    color = KALK_STATUS_COLORS.get(status, KALK_STATUS_COLORS["pending"])
    return f'<span class="kalk-bo-dot" style="background:{color}"></span>'


def format_kalk_number(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value - round(value)) < 0.005:
        return f"{value:.0f}"
    return f"{value:.2f}".replace(".", ",")


def collaborators_for_kalk_scope(df: pd.DataFrame, scope_type: str, setor: str, subsetor: str = "") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["SETOR"] = work["SETOR"].fillna("").astype(str).str.strip()
    work["SUBSETOR"] = work["SUBSETOR"].fillna("").astype(str).str.strip()
    setor = str(setor or "").strip()
    subsetor = str(subsetor or "").strip()
    if scope_type == "subsetor":
        scoped = work[(work["SETOR"] == setor) & (work["SUBSETOR"] == subsetor)]
    else:
        scoped = work[work["SETOR"] == setor]
    return scoped.sort_values(["NOME", "MAT"]).reset_index(drop=True)


def build_kalk_editor_df(collaborators_df: pd.DataFrame, values_df: pd.DataFrame, scope_type: str, scope_key: str) -> pd.DataFrame:
    current_values = values_df[
        (values_df["SCOPE_TYPE"] == scope_type) & (values_df["SCOPE_KEY"] == scope_key)
    ].copy()
    value_map = {
        str(row.get("MAT", "")).strip(): row
        for _, row in current_values.iterrows()
        if str(row.get("MAT", "")).strip()
    }
    rows = []
    for _, row in collaborators_df.iterrows():
        mat = str(row.get("MAT", "")).strip()
        value_row = value_map.get(mat, {})
        rows.append(
            {
                "MAT": mat,
                "NOME": str(row.get("NOME", "")).strip(),
                "CARGO": str(row.get("CARGO", "")).strip(),
                "DRIVER": value_row.get("DRIVER_VALUE", None),
                "INDICADOR": value_row.get("INDICATOR_VALUE", None),
            }
        )
    return pd.DataFrame(rows, columns=["MAT", "NOME", "CARGO", "DRIVER", "INDICADOR"])


def kalk_scope_metrics(editor_df: pd.DataFrame, config: dict, has_collaborators: bool) -> dict:
    driver_values = [parse_optional_float(value) for value in editor_df.get("DRIVER", pd.Series(dtype=object)).tolist()]
    indicator_values = [parse_optional_float(value) for value in editor_df.get("INDICADOR", pd.Series(dtype=object)).tolist()]
    driver_values = [value for value in driver_values if value is not None]
    indicator_values = [value for value in indicator_values if value is not None]
    driver_total = sum(driver_values) if driver_values else None
    indicator_avg = statistics.mean(indicator_values) if indicator_values else None
    status = kalk_status_for_average(indicator_avg, config, has_collaborators)
    return {
        "driver_total": driver_total,
        "indicator_avg": indicator_avg,
        "status": status,
    }


def kalk_config_for_scope(configs: dict[tuple[str, str], dict], scope_type: str, setor: str, subsetor: str = "") -> dict:
    scope_key = kalk_scope_key(scope_type, setor, subsetor)
    return configs.get((scope_type, scope_key), default_kalk_config(scope_type, setor, subsetor))


def kalk_status_for_scope(
    df: pd.DataFrame,
    values_df: pd.DataFrame,
    configs: dict[tuple[str, str], dict],
    scope_type: str,
    setor: str,
    subsetor: str = "",
) -> dict:
    scope_key = kalk_scope_key(scope_type, setor, subsetor)
    config = kalk_config_for_scope(configs, scope_type, setor, subsetor)
    collaborators_df = collaborators_for_kalk_scope(df, scope_type, setor, subsetor)
    editor_df = build_kalk_editor_df(collaborators_df, values_df, scope_type, scope_key)
    metrics = kalk_scope_metrics(editor_df, config, not collaborators_df.empty)
    return {**metrics, "collaborator_count": len(collaborators_df), "config": config}


def aggregate_kalk_sector_status(child_statuses: list[str]) -> str:
    active_statuses = [status for status in child_statuses if status != "pending"]
    if not active_statuses:
        return "pending"
    if "red" in active_statuses:
        return "red"
    if "yellow" in active_statuses:
        return "yellow"
    return "green"


def get_sector_scope_ids(
    df: pd.DataFrame,
    setores_df: pd.DataFrame,
    selected_setores: list[str],
) -> set[str]:
    if not selected_setores or setores_df is None or setores_df.empty:
        return set()

    selected_rows = setores_df[setores_df["SETOR"].isin(selected_setores)]
    target_leaders = set(selected_rows["LIDERMAT"].tolist())
    valid_ids = set(df["MAT"].tolist())

    children_map: dict[str, list[str]] = defaultdict(list)
    parent_map: dict[str, str] = {}
    for _, row in df.iterrows():
        child = row["MAT"]
        parent = row["LIDER"]
        if parent and parent != child:
            children_map[parent].append(child)
            if child not in parent_map:
                parent_map[child] = parent

    include_ids: set[str] = set()
    for leader in target_leaders:
        if leader not in valid_ids:
            continue

        include_ids.add(leader)

        stack = [leader]
        while stack:
            cur = stack.pop()
            for child in children_map.get(cur, []):
                if child not in include_ids:
                    include_ids.add(child)
                    stack.append(child)

        seen: set[str] = set()
        cur = leader
        while cur in parent_map and cur not in seen:
            seen.add(cur)
            parent = parent_map[cur]
            include_ids.add(parent)
            cur = parent

    return include_ids


def get_sector_descendant_ids(
    df: pd.DataFrame,
    setores_df: pd.DataFrame,
    selected_setores: list[str],
) -> set[str]:
    if not selected_setores or setores_df is None or setores_df.empty:
        return set()

    selected_rows = setores_df[setores_df["SETOR"].isin(selected_setores)]
    target_leaders = set(selected_rows["LIDERMAT"].tolist())
    valid_ids = set(df["MAT"].tolist())

    children_map: dict[str, list[str]] = defaultdict(list)
    for _, row in df.iterrows():
        child = row["MAT"]
        parent = row["LIDER"]
        if parent and parent != child:
            children_map[parent].append(child)

    descendants: set[str] = set()
    for leader in target_leaders:
        if leader not in valid_ids:
            continue

        stack = list(children_map.get(leader, []))
        while stack:
            cur = stack.pop()
            if cur in descendants:
                continue
            descendants.add(cur)
            stack.extend(children_map.get(cur, []))

    return descendants


def build_graph(
    df: pd.DataFrame,
    selected_posicoes: list[str],
    search: str,
    setores_df: pd.DataFrame | None = None,
    selected_setores: list[str] | None = None,
):
    selected_setores = selected_setores or []

    if selected_setores and setores_df is not None and not setores_df.empty:
        include_ids = get_sector_scope_ids(df, setores_df, selected_setores)

        work = df[df["MAT"].isin(include_ids)].copy()
    else:
        work = df.copy()
        if selected_posicoes:
            work = work[work["POSICAO"].isin(selected_posicoes)]

    highlighted_ids: set[str] = set()
    if search:
        s = search.lower().strip()
        if s:
            mask = (
                work["NOME"].str.lower().str.contains(s, regex=False)
                | work["CARGO"].str.lower().str.contains(s, regex=False)
                | work["MAT"].str.lower().str.contains(s, regex=False)
            )
            highlighted_ids = set(work.loc[mask, "MAT"].tolist())

    ids = set(work["MAT"])

    leaders = set(work["LIDER"]) - {""}
    missing_leaders = leaders - ids
    if missing_leaders:
        context = df[df["MAT"].isin(missing_leaders)]
        work = pd.concat([work, context], ignore_index=True).drop_duplicates("MAT")
        ids = set(work["MAT"])

    edge_count = 0
    for _, row in work.iterrows():
        parent = row["LIDER"]
        child = row["MAT"]
        if parent and parent in ids and parent != child:
            edge_count += 1

    if "1979" not in ids:
        fallback = df[df["MAT"] == "1979"]
        if not fallback.empty:
            work = pd.concat([work, fallback], ignore_index=True).drop_duplicates("MAT")

    return work, edge_count, highlighted_ids


def build_span_ranking(work: pd.DataFrame) -> pd.DataFrame:
    ids = set(work["MAT"].tolist())
    if not ids:
        return pd.DataFrame(columns=["MAT", "NOME", "CARGO", "SPAN"])

    spans: dict[str, int] = defaultdict(int)
    for _, row in work.iterrows():
        parent = row["LIDER"]
        child = row["MAT"]
        if parent and parent in ids and parent != child:
            spans[parent] += 1

    if not spans:
        return pd.DataFrame(columns=["MAT", "NOME", "CARGO", "SPAN"])

    leaders = work[work["MAT"].isin(spans.keys())][["MAT", "NOME", "CARGO"]].drop_duplicates("MAT")
    leaders["SPAN"] = leaders["MAT"].map(spans).fillna(0).astype(int)

    return leaders.sort_values(by=["SPAN", "NOME"], ascending=[False, True]).reset_index(drop=True)


def _build_maps(work: pd.DataFrame) -> tuple[set[str], dict[str, str], dict[str, list[str]]]:
    ids = set(work["MAT"].tolist())
    parent_map: dict[str, str] = {}
    children_map: dict[str, list[str]] = defaultdict(list)

    for _, row in work.iterrows():
        child = row["MAT"]
        parent = row["LIDER"]
        if parent and parent in ids and parent != child:
            parent_map[child] = parent
            children_map[parent].append(child)

    for parent in children_map:
        children_map[parent].sort()

    return ids, parent_map, children_map


def generate_reorg_suggestions(work: pd.DataFrame) -> list[dict]:
    if work.empty:
        return []

    ids, parent_map, children_map = _build_maps(work)
    spans = {node: len(children_map.get(node, [])) for node in ids}
    leaders = [node for node, span in spans.items() if span > 0]
    if not leaders:
        return []

    people = work.drop_duplicates("MAT").set_index("MAT")

    def person_name(mat: str) -> str:
        if mat in people.index:
            return str(people.loc[mat, "NOME"])
        return mat

    def person_role(mat: str) -> str:
        if mat in people.index:
            return str(people.loc[mat, "CARGO"])
        return ""

    positive_spans = [spans[node] for node in leaders if spans[node] > 0]
    span_median = int(round(statistics.median(positive_spans))) if positive_spans else 0
    split_target = max(4, span_median)

    suggestions: list[dict] = []

    for leader in sorted(leaders, key=lambda x: (-spans[x], person_name(x))):
        span = spans[leader]
        direct_reports = list(children_map.get(leader, []))
        if span < split_target + 3 or len(direct_reports) < 4:
            continue

        candidate = max(direct_reports, key=lambda x: (spans.get(x, 0), person_name(x)))
        movable = [node for node in sorted(direct_reports, key=lambda x: (spans.get(x, 0), person_name(x))) if node != candidate]
        move_count = max(2, min(len(movable), span - split_target))
        moved_ids = movable[:move_count]
        if len(moved_ids) < 2:
            continue

        suggestions.append(
            {
                "kind": "split",
                "title": f"Split da area de {person_name(leader)}",
                "summary": (
                    f"{person_name(leader)} possui span {span}. Repassar {len(moved_ids)} liderados para "
                    f"{person_name(candidate)} reduziria o span para {span - len(moved_ids)}."
                ),
                "leader_id": leader,
                "candidate_id": candidate,
                "moved_ids": moved_ids,
                "focus_ids": [leader, candidate, *moved_ids],
                "impact": len(moved_ids),
            }
        )
        if len([s for s in suggestions if s["kind"] == "split"]) >= 4:
            break

    for parent, kids in children_map.items():
        child_leaders = [node for node in kids if spans.get(node, 0) > 0]
        low_span_leaders = [node for node in child_leaders if spans.get(node, 0) <= 2]
        if len(low_span_leaders) < 2:
            continue

        low_span_leaders = sorted(low_span_leaders, key=lambda x: (spans.get(x, 0), person_name(x)))
        primary = low_span_leaders[0]
        secondary = low_span_leaders[1]
        moved_ids = list(children_map.get(secondary, []))
        if not moved_ids:
            continue

        suggestions.append(
            {
                "kind": "merge",
                "title": f"Merge das frentes de {person_name(primary)} e {person_name(secondary)}",
                "summary": (
                    f"Ambos respondem para {person_name(parent)} e operam com baixo span. "
                    f"Unificar {len(moved_ids)} liderados de {person_name(secondary)} sob {person_name(primary)} "
                    f"pode simplificar a estrutura."
                ),
                "parent_id": parent,
                "primary_id": primary,
                "secondary_id": secondary,
                "moved_ids": moved_ids,
                "focus_ids": [parent, primary, secondary, *moved_ids],
                "impact": len(moved_ids),
            }
        )
        if len([s for s in suggestions if s["kind"] == "merge"]) >= 4:
            break

    suggestions.sort(key=lambda x: (-int(x.get("impact", 0)), x.get("title", "")))
    return suggestions[:8]


def apply_reorg_suggestion(work: pd.DataFrame, suggestion: dict) -> pd.DataFrame:
    proposed = work.copy()
    kind = str(suggestion.get("kind", ""))

    if kind == "split":
        candidate_id = str(suggestion.get("candidate_id", ""))
        moved_ids = set(suggestion.get("moved_ids", []))
        proposed.loc[proposed["MAT"].isin(moved_ids), "LIDER"] = candidate_id
    elif kind == "merge":
        primary_id = str(suggestion.get("primary_id", ""))
        moved_ids = set(suggestion.get("moved_ids", []))
        proposed.loc[proposed["MAT"].isin(moved_ids), "LIDER"] = primary_id

    return proposed


def build_focus_scope(work: pd.DataFrame, focus_ids: list[str], up_levels: int = 1, down_levels: int = 3) -> set[str]:
    ids, parent_map, children_map = _build_maps(work)
    seeds = [node for node in focus_ids if node in ids]
    if not seeds:
        return set(ids)

    selected: set[str] = set(seeds)

    q_up = deque((node, 0) for node in seeds)
    while q_up:
        node, depth = q_up.popleft()
        if depth >= up_levels:
            continue
        parent = parent_map.get(node)
        if parent and parent not in selected:
            selected.add(parent)
            q_up.append((parent, depth + 1))

    q_down = deque((node, 0) for node in seeds)
    while q_down:
        node, depth = q_down.popleft()
        if depth >= down_levels:
            continue
        for child in children_map.get(node, []):
            if child not in selected:
                selected.add(child)
                q_down.append((child, depth + 1))

    return selected


def get_person_label(df: pd.DataFrame, mat: str) -> str:
    if not mat:
        return ""
    person = df[df["MAT"] == mat]
    if person.empty:
        return mat
    nome = str(person.iloc[0]["NOME"]).strip()
    return nome or mat


NIVEL_OPTIONS = ["I", "II", "III", "IV", "V", "VI", "VII"]


def split_cargo_nivel_value(cargo: str) -> tuple[str, str]:
    text = (cargo or "").strip()
    if " " not in text:
        return text, ""
    cargo_base, nivel = text.rsplit(" ", 1)
    nivel = nivel.strip()
    if nivel in NIVEL_OPTIONS:
        return cargo_base.strip(), nivel
    return text, ""


def join_cargo_nivel(cargo: str, nivel: str) -> str:
    return " ".join([value for value in [str(cargo).strip(), str(nivel).strip()] if value])


def cargo_position_map_from_df(df: pd.DataFrame) -> dict[str, str]:
    if "CARGO" not in df.columns or "POSICAO" not in df.columns:
        return {}
    positions_by_cargo: dict[str, set[str]] = defaultdict(set)
    for _, row in df.iterrows():
        cargo = str(row.get("CARGO", "")).strip()
        posicao = str(row.get("POSICAO", "")).strip()
        if cargo and posicao:
            positions_by_cargo[cargo].add(posicao)
    return {
        cargo: next(iter(values)) if len(values) == 1 else ""
        for cargo, values in positions_by_cargo.items()
    }


def setor_supersetor_map(supersetores_df: pd.DataFrame) -> dict[str, str]:
    if supersetores_df is None or supersetores_df.empty:
        return {}
    return {
        str(row.get("SETORFILHO", "")).strip(): str(row.get("SUPERSETOR", "")).strip()
        for _, row in supersetores_df.iterrows()
        if str(row.get("SETORFILHO", "")).strip()
    }


def subsetores_by_setor(subsetores_df: pd.DataFrame, df: pd.DataFrame) -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    if subsetores_df is not None and not subsetores_df.empty:
        for _, row in subsetores_df.iterrows():
            setor = str(row.get("SETORPAI", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            if setor and subsetor:
                mapping[setor].add(subsetor)
    if "SETOR" in df.columns and "SUBSETOR" in df.columns:
        for _, row in df.iterrows():
            setor = str(row.get("SETOR", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            if setor and subsetor:
                mapping[setor].add(subsetor)
    return {setor: sorted(values, key=str.casefold) for setor, values in mapping.items()}


def clean_org_frame(frame: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    clean = frame.copy() if frame is not None else pd.DataFrame(columns=columns)
    for col in columns:
        if col not in clean.columns:
            clean[col] = ""
        clean[col] = clean[col].fillna("").astype(str).str.strip()
    return clean


def build_org_leader_lookup(
    df: pd.DataFrame,
    setores_df: pd.DataFrame | None,
    subsetores_df: pd.DataFrame | None,
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    collaborators = clean_org_frame(df, COLLABORATOR_COLUMNS)
    setores = clean_org_frame(setores_df, ["SETOR", "LIDERMAT"])
    subsetores = clean_org_frame(subsetores_df, ["SUBSETOR", "SETORPAI", "LIDERMAT"])

    collaborator_area = {
        str(row.get("MAT", "")).strip(): (
            str(row.get("SETOR", "")).strip(),
            str(row.get("SUBSETOR", "")).strip(),
        )
        for _, row in collaborators.iterrows()
        if str(row.get("MAT", "")).strip()
    }

    sector_leaders: dict[str, str] = {}
    for _, row in setores.iterrows():
        setor = str(row.get("SETOR", "")).strip()
        leader_mat = str(row.get("LIDERMAT", "")).strip()
        leader_area = collaborator_area.get(leader_mat)
        if setor and leader_mat and leader_area:
            sector_leaders[setor] = leader_mat

    subsetor_leaders: dict[tuple[str, str], str] = {}
    for _, row in subsetores.iterrows():
        setor = str(row.get("SETORPAI", "")).strip()
        subsetor = str(row.get("SUBSETOR", "")).strip()
        leader_mat = str(row.get("LIDERMAT", "")).strip()
        leader_area = collaborator_area.get(leader_mat)
        if setor and subsetor and leader_mat and leader_area:
            subsetor_leaders[(setor, subsetor)] = leader_mat

    return subsetor_leaders, sector_leaders


def org_leader_mat_for(
    setor: str,
    subsetor: str,
    excluded_mat: str,
    subsetor_leaders: dict[tuple[str, str], str],
    sector_leaders: dict[str, str],
    ignored_mats: set[str] | None = None,
) -> str:
    setor = str(setor or "").strip()
    subsetor = str(subsetor or "").strip()
    excluded_mat = str(excluded_mat or "").strip()
    ignored = {str(value).strip() for value in (ignored_mats or set()) if str(value).strip()}
    if excluded_mat:
        ignored.add(excluded_mat)
    subsetor_leader = subsetor_leaders.get((setor, subsetor), "") if setor and subsetor else ""
    if subsetor_leader and subsetor_leader not in ignored:
        return subsetor_leader
    sector_leader = sector_leaders.get(setor, "") if setor else ""
    if sector_leader and sector_leader not in ignored:
        return sector_leader
    return ""


def redistribute_collaborator_leaders_in_frame(
    df: pd.DataFrame,
    setores_df: pd.DataFrame | None,
    subsetores_df: pd.DataFrame | None,
    only_current_leaders: set[str] | None = None,
) -> tuple[pd.DataFrame, int]:
    result = clean_org_frame(df, COLLABORATOR_COLUMNS)
    subsetor_leaders, sector_leaders = build_org_leader_lookup(result, setores_df, subsetores_df)
    if not subsetor_leaders and not sector_leaders:
        return result, 0

    current_leader_filter = {
        str(value).strip()
        for value in (only_current_leaders or set())
        if str(value).strip()
    }
    ignored_leaders = current_leader_filter if current_leader_filter else set()
    updates = 0
    for idx, row in result.iterrows():
        current_leader = str(row.get("LIDER", "")).strip()
        if current_leader_filter and current_leader not in current_leader_filter:
            continue
        mat = str(row.get("MAT", "")).strip()
        new_leader = org_leader_mat_for(
            str(row.get("SETOR", "")).strip(),
            str(row.get("SUBSETOR", "")).strip(),
            mat,
            subsetor_leaders,
            sector_leaders,
            ignored_mats=ignored_leaders,
        )
        if new_leader and new_leader != current_leader:
            result.at[idx, "LIDER"] = new_leader
            updates += 1
    return result, updates


def out_of_area_leader_ids(
    df: pd.DataFrame,
    setores_df: pd.DataFrame | None = None,
    subsetores_df: pd.DataFrame | None = None,
) -> set[str]:
    collaborators = clean_org_frame(df, COLLABORATOR_COLUMNS)
    subsetor_leaders, sector_leaders = build_org_leader_lookup(collaborators, setores_df, subsetores_df)
    area_by_mat = {
        str(row.get("MAT", "")).strip(): (
            str(row.get("SETOR", "")).strip(),
            str(row.get("SUBSETOR", "")).strip(),
        )
        for _, row in collaborators.iterrows()
        if str(row.get("MAT", "")).strip()
    }
    invalid: set[str] = set()
    for _, row in collaborators.iterrows():
        leader_mat = str(row.get("LIDER", "")).strip()
        if not leader_mat:
            continue
        leader_area = area_by_mat.get(leader_mat)
        setor = str(row.get("SETOR", "")).strip()
        subsetor = str(row.get("SUBSETOR", "")).strip()
        mat = str(row.get("MAT", "")).strip()
        if leader_area is None:
            invalid.add(leader_mat)
            continue
        leader_setor, leader_subsetor = leader_area
        expected_leader = org_leader_mat_for(setor, subsetor, mat, subsetor_leaders, sector_leaders)
        if expected_leader and leader_mat == expected_leader:
            if subsetor and leader_subsetor and leader_subsetor != subsetor:
                invalid.add(leader_mat)
            continue
        if setor and leader_setor and leader_setor != setor:
            invalid.add(leader_mat)
            continue
        if subsetor and leader_subsetor and leader_subsetor != subsetor:
            invalid.add(leader_mat)
    return invalid


def redistribute_collaborator_leaders(
    setores_df: pd.DataFrame,
    subsetores_df: pd.DataFrame,
    only_current_leaders: set[str] | None = None,
    db_path: str | Path = DB_PATH,
) -> tuple[int, list[str]]:
    errors: list[str] = []
    with connect_db(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT MAT, NOME, CARGO, SUPERSETOR, SETOR, SUBSETOR, LIDER, POSICAO, OBSERVACOES
            FROM colaboradores
            ORDER BY NOME COLLATE NOCASE, MAT
            """,
            conn,
            dtype=str,
        )
        redistributed, updates = redistribute_collaborator_leaders_in_frame(
            df,
            setores_df,
            subsetores_df,
            only_current_leaders=only_current_leaders,
        )
        if updates:
            for _, row in redistributed.iterrows():
                mat = str(row.get("MAT", "")).strip()
                if not mat:
                    continue
                conn.execute(
                    """
                    UPDATE colaboradores
                    SET LIDER = ?, UPDATED_AT = CURRENT_TIMESTAMP
                    WHERE MAT = ? AND COALESCE(LIDER, '') <> ?
                    """,
                    (str(row.get("LIDER", "")).strip(), mat, str(row.get("LIDER", "")).strip()),
                )
            conn.commit()

    if updates and is_primary_db_path(db_path):
        try:
            export_collaborators_to_csv(db_path=db_path)
        except Exception as exc:
            errors.append(f"Lideres redistribuidos no banco, mas backup CSV falhou: {exc}")
    return updates, errors


def load_crud_changes_from_query() -> dict:
    raw = st.query_params.get("org_changes", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    if not raw:
        return {"upserts": {}, "deletes": []}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {"upserts": {}, "deletes": []}
    return {
        "upserts": parsed.get("upserts", {}) if isinstance(parsed.get("upserts", {}), dict) else {},
        "deletes": parsed.get("deletes", []) if isinstance(parsed.get("deletes", []), list) else [],
    }


def normalize_collaborator_payload(details: dict) -> dict:
    rename_map = {
        "mat": "MAT",
        "nome": "NOME",
        "cargo": "CARGO",
        "supersetor": "SUPERSETOR",
        "setor": "SETOR",
        "subsetor": "SUBSETOR",
        "liderMat": "LIDER",
        "posicao": "POSICAO",
        "observacoes": "OBSERVACOES",
    }
    row = {col: "" for col in COLLABORATOR_COLUMNS}
    for source_key, target_col in rename_map.items():
        row[target_col] = str(details.get(source_key, "")).strip()
    return row


def validate_collaborator_row(row: dict, valid_ids: set[str], allow_existing: bool = True) -> str:
    mat = str(row.get("MAT", "")).strip()
    if not mat:
        return "MAT e obrigatorio."
    if not str(row.get("NOME", "")).strip():
        return "Nome e obrigatorio."
    if not str(row.get("CARGO", "")).strip():
        return "Cargo e obrigatorio."
    if not str(row.get("POSICAO", "")).strip():
        return "Posicao e obrigatoria."
    lider = str(row.get("LIDER", "")).strip()
    if lider and lider == mat:
        return "O lider nao pode ser o proprio colaborador."
    if lider and lider not in valid_ids:
        return "O lider informado nao existe na tabela de colaboradores."
    if not allow_existing and mat in valid_ids:
        return "Ja existe um colaborador com essa MAT."
    return ""


def persist_crud_changes_to_db(changes: dict, db_path: str | Path = DB_PATH) -> list[str]:
    errors: list[str] = []
    wrote_changes = False
    changed_leader_ids: set[str] = set()
    with connect_db(db_path) as conn:
        existing_area_by_mat: dict[str, tuple[str, str]] = {}
        for row in conn.execute("SELECT MAT, SETOR, SUBSETOR FROM colaboradores").fetchall():
            existing_mat = str(row[0]).strip()
            if existing_mat:
                existing_area_by_mat[existing_mat] = (str(row[1] or "").strip(), str(row[2] or "").strip())
        existing_ids = set(existing_area_by_mat)

        delete_ids = {str(value).strip() for value in changes.get("deletes", []) if str(value).strip()}
        for mat in delete_ids:
            conn.execute("DELETE FROM colaboradores WHERE MAT = ?", (mat,))
            existing_ids.discard(mat)
            changed_leader_ids.add(mat)
            wrote_changes = True

        for _, details in (changes.get("upserts", {}) or {}).items():
            if not isinstance(details, dict):
                continue
            row = normalize_collaborator_payload(details)
            mat = row["MAT"]
            error = validate_collaborator_row(row, existing_ids | {mat}, allow_existing=True)
            if error:
                errors.append(f"{mat or 'sem MAT'}: {error}")
                continue
            conn.execute(
                """
                INSERT INTO colaboradores (MAT, NOME, CARGO, SUPERSETOR, SETOR, SUBSETOR, LIDER, POSICAO, OBSERVACOES, UPDATED_AT)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(MAT) DO UPDATE SET
                    NOME = excluded.NOME,
                    CARGO = excluded.CARGO,
                    SUPERSETOR = excluded.SUPERSETOR,
                    SETOR = excluded.SETOR,
                    SUBSETOR = excluded.SUBSETOR,
                    LIDER = excluded.LIDER,
                    POSICAO = excluded.POSICAO,
                    OBSERVACOES = excluded.OBSERVACOES,
                    UPDATED_AT = CURRENT_TIMESTAMP
                """,
                tuple(row[col] for col in COLLABORATOR_COLUMNS),
            )
            previous_area = existing_area_by_mat.get(mat)
            new_area = (row["SETOR"], row["SUBSETOR"])
            existing_ids.add(mat)
            if previous_area and previous_area != new_area:
                changed_leader_ids.add(mat)
            wrote_changes = True
        conn.commit()
    if wrote_changes and changed_leader_ids:
        try:
            setores_df, _, subsetores_df = load_hierarchy_from_db(db_path=db_path)
            _, redistribution_errors = redistribute_collaborator_leaders(
                setores_df,
                subsetores_df,
                only_current_leaders=changed_leader_ids,
                db_path=db_path,
            )
            errors.extend(redistribution_errors)
        except Exception as exc:
            errors.append(f"Alteracao salva, mas redistribuicao de liderados falhou: {exc}")
        if delete_ids:
            with connect_db(db_path) as conn:
                for mat in delete_ids:
                    conn.execute("UPDATE colaboradores SET LIDER = '', UPDATED_AT = CURRENT_TIMESTAMP WHERE LIDER = ?", (mat,))
                conn.commit()
    if wrote_changes and is_primary_db_path(db_path):
        try:
            export_collaborators_to_csv(db_path=db_path)
        except Exception as exc:
            errors.append(f"Alteracao salva no banco, mas backup CSV falhou: {exc}")
    return errors


def consume_crud_query(db_path: str | Path = DB_PATH) -> None:
    changes = load_crud_changes_from_query()
    if not changes.get("upserts") and not changes.get("deletes"):
        return
    errors = persist_crud_changes_to_db(changes, db_path=db_path)
    if errors:
        st.session_state["crud_errors"] = errors
    elif "crud_errors" in st.session_state:
        del st.session_state["crud_errors"]
    if "org_changes" in st.query_params:
        del st.query_params["org_changes"]
    st.rerun()


def apply_crud_changes(df: pd.DataFrame, changes: dict) -> pd.DataFrame:
    result = df.copy()
    if "OBSERVACOES" not in result.columns:
        result["OBSERVACOES"] = ""

    delete_ids = {str(value).strip() for value in changes.get("deletes", []) if str(value).strip()}
    if delete_ids:
        result = result[~result["MAT"].astype(str).isin(delete_ids)].copy()

    editable_columns = ["MAT", "NOME", "CARGO", "SUPERSETOR", "SETOR", "SUBSETOR", "LIDER", "POSICAO", "OBSERVACOES"]
    rename_map = {
        "mat": "MAT",
        "nome": "NOME",
        "cargo": "CARGO",
        "supersetor": "SUPERSETOR",
        "setor": "SETOR",
        "subsetor": "SUBSETOR",
        "liderMat": "LIDER",
        "posicao": "POSICAO",
        "observacoes": "OBSERVACOES",
    }

    for _, details in (changes.get("upserts", {}) or {}).items():
        if not isinstance(details, dict):
            continue
        mat = str(details.get("mat", "")).strip()
        if not mat or mat in delete_ids:
            continue

        row_values = {col: "" for col in result.columns}
        for source_key, target_col in rename_map.items():
            if target_col in row_values:
                row_values[target_col] = str(details.get(source_key, "")).strip()
        row_values["MAT"] = mat

        mask = result["MAT"].astype(str) == mat
        if mask.any():
            for col in editable_columns:
                if col in result.columns and col in row_values:
                    result.loc[mask, col] = row_values[col]
        else:
            result = pd.concat([result, pd.DataFrame([row_values])], ignore_index=True)

    return result.drop_duplicates(subset=["MAT"], keep="last").reset_index(drop=True)


def build_pyvis_network(
    work: pd.DataFrame,
    direction: str = "UD",
    highlighted_ids: set[str] | None = None,
    editor_df: pd.DataFrame | None = None,
    setores_df: pd.DataFrame | None = None,
    supersetores_df: pd.DataFrame | None = None,
    subsetores_df: pd.DataFrame | None = None,
) -> tuple[Network, dict[str, dict[str, list[dict]]]]:
    graph = nx.DiGraph()
    node_payload: dict[str, dict] = {}
    highlighted_ids = highlighted_ids or set()
    editor_source = editor_df if editor_df is not None else work
    
    # Preparar mapeamentos de container
    if setores_df is None:
        setores_df = pd.DataFrame()
    if supersetores_df is None:
        supersetores_df = pd.DataFrame()
    if subsetores_df is None:
        subsetores_df = pd.DataFrame()
    
    # Mapear SETOR -> SUPERSETOR
    setor_to_supersetor: dict[str, str] = {}
    supersetor_by_leader: dict[str, str] = {}
    if not supersetores_df.empty:
        for _, row in supersetores_df.iterrows():
            supersetor = str(row.get("SUPERSETOR", "")).strip()
            setor_filho = str(row.get("SETORFILHO", "")).strip()
            leader_id = str(row.get("LIDERMAT", "")).strip()
            if setor_filho and supersetor:
                setor_to_supersetor[setor_filho] = supersetor
            if leader_id and supersetor and leader_id not in supersetor_by_leader:
                supersetor_by_leader[leader_id] = supersetor
    
    # Mapear SUBSETOR -> SETOR
    subsetor_to_setor: dict[str, str] = {}
    if not subsetores_df.empty:
        for _, row in subsetores_df.iterrows():
            subsetor_to_setor[row["SUBSETOR"]] = row["SETORPAI"]

    setor_order: dict[str, int] = {}
    if not supersetores_df.empty:
        for idx, row in supersetores_df.reset_index(drop=True).iterrows():
            setor = str(row.get("SETORFILHO", "")).strip()
            if setor and setor not in setor_order:
                setor_order[setor] = int(idx)

    subsetor_order: dict[tuple[str, str], int] = {}
    if not subsetores_df.empty:
        for idx, row in subsetores_df.reset_index(drop=True).iterrows():
            setor = str(row.get("SETORPAI", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            if setor and subsetor and (setor, subsetor) not in subsetor_order:
                subsetor_order[(setor, subsetor)] = int(idx)

    node_org: dict[str, dict[str, str]] = {}
    
    # Dicionário para rastrear containers
    containers: dict[str, dict[str, list[dict]]] = {
        "subsetor": {},
        "setor": {},
        "supersetor": {},
    }

    def short_text(value: str, limit: int) -> str:
        text = (value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def sort_text(value: str) -> str:
        return (value or "").strip().casefold()

    def resolve_org(row: pd.Series) -> dict[str, str]:
        mat = str(row.get("MAT", "")).strip()
        setor = str(row.get("SETOR", "")).strip()
        subsetor = str(row.get("SUBSETOR", "")).strip()
        supersetor = str(row.get("SUPERSETOR", "")).strip()
        if not setor and subsetor in subsetor_to_setor:
            setor = subsetor_to_setor[subsetor]
        if not supersetor and setor in setor_to_supersetor:
            supersetor = setor_to_supersetor[setor]
        if not supersetor and mat in supersetor_by_leader:
            supersetor = supersetor_by_leader[mat]
        return {
            "supersetor": supersetor,
            "setor": setor,
            "subsetor": subsetor,
            "nome": str(row.get("NOME", "")).strip(),
            "cargo": str(row.get("CARGO", "")).strip(),
            "posicao": str(row.get("POSICAO", "")).strip(),
            "observacoes": str(row.get("OBSERVACOES", "")).strip(),
        }

    for _, row in work.iterrows():
        mat = row["MAT"]
        nome = row["NOME"] or "Sem nome"
        cargo = row["CARGO"] or "Sem cargo"
        posicao = row["POSICAO"] or "-"
        node_org[mat] = resolve_org(row)

        is_root = mat == "1979" or "glauber" in nome.lower()
        is_highlighted = mat in highlighted_ids

        if is_root:
            size = 34
        else:
            size = 22

        payload = {
            "label": f"{short_text(nome, 24)}\n{short_text(cargo, 26)}",
            "title": "Clique para ver detalhes",
            "is_root": is_root,
            "is_highlighted": is_highlighted,
            "size": size,
        }
        graph.add_node(mat, **payload)
        node_payload[mat] = payload

    id_set = set(work["MAT"].tolist())
    name_by_id = {
        str(row["MAT"]).strip(): str(row["NOME"]).strip()
        for _, row in editor_source.iterrows()
    }
    name_by_id.update({
        str(row["MAT"]).strip(): str(row["NOME"]).strip()
        for _, row in work.iterrows()
    })

    def unique_sorted(column: str) -> list[str]:
        if column not in editor_source.columns:
            return []
        return sorted({str(value).strip() for value in editor_source[column].tolist() if str(value).strip()})

    nivel_options = ["I", "II", "III", "IV", "V", "VI", "VII"]

    def split_cargo_nivel(cargo: str) -> tuple[str, str]:
        text = (cargo or "").strip()
        if " " not in text:
            return text, ""
        cargo_base, nivel = text.rsplit(" ", 1)
        nivel = nivel.strip()
        if nivel in nivel_options:
            return cargo_base.strip(), nivel
        return text, ""

    sectors_for_editor = unique_sorted("SETOR")
    if not setores_df.empty and "SETOR" in setores_df.columns:
        sectors_for_editor = sorted(
            set(sectors_for_editor)
            | {str(value).strip() for value in setores_df["SETOR"].tolist() if str(value).strip()},
            key=sort_text,
        )
    cargos_for_editor = unique_sorted("CARGO")
    cargos_base_for_editor = sorted({split_cargo_nivel(cargo)[0] for cargo in cargos_for_editor if split_cargo_nivel(cargo)[0]}, key=sort_text)
    positions_for_editor = unique_sorted("POSICAO")
    cargo_position_map = cargo_position_map_from_df(editor_source)

    subsetors_by_sector: dict[str, list[str]] = defaultdict(list)
    if not subsetores_df.empty:
        for _, row in subsetores_df.iterrows():
            setor = str(row.get("SETORPAI", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            if setor and subsetor and subsetor not in subsetors_by_sector[setor]:
                subsetors_by_sector[setor].append(subsetor)
    if "SETOR" in editor_source.columns and "SUBSETOR" in editor_source.columns:
        for _, row in editor_source.iterrows():
            setor = str(row.get("SETOR", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            if setor and subsetor and subsetor not in subsetors_by_sector[setor]:
                subsetors_by_sector[setor].append(subsetor)
    subsetors_by_sector = {
        setor: sorted(values, key=sort_text)
        for setor, values in subsetors_by_sector.items()
    }

    valid_subsetor_leaders, valid_sector_leaders = build_org_leader_lookup(editor_source, setores_df, subsetores_df)
    sector_leaders = {
        setor: {"mat": lider_id, "nome": name_by_id.get(lider_id, lider_id)}
        for setor, lider_id in valid_sector_leaders.items()
    }
    subsetor_leaders = {
        f"{setor}||{subsetor}": {"mat": lider_id, "nome": name_by_id.get(lider_id, lider_id)}
        for (setor, subsetor), lider_id in valid_subsetor_leaders.items()
    }

    for _, row in work.iterrows():
        parent = row["LIDER"]
        child = row["MAT"]
        if parent and parent in id_set and parent != child:
            graph.add_edge(parent, child)

    direct_reports = {node: graph.out_degree(node) for node in graph.nodes}
    leader_spans = [span for span in direct_reports.values() if span > 0]
    min_span = min(leader_spans) if leader_spans else 0
    max_span = max(leader_spans) if leader_spans else 0

    def lerp_color(start_hex: str, end_hex: str, t: float) -> str:
        t = max(0.0, min(1.0, t))
        s = start_hex.lstrip("#")
        e = end_hex.lstrip("#")
        sr, sg, sb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        er, eg, eb = int(e[0:2], 16), int(e[2:4], 16), int(e[4:6], 16)
        rr = round(sr + (er - sr) * t)
        rg = round(sg + (eg - sg) * t)
        rb = round(sb + (eb - sb) * t)
        return f"#{rr:02x}{rg:02x}{rb:02x}"

    is_horizontal = direction == "LR"
    net = Network(
        height="760px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
    )

    def sort_key(node_id: str) -> tuple:
        org = node_org.get(node_id, {})
        setor = org.get("setor", "")
        subsetor = org.get("subsetor", "")
        known_setor = setor in setor_order
        known_subsetor = (setor, subsetor) in subsetor_order
        subsetor_group = 0 if not subsetor else 1 if known_subsetor else 2
        return (
            sort_text(org.get("supersetor", "")),
            0 if known_setor else 1,
            setor_order.get(setor, 999_999),
            sort_text(setor),
            subsetor_group,
            subsetor_order.get((setor, subsetor), 999_999),
            sort_text(subsetor),
            sort_text(org.get("nome", graph.nodes[node_id].get("label", node_id))),
            sort_text(org.get("cargo", "")),
            node_id,
        )

    parent_of: dict[str, str] = {}
    for _, row in work.iterrows():
        child = row["MAT"]
        parent = row["LIDER"]
        if parent and parent in id_set and parent != child:
            parent_of[child] = parent

    children: dict[str, list[str]] = defaultdict(list)
    for child, parent in parent_of.items():
        children[parent].append(child)
    for parent in children:
        children[parent].sort(key=sort_key)

    roots = [node for node in graph.nodes if node not in parent_of]
    roots.sort(key=lambda n: (n != "1979", sort_key(n)))
    if not roots and graph.nodes:
        roots = [next(iter(graph.nodes))]

    subtree_leaves: dict[str, int] = {}

    def count_leaves(node_id: str) -> int:
        if node_id in subtree_leaves:
            return subtree_leaves[node_id]
        kids = children.get(node_id, [])
        if not kids:
            subtree_leaves[node_id] = 1
            return 1
        total = sum(count_leaves(child) for child in kids)
        subtree_leaves[node_id] = max(1, total)
        return subtree_leaves[node_id]

    for root in roots:
        count_leaves(root)

    def position_rank(node_id: str) -> int:
        posicao = sort_text(node_org.get(node_id, {}).get("posicao", ""))
        if "estrat" in posicao:
            return 0
        if "tat" in posicao or "tát" in posicao:
            return 1
        if "operacional" in posicao:
            return 2
        return 1

    mixed_level_parent: dict[str, bool] = {}
    for parent, kids in children.items():
        child_ranks = {position_rank(child) for child in kids}
        mixed_level_parent[parent] = 1 in child_ranks and 2 in child_ranks

    def child_subsetor_key(node_id: str) -> tuple[str, str] | None:
        org = node_org.get(node_id, {})
        subsetor = org.get("subsetor", "")
        if not subsetor:
            return None
        return (org.get("setor", ""), subsetor)

    mixed_subsetor_groups: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for parent, kids in children.items():
        ranks_by_subsetor: dict[tuple[str, str], set[int]] = defaultdict(set)
        for child in kids:
            key = child_subsetor_key(child)
            if key is not None:
                ranks_by_subsetor[key].add(position_rank(child))
        for key, ranks in ranks_by_subsetor.items():
            if 1 in ranks and 2 in ranks:
                mixed_subsetor_groups[parent].add(key)

    def shares_tactical_subsetor_branch(parent: str, child: str) -> bool:
        return position_rank(child) == 2 and child_subsetor_key(child) in mixed_subsetor_groups.get(parent, set())

    def child_level_gap(parent: str, child: str) -> int:
        if mixed_level_parent.get(parent) and position_rank(child) == 2:
            return 2
        return 1

    depth: dict[str, int] = {}
    queue = deque((root, 0) for root in roots)
    while queue:
        node, d = queue.popleft()
        if node in depth and depth[node] <= d:
            continue
        depth[node] = d
        for child in children.get(node, []):
            queue.append((child, d + child_level_gap(node, child)))

    max_depth = max(depth.values(), default=0)
    for node in sorted(graph.nodes, key=sort_key):
        if node not in depth:
            max_depth += 1
            depth[node] = max_depth

    slot: dict[str, float] = {}
    cursor = 0.0
    tree_gap_slots = 1.6
    sector_gap_slots = 0.45
    subsetor_gap_slots = 0.55

    def place(node_id: str) -> None:
        nonlocal cursor
        kids = children.get(node_id, [])
        if not kids:
            slot[node_id] = cursor
            cursor += 1.0
            return
        first_cursor = cursor
        previous_sector = ""
        previous_subsetor = ""
        for child in kids:
            child_sector = node_org.get(child, {}).get("setor", "")
            child_subsetor = node_org.get(child, {}).get("subsetor", "")
            if previous_sector and child_sector and child_sector != previous_sector:
                cursor += sector_gap_slots
            elif (
                previous_sector
                and child_sector == previous_sector
                and previous_subsetor
                and child_subsetor
                and child_subsetor != previous_subsetor
            ):
                cursor += subsetor_gap_slots
            place(child)
            if child_sector:
                previous_sector = child_sector
            if child_subsetor:
                previous_subsetor = child_subsetor
        slot[node_id] = (first_cursor + (cursor - 1.0)) / 2.0

    for idx, root in enumerate(roots):
        place(root)
        if idx < len(roots) - 1:
            cursor += tree_gap_slots

    for node in sorted(graph.nodes, key=sort_key):
        if node not in slot:
            slot[node] = cursor
            cursor += 1.0

    if is_horizontal:
        level_gap = 820
        sibling_gap = 220
    else:
        level_gap = 340
        sibling_gap = 240

    def node_primary_half_width(node_id: str) -> float:
        payload = node_payload.get(node_id, {})
        label = str(payload.get("label", ""))
        longest_line = max((len(line) for line in label.split("\n")), default=0)
        text_width = longest_line * 7.2
        node_width = (max(payload.get("size", 22), 30) if payload.get("is_highlighted") else payload.get("size", 22)) * 2.0
        return max(48.0, text_width / 2.0, node_width)

    node_box_reserved_chars = 26
    node_box_char_width = 7.2
    node_box_horizontal_padding = 44.0

    def node_canvas_extents(node_id: str) -> tuple[float, float, float]:
        payload = node_payload.get(node_id, {})
        label = str(payload.get("label", ""))
        lines = label.split("\n")
        line_count = len(lines) + (1 if direct_reports.get(node_id, 0) > 0 else 0)
        longest_line = max((len(line) for line in lines), default=0)
        label_width = (max(node_box_reserved_chars, longest_line) * node_box_char_width) + node_box_horizontal_padding
        size = max(float(payload.get("size", 22) or 22), 30.0 if payload.get("is_highlighted") else 22.0)
        half_width = max(64.0, label_width / 2.0, size * 2.0)
        top_extent = max(56.0, size * 2.15)
        bottom_extent = max(74.0, (size * 1.85) + (max(1, line_count) * 15.0))
        return half_width, top_extent, bottom_extent

    def node_gap_slots(left_id: str, right_id: str, gap_px: float = 22.0) -> float:
        return (node_primary_half_width(left_id) + node_primary_half_width(right_id) + gap_px) / sibling_gap

    def shift_subtree_slots(node_id: str, delta: float) -> None:
        slot[node_id] = slot.get(node_id, 0.0) + delta
        for child_id in children.get(node_id, []):
            shift_subtree_slots(child_id, delta)

    def compact_operational_under_mixed_parents() -> None:
        for parent in sorted(children, key=lambda node_id: depth.get(node_id, 0)):
            kids = children.get(parent, [])
            if not kids or not mixed_level_parent.get(parent) or parent not in slot:
                continue
            operational = [child for child in kids if position_rank(child) == 2 and child_level_gap(parent, child) > 1]
            if not operational:
                continue
            operational.sort(key=sort_key)
            spacing = 0.68
            start = slot[parent] - ((len(operational) - 1) * spacing / 2.0)
            for index, child in enumerate(operational):
                target = start + (index * spacing)
                shift_subtree_slots(child, target - slot.get(child, target))

    def enforce_level_spacing(min_gap_slots: float = 0.64) -> None:
        nodes_by_depth: dict[int, list[str]] = defaultdict(list)
        for node_id, node_depth in depth.items():
            if node_id in slot:
                nodes_by_depth[node_depth].append(node_id)
        for node_depth in sorted(nodes_by_depth):
            ordered = sorted(nodes_by_depth[node_depth], key=lambda node_id: (slot.get(node_id, 0.0), sort_key(node_id)))
            previous_node: str | None = None
            for node_id in ordered:
                current = slot.get(node_id, 0.0)
                if previous_node is not None:
                    required_gap = max(min_gap_slots, node_gap_slots(previous_node, node_id))
                    previous_slot = slot.get(previous_node, current)
                    if current - previous_slot < required_gap:
                        delta = (previous_slot + required_gap) - current
                        shift_subtree_slots(node_id, delta)
                        current += delta
                previous_node = node_id

    def enforce_sibling_text_spacing(gap_px: float = 18.0) -> None:
        for parent in sorted(children, key=lambda node_id: depth.get(node_id, 0), reverse=True):
            kids = [child for child in children.get(parent, []) if child in slot]
            if len(kids) < 2:
                continue
            kids.sort(key=lambda node_id: (slot.get(node_id, 0.0), sort_key(node_id)))
            previous = kids[0]
            for child in kids[1:]:
                required_gap = node_gap_slots(previous, child, gap_px)
                actual_gap = slot.get(child, 0.0) - slot.get(previous, 0.0)
                if actual_gap < required_gap:
                    delta = required_gap - actual_gap
                    shift_subtree_slots(child, delta)
                previous = child

    compact_operational_under_mixed_parents()
    enforce_sibling_text_spacing()
    enforce_level_spacing()

    def compact_subsetor_roots(spacing_slots: float = 0.72) -> None:
        groups = subsetor_nodes()
        if not groups:
            return
        for nodes in groups.values():
            node_set = set(nodes)
            roots_in_group = [
                node_id
                for node_id in nodes
                if node_id in slot and parent_of.get(node_id) not in node_set
            ]
            if len(roots_in_group) < 2:
                continue
            roots_in_group.sort(key=lambda node_id: (position_rank(node_id), slot.get(node_id, 0.0), sort_key(node_id)))
            center = sum(slot[node_id] for node_id in roots_in_group) / len(roots_in_group)
            start = center - ((len(roots_in_group) - 1) * spacing_slots / 2.0)
            for index, node_id in enumerate(roots_in_group):
                target = start + (index * spacing_slots)
                shift_subtree_slots(node_id, target - slot.get(node_id, target))

    def keep_leaders_off_parent_axis(clearance_slots: float = 0.42) -> None:
        for parent in sorted(children, key=lambda node_id: depth.get(node_id, 0), reverse=True):
            kids = children.get(parent, [])
            if len(kids) < 2 or parent not in slot:
                continue
            parent_axis = slot[parent]
            for index, child in enumerate(kids):
                is_tactical_under_strategic = position_rank(parent) == 0 and position_rank(child) == 1
                if not children.get(child) and not is_tactical_under_strategic:
                    continue
                if abs(slot.get(child, 0.0) - parent_axis) > 0.03:
                    continue
                direction_sign = -1.0 if index < len(kids) / 2 else 1.0
                required_clearance = max(clearance_slots, (node_primary_half_width(parent) + node_primary_half_width(child) + 18.0) / sibling_gap)
                shift_subtree_slots(child, direction_sign * required_clearance)

    keep_leaders_off_parent_axis()
    enforce_sibling_text_spacing()
    enforce_level_spacing()

    def sector_nodes() -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for node_id in graph.nodes:
            setor = node_org.get(node_id, {}).get("setor", "")
            if setor:
                groups[setor].append(node_id)
        return groups

    def subsetor_nodes() -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for node_id in graph.nodes:
            org = node_org.get(node_id, {})
            setor = org.get("setor", "")
            subsetor = org.get("subsetor", "")
            if setor and subsetor:
                groups[f"{setor}||{subsetor}"].append(node_id)
        return groups

    def supersetor_nodes() -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for node_id in graph.nodes:
            supersetor = node_org.get(node_id, {}).get("supersetor", "")
            if supersetor:
                groups[supersetor].append(node_id)
        return groups

    def separate_group_slots(
        groups: dict[str, list[str]],
        *,
        primary_padding: float,
        secondary_padding_before: float,
        secondary_padding_after: float,
        gap: float,
    ) -> None:
        if len(groups) < 2:
            return
        extents_by_node = {node_id: node_canvas_extents(node_id) for node_id in graph.nodes}

        def make_box(name: str, nodes: list[str]) -> dict[str, float | str]:
            primary_min_values: list[float] = []
            primary_max_values: list[float] = []
            secondary_min_values: list[float] = []
            secondary_max_values: list[float] = []
            for node_id in nodes:
                if node_id not in slot or node_id not in depth:
                    continue
                half_width, top_extent, bottom_extent = extents_by_node.get(node_id, (64.0, 56.0, 74.0))
                primary = slot[node_id] * sibling_gap
                secondary = depth[node_id] * level_gap
                primary_min_values.append(primary - half_width)
                primary_max_values.append(primary + half_width)
                secondary_min_values.append(secondary - top_extent)
                secondary_max_values.append(secondary + bottom_extent)
            if not primary_min_values or not secondary_min_values:
                return {}
            primary_min = min(primary_min_values) - primary_padding
            primary_max = max(primary_max_values) + primary_padding
            label_width = (len(str(name or "")) * 8.4) + 30.0
            if not is_horizontal:
                primary_max = max(primary_max, primary_min + label_width)
            return {
                "name": name,
                "primary_min": primary_min,
                "primary_max": primary_max,
                "secondary_min": min(secondary_min_values) - secondary_padding_before,
                "secondary_max": max(secondary_max_values) + secondary_padding_after,
            }

        boxes = [box for name, nodes in groups.items() if (box := make_box(name, nodes))]
        boxes.sort(key=lambda box: (box["primary_min"], box["primary_max"], sort_text(str(box["name"]))))
        group_names = [str(box["name"]) for box in boxes]

        for _ in range(3):
            placed: list[dict[str, float | str]] = []
            moved = False
            for group_name in group_names:
                current = make_box(group_name, groups.get(group_name, []))
                if not current:
                    continue
                overlap = 0.0
                for previous in placed:
                    secondary_overlap = previous["secondary_max"] > current["secondary_min"] and current["secondary_max"] > previous["secondary_min"]
                    if not secondary_overlap:
                        continue
                    overlap = max(overlap, previous["primary_max"] + gap - current["primary_min"])
                if overlap > 0:
                    delta_slots = overlap / sibling_gap
                    for node_id in groups.get(group_name, []):
                        slot[node_id] = slot.get(node_id, 0.0) + delta_slots
                    current["primary_min"] = float(current["primary_min"]) + overlap
                    current["primary_max"] = float(current["primary_max"]) + overlap
                    moved = True
                placed.append(current)
            if not moved:
                break

    compact_subsetor_roots()
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    fixed_group_gap = 18
    separate_group_slots(
        subsetor_nodes(),
        primary_padding=18,
        secondary_padding_before=18,
        secondary_padding_after=30,
        gap=fixed_group_gap,
    )
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    separate_group_slots(
        sector_nodes(),
        primary_padding=26,
        secondary_padding_before=24,
        secondary_padding_after=42,
        gap=fixed_group_gap,
    )
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    separate_group_slots(
        supersetor_nodes(),
        primary_padding=30,
        secondary_padding_before=28,
        secondary_padding_after=44,
        gap=fixed_group_gap,
    )
    enforce_sibling_text_spacing()
    enforce_level_spacing()

    positions: dict[str, tuple[float, float]] = {}
    for node in graph.nodes:
        branch_axis = slot[node] * sibling_gap
        hierarchy_axis = depth[node] * level_gap
        if is_horizontal:
            positions[node] = (hierarchy_axis, branch_axis)
        else:
            positions[node] = (branch_axis, hierarchy_axis)

    for node_id, attrs in node_payload.items():
        x, y = positions.get(node_id, (0.0, 0.0))
        span = direct_reports.get(node_id, 0)
        label_text = attrs["label"]
        title_text = attrs["title"]
        is_highlighted = bool(attrs.get("is_highlighted"))
        is_root = bool(attrs.get("is_root"))

        # Extrair informações de container do trabalho
        org = node_org.get(node_id, {})
        setor = org.get("setor", "")
        subsetor = org.get("subsetor", "")
        supersetor = org.get("supersetor", "")

        if span > 0 and max_span > 0:
            if max_span == min_span:
                t = 1.0
            else:
                t = (span - min_span) / (max_span - min_span)
            node_color = {
                "background": lerp_color("#d8e6f8", BRAND_BLUE, t),
                "border": lerp_color("#9db7da", "#0f274a", t),
            }
        elif is_root:
            node_color = {"background": BRAND_GREEN, "border": "#1f9d66"}
        else:
            node_color = {"background": "#b8cbe6", "border": "#7f9fc4"}

        border_width = 1
        node_size = attrs["size"]
        if is_highlighted:
            node_color = {"background": BRAND_GREEN, "border": BRAND_BLUE}
            border_width = 3
            node_size = max(node_size, 30)

        if span > 0:
            label_text = f"{label_text}\nSpan: {span}"

        node_kwargs = {
            "label": label_text,
            "title": "Clique para ver detalhes",
            "color": node_color,
            "borderWidth": border_width,
            "size": node_size,
            "x": x,
            "y": y,
            "fixed": {"x": True, "y": True},
            "physics": False,
            "collaborator": {
                "mat": node_id,
                "nome": org.get("nome", ""),
                "cargo": org.get("cargo", ""),
                "supersetor": supersetor,
                "setor": setor,
                "subsetor": subsetor,
                "lider": name_by_id.get(parent_of.get(node_id, ""), ""),
                "liderMat": parent_of.get(node_id, ""),
                "posicao": org.get("posicao", ""),
                "observacoes": org.get("observacoes", ""),
                "baseLabel": attrs["label"],
                "span": span,
            },
            "containerInfo": {
                "supersetor": supersetor,
                "setor": setor,
                "subsetor": subsetor,
            },
        }
        
        # Rastrear informações de container para posterior renderização
        def add_container_node(container_type: str, container_key: str) -> None:
            if not container_key:
                return
            if container_key not in containers[container_type]:
                containers[container_type][container_key] = []
            containers[container_type][container_key].append({
                "id": node_id,
                "x": x,
                "y": y,
                "size": node_size,
            })

        add_container_node("supersetor", supersetor)
        add_container_node("setor", setor)
        add_container_node("subsetor", subsetor)

        net.add_node(node_id, **node_kwargs)

    bend_seq = 0
    line_color = "#7f95b5"

    def branch_offset(parent: str, child: str, distance: float) -> float:
        if mixed_level_parent.get(parent):
            rank = position_rank(child)
            if rank == 1:
                return min(max(90.0, distance * 0.35), max(90.0, distance - 80.0))
            if rank == 2:
                if shares_tactical_subsetor_branch(parent, child):
                    tactical_distance = distance / max(1, child_level_gap(parent, child))
                    return min(max(90.0, tactical_distance * 0.35), max(90.0, tactical_distance - 80.0))
                return max(90.0, distance - min(130.0, max(90.0, distance * 0.35)))
        return max(90.0, distance * 0.5)

    for parent, child in graph.edges:
        if parent not in positions or child not in positions:
            continue

        sx, sy = positions[parent]
        tx, ty = positions[child]

        if is_horizontal:
            mid_x = sx + branch_offset(parent, child, tx - sx)
            if mid_x > tx - 30:
                mid_x = (sx + tx) / 2
            b1_pos = (mid_x, sy)
            b2_pos = (mid_x, ty)
        else:
            mid_y = sy + branch_offset(parent, child, ty - sy)
            if mid_y > ty - 20:
                mid_y = (sy + ty) / 2
            b1_pos = (sx, mid_y)
            b2_pos = (tx, mid_y)

        b1 = f"__bend_{bend_seq}_1"
        b2 = f"__bend_{bend_seq}_2"
        bend_seq += 1

        bend_style = {
            "size": 0.1,
            "shape": "dot",
            "label": "",
            "title": "",
            "font": {"size": 1, "color": "rgba(0,0,0,0)"},
            "color": {"background": "rgba(0,0,0,0)", "border": "rgba(0,0,0,0)"},
            "borderWidth": 0,
            "fixed": {"x": True, "y": True},
            "physics": False,
        }
        net.add_node(b1, x=b1_pos[0], y=b1_pos[1], **bend_style)
        net.add_node(b2, x=b2_pos[0], y=b2_pos[1], **bend_style)

        net.add_edge(parent, b1, arrows="", color=line_color, width=2.0)
        net.add_edge(b1, b2, arrows="", color=line_color, width=2.0)
        net.add_edge(b2, child, arrows="to", color=line_color, width=2.0)

    net.org_editor_data = {
        "cargos": cargos_for_editor,
        "cargosBase": cargos_base_for_editor,
        "niveis": nivel_options,
        "posicoes": positions_for_editor,
        "setores": sectors_for_editor,
        "subsetoresPorSetor": subsetors_by_sector,
        "lideresSetor": sector_leaders,
        "lideresSubsetor": subsetor_leaders,
        "posicaoPorCargo": cargo_position_map,
        "supersetorPorSetor": setor_to_supersetor,
        "direction": direction,
    }

    options = {
        "layout": {"hierarchical": {"enabled": False}},
        "edges": {"smooth": {"enabled": False}},
        "physics": {"enabled": False},
        "interaction": {
            "hover": True,
            "dragView": True,
            "zoomView": True,
            "zoomSpeed": 0.35,
            "navigationButtons": True,
        },
    }

    net.set_options(json.dumps(options))

    return net, containers


def render_pyvis(
    net: Network,
    containers: dict | None = None,
    height: int = 780,
    initial_scale: float = 0.42,
    enable_crud: bool = True,
) -> None:
    html_content = net.generate_html(notebook=False)
    def json_for_script(value: object) -> str:
        return (
            json.dumps(value, ensure_ascii=False)
            .replace("</", "<\\/")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    editor_json = json_for_script(getattr(net, "org_editor_data", {}))
    initial_scale_json = json.dumps(initial_scale)
    enable_crud_json = json.dumps(enable_crud)
    
    # Adicionar JavaScript para renderizar containers
    container_styles = """
    <style>
    .org-crud-toolbar {
        position: absolute;
        top: 12px;
        right: 12px;
        z-index: 15;
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: Arial, sans-serif;
    }
    .org-chart-search {
        width: min(280px, 38vw);
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 8px 10px;
        background: #FFFFFF;
        color: #14315E;
        font-size: 13px;
        box-shadow: 0 8px 24px rgba(15, 39, 74, 0.12);
        outline: none;
    }
    .org-chart-search:focus {
        border-color: rgba(20, 49, 94, 0.55);
    }
    .org-chart-search-group {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .org-search-nav {
        display: none;
        align-items: center;
        gap: 6px;
    }
    .org-search-nav.is-visible {
        display: flex;
    }
    .org-search-nav-button {
        width: 34px;
        height: 34px;
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        background: #FFFFFF;
        color: #14315E;
        cursor: pointer;
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
        box-shadow: 0 8px 24px rgba(15, 39, 74, 0.12);
    }
    .org-search-nav-button:hover:not(:disabled) {
        border-color: rgba(20, 49, 94, 0.45);
    }
    .org-search-nav-button:disabled {
        cursor: default;
        opacity: 0.42;
    }
    .org-search-count {
        min-width: 44px;
        color: #14315E;
        font-size: 12px;
        font-weight: 800;
        text-align: center;
    }
    .org-crud-button {
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 8px 12px;
        background: #FFFFFF;
        color: #14315E;
        cursor: pointer;
        font-size: 13px;
        font-weight: 800;
        box-shadow: 0 8px 24px rgba(15, 39, 74, 0.12);
    }
    .org-crud-button:hover {
        border-color: rgba(20, 49, 94, 0.45);
    }
    .collab-modal-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(15, 39, 74, 0.24);
        z-index: 20;
        display: none;
        align-items: center;
        justify-content: center;
        pointer-events: auto;
        font-family: Arial, sans-serif;
    }
    .collab-modal-backdrop.is-open {
        display: flex;
    }
    .collab-modal {
        width: min(900px, calc(100% - 32px));
        max-height: calc(100% - 32px);
        overflow: auto;
        background: #FFFFFF;
        border: 1px solid rgba(20, 49, 94, 0.16);
        border-radius: 8px;
        box-shadow: 0 18px 54px rgba(15, 39, 74, 0.22);
        color: #14315E;
    }
    .collab-modal-header,
    .collab-modal-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 16px 20px;
        border-bottom: 1px solid rgba(20, 49, 94, 0.1);
    }
    .collab-modal-footer {
        border-top: 1px solid rgba(20, 49, 94, 0.1);
        border-bottom: 0;
        justify-content: flex-end;
        flex-wrap: wrap;
    }
    .collab-modal-title {
        margin: 0;
        font-size: 20px;
        line-height: 1.2;
        font-weight: 800;
    }
    .collab-modal-body {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px 16px;
        padding: 18px 20px 20px 20px;
    }
    .collab-field.full {
        grid-column: 1 / -1;
    }
    .collab-field label {
        display: block;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 7px;
        text-transform: uppercase;
        color: #53657f;
    }
    .collab-field input,
    .collab-field select,
    .collab-field textarea {
        width: 100%;
        min-width: 0;
        box-sizing: border-box;
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 10px 11px;
        color: #14315E;
        background: #FFFFFF;
        font-size: 14px;
        font-family: Arial, sans-serif;
    }
    .collab-field textarea {
        min-height: 76px;
        resize: vertical;
    }
    .collab-field input[readonly] {
        background: #F3F6FA;
        color: #53657f;
    }
    .collab-modal-message {
        grid-column: 1 / -1;
        min-height: 18px;
        color: #BE123C;
        font-size: 12px;
        font-weight: 800;
    }
    .collab-button {
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 9px 14px;
        background: #FFFFFF;
        color: #14315E;
        cursor: pointer;
        font-weight: 800;
    }
    .collab-button.primary {
        background: #14315E;
        border-color: #14315E;
        color: #FFFFFF;
    }
    .collab-button.danger {
        border-color: rgba(190, 18, 60, 0.35);
        color: #BE123C;
    }
    .collab-button.icon {
        border: 0;
        padding: 4px 6px;
        font-size: 20px;
        line-height: 1;
        box-shadow: none;
    }
    @media (max-width: 680px) {
        .collab-modal-body {
            grid-template-columns: 1fr;
        }
    }
    </style>

    <script>
    (function() {
        const editorData = """ + editor_json + """;
        const initialScale = """ + initial_scale_json + """;
        const crudEnabled = """ + enable_crud_json + """;
        const STORAGE_KEY = 'org_chart_crud_changes_v1';
        const MIN_ZOOM_LEVEL = 0.18;
        const MAX_ZOOM_LEVEL = 2.5;
        const WHEEL_ZOOM_SENSITIVITY = 0.0017;
        const TRACKPAD_ZOOM_SENSITIVITY = 0.004;
        const MAX_WHEEL_ZOOM_DELTA = 120;
        const NODE_LABEL_MAX_CHARS = 26;
        const NODE_LABEL_CHAR_WIDTH = 7.2;
        const NODE_LABEL_HORIZONTAL_PADDING = 44;
        let eventsBound = false;
        let initialViewApplied = false;
        let modalInstalled = false;
        let isClampingZoom = false;
        let wheelZoomInstalled = false;
        let lastZoomSafeView = null;
        let localSearchState = { query: '', matches: [], currentIndex: 0 };

        function getVisNetwork() {
            if (typeof network !== 'undefined' && network && typeof network.redraw === 'function') return network;
            if (window.network && typeof window.network.redraw === 'function') return window.network;
            return null;
        }

        function getNodesDataset() {
            if (typeof nodes !== 'undefined' && nodes) return nodes;
            return window.nodes || null;
        }

        function realGraphNodes() {
            const ds = getNodesDataset();
            if (!ds) return [];
            return ds.get().filter(node => !String(node.id).startsWith('__bend_') && node.collaborator);
        }

        function scheduleRedraw() {
            const visNetwork = getVisNetwork();
            if (visNetwork && typeof visNetwork.redraw === 'function') visNetwork.redraw();
        }

        function currentContainers() {
            const data = { supersetor: {}, setor: {}, subsetor: {} };
            realGraphNodes().forEach(node => {
                const details = node.containerInfo || {};
                const item = {
                    id: node.id,
                    x: Number(node.x) || 0,
                    y: Number(node.y) || 0,
                    size: Number(node.size) || 22,
                    label: String(node.label || '')
                };
                if (details.supersetor) {
                    if (!data.supersetor[details.supersetor]) data.supersetor[details.supersetor] = [];
                    data.supersetor[details.supersetor].push(item);
                }
                if (details.setor) {
                    if (!data.setor[details.setor]) data.setor[details.setor] = [];
                    data.setor[details.setor].push(item);
                }
                if (details.subsetor) {
                    if (!data.subsetor[details.subsetor]) data.subsetor[details.subsetor] = [];
                    data.subsetor[details.subsetor].push(item);
                }
            });
            return data;
        }

        function nodeCanvasBox(visNetwork, node) {
            if (!node) return null;
            const lines = String(node.label || '').split('\\n');
            const labelWidth = (Math.max(
                NODE_LABEL_MAX_CHARS,
                ...lines.map(line => line.length)
            ) * NODE_LABEL_CHAR_WIDTH) + NODE_LABEL_HORIZONTAL_PADDING;
            const size = Number(node.size) || 22;
            const halfWidth = Math.max(64, labelWidth / 2, size * 2.0);
            const topExtent = Math.max(56, size * 2.15);
            const bottomExtent = Math.max(74, (size * 1.85) + (Math.max(1, lines.length) * 15));
            const x = Number(node.x) || 0;
            const y = Number(node.y) || 0;
            return { left: x - halfWidth, right: x + halfWidth, top: y - topExtent, bottom: y + bottomExtent };
        }

        function buildContainerBox(type, name, nodes, visNetwork) {
            let minX = Infinity;
            let maxX = -Infinity;
            let minY = Infinity;
            let maxY = -Infinity;
            let count = 0;
            nodes.forEach(node => {
                const box = nodeCanvasBox(visNetwork, node);
                if (!box) return;
                minX = Math.min(minX, box.left);
                maxX = Math.max(maxX, box.right);
                minY = Math.min(minY, box.top);
                maxY = Math.max(maxY, box.bottom);
                count += 1;
            });
            if (!count || !Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) return null;

            const padding = {
                supersetor: { x: 30, top: 28, bottom: 44 },
                setor: { x: 26, top: 24, bottom: 42 },
                subsetor: { x: 18, top: 18, bottom: 32 }
            }[type] || { x: 24, top: 22, bottom: 38 };

            const labelWidth = String(name || '').length * 8.4 + 30;
            const left = minX - padding.x;
            const right = Math.max(maxX + padding.x, left + labelWidth);
            return {
                type,
                name,
                left: left,
                right: right,
                top: minY - padding.top,
                bottom: maxY + padding.bottom
            };
        }

        function roundedRectPath(ctx, x, y, width, height, radius) {
            const r = Math.max(0, Math.min(radius, Math.abs(width) / 2, Math.abs(height) / 2));
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.lineTo(x + width - r, y);
            ctx.quadraticCurveTo(x + width, y, x + width, y + r);
            ctx.lineTo(x + width, y + height - r);
            ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
            ctx.lineTo(x + r, y + height);
            ctx.quadraticCurveTo(x, y + height, x, y + height - r);
            ctx.lineTo(x, y + r);
            ctx.quadraticCurveTo(x, y, x + r, y);
            ctx.closePath();
        }

        function drawContainerBox(ctx, box, visNetwork) {
            const styles = {
                supersetor: { fill: 'rgba(20, 49, 94, 0.04)', stroke: 'rgba(20, 49, 94, 0.25)', width: 2, dash: [18, 18] },
                setor: { fill: 'rgba(47, 214, 139, 0.08)', stroke: 'rgba(47, 214, 139, 0.6)', width: 2, dash: [] },
                subsetor: { fill: 'rgba(0, 0, 0, 0)', stroke: 'rgba(20, 49, 94, 0.35)', width: 1.5, dash: [10, 10] }
            };
            const style = styles[box.type] || styles.setor;
            const width = box.right - box.left;
            const height = box.bottom - box.top;
            if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return;

            const scale = visNetwork && typeof visNetwork.getScale === 'function' ? visNetwork.getScale() : 1;
            const fontSize = Math.max(14, Math.min(22, 16 / Math.max(scale, 0.35)));
            ctx.save();
            roundedRectPath(ctx, box.left, box.top, width, height, 8);
            ctx.fillStyle = style.fill;
            ctx.fill();
            ctx.strokeStyle = style.stroke;
            ctx.lineWidth = style.width / Math.max(scale, 0.1);
            ctx.setLineDash(style.dash);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.font = '800 ' + fontSize + 'px Arial, sans-serif';
            ctx.fillStyle = '#14315E';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'alphabetic';
            ctx.fillText(String(box.name || ''), box.left + 10, box.top + 16);
            ctx.restore();
        }

        function rememberZoomView(visNetwork) {
            if (!visNetwork || typeof visNetwork.getScale !== 'function' || typeof visNetwork.getViewPosition !== 'function') return;
            const scale = visNetwork.getScale();
            if (!Number.isFinite(scale) || scale < MIN_ZOOM_LEVEL || scale > MAX_ZOOM_LEVEL) return;
            const position = visNetwork.getViewPosition();
            if (!position || !Number.isFinite(position.x) || !Number.isFinite(position.y)) return;
            lastZoomSafeView = {
                scale: scale,
                position: { x: position.x, y: position.y }
            };
        }

        function clampZoom(visNetwork) {
            if (!visNetwork || typeof visNetwork.getScale !== 'function' || typeof visNetwork.moveTo !== 'function') return;
            if (isClampingZoom) return;
            const scale = visNetwork.getScale();
            if (!Number.isFinite(scale)) return;
            if (scale >= MIN_ZOOM_LEVEL && scale <= MAX_ZOOM_LEVEL) {
                rememberZoomView(visNetwork);
                return;
            }
            isClampingZoom = true;
            const targetScale = Math.min(Math.max(scale, MIN_ZOOM_LEVEL), MAX_ZOOM_LEVEL);
            const currentPosition = typeof visNetwork.getViewPosition === 'function' ? visNetwork.getViewPosition() : undefined;
            const position = lastZoomSafeView && lastZoomSafeView.position ? lastZoomSafeView.position : currentPosition;
            visNetwork.moveTo({
                position: position,
                scale: targetScale,
                animation: false
            });
            lastZoomSafeView = {
                scale: targetScale,
                position: position
            };
            window.setTimeout(function() {
                isClampingZoom = false;
            }, 0);
        }

        function normalizeWheelDelta(event) {
            let delta = Number(event.deltaY) || 0;
            if (event.deltaMode === 1) delta *= 16;
            if (event.deltaMode === 2) delta *= 600;
            return Math.max(-MAX_WHEEL_ZOOM_DELTA, Math.min(MAX_WHEEL_ZOOM_DELTA, delta));
        }

        function relativePointer(event, element) {
            const rect = element.getBoundingClientRect();
            return {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top,
                width: rect.width,
                height: rect.height
            };
        }

        function zoomPositionForPointer(visNetwork, pointer, targetScale) {
            if (!visNetwork || typeof visNetwork.DOMtoCanvas !== 'function') return undefined;
            const canvasPoint = visNetwork.DOMtoCanvas({ x: pointer.x, y: pointer.y });
            if (!canvasPoint || !Number.isFinite(canvasPoint.x) || !Number.isFinite(canvasPoint.y)) return undefined;
            return {
                x: canvasPoint.x - ((pointer.x - (pointer.width / 2)) / targetScale),
                y: canvasPoint.y - ((pointer.y - (pointer.height / 2)) / targetScale)
            };
        }

        function applyWheelZoom(visNetwork, networkDiv, event) {
            if (!visNetwork || typeof visNetwork.getScale !== 'function' || typeof visNetwork.moveTo !== 'function') return;
            const currentScale = visNetwork.getScale();
            if (!Number.isFinite(currentScale)) return;
            const delta = normalizeWheelDelta(event);
            if (delta === 0) return;
            event.preventDefault();
            event.stopImmediatePropagation();

            const atMinZoom = currentScale <= MIN_ZOOM_LEVEL + 0.0001;
            const atMaxZoom = currentScale >= MAX_ZOOM_LEVEL - 0.0001;
            if ((atMinZoom && delta > 0) || (atMaxZoom && delta < 0)) {
                rememberZoomView(visNetwork);
                return;
            }

            const isLikelyTrackpad = event.ctrlKey || Math.abs(Number(event.deltaY) || 0) < 50;
            const sensitivity = isLikelyTrackpad ? TRACKPAD_ZOOM_SENSITIVITY : WHEEL_ZOOM_SENSITIVITY;
            const requestedScale = currentScale * Math.exp(-delta * sensitivity);
            const targetScale = Math.min(Math.max(requestedScale, MIN_ZOOM_LEVEL), MAX_ZOOM_LEVEL);
            if (!Number.isFinite(targetScale) || Math.abs(targetScale - currentScale) < 0.0001) {
                rememberZoomView(visNetwork);
                return;
            }

            const canvas = networkDiv.querySelector('canvas');
            const pointerElement = canvas || networkDiv;
            const pointer = relativePointer(event, pointerElement);
            const position = zoomPositionForPointer(visNetwork, pointer, targetScale)
                || (typeof visNetwork.getViewPosition === 'function' ? visNetwork.getViewPosition() : undefined);
            isClampingZoom = true;
            visNetwork.moveTo({
                position: position,
                scale: targetScale,
                animation: false
            });
            lastZoomSafeView = {
                scale: targetScale,
                position: position
            };
            window.setTimeout(function() {
                isClampingZoom = false;
                scheduleRedraw();
            }, 0);
        }

        function installWheelZoomControl(visNetwork, networkDiv) {
            if (wheelZoomInstalled || !networkDiv || !networkDiv.addEventListener) return;
            wheelZoomInstalled = true;
            networkDiv.addEventListener('wheel', function(event) {
                if (event.target && event.target.closest && event.target.closest('.org-crud-toolbar, .collab-modal-backdrop')) return;
                applyWheelZoom(visNetwork, networkDiv, event);
            }, { capture: true, passive: false });
        }

        function drawContainers(ctx, data, visNetwork) {
            if (!ctx || !data || !visNetwork) return;
            ['supersetor', 'setor', 'subsetor'].forEach(type => {
                Object.keys(data[type] || {}).forEach(name => {
                    const box = buildContainerBox(type, name, data[type][name], visNetwork);
                    if (box) drawContainerBox(ctx, box, visNetwork);
                });
            });
        }

        function emptyChanges() {
            return { upserts: {}, deletes: [] };
        }

        function loadChanges() {
            return emptyChanges();
        }

        function saveChanges(changes) {
            try {
                localStorage.removeItem(STORAGE_KEY);
            } catch (err) {
                console.log('Could not clear local graph changes:', err);
            }
        }

        function syncParentWithChanges(changes) {
            if (!crudEnabled || !window.parent || window.parent === window) return;
            try {
                window.parent.postMessage({
                    type: 'org_chart_event',
                    payload: {
                        nonce: Date.now().toString() + '_' + Math.random().toString(16).slice(2),
                        changes: changes || emptyChanges()
                    }
                }, '*');
            } catch (err) {
                console.log('Could not send graph changes to Streamlit component:', err);
            }
        }

        function hasMeaningfulChanges(changes) {
            return Boolean(
                changes
                && (
                    Object.keys(changes.upserts || {}).length > 0
                    || (Array.isArray(changes.deletes) && changes.deletes.length > 0)
                )
            );
        }

        function syncStoredChangesToParent() {
            try {
                localStorage.removeItem(STORAGE_KEY);
            } catch (err) {
                console.log('Could not clear old local graph changes:', err);
            }
        }

        function sortedUnique(values) {
            return Array.from(new Set((values || []).map(value => String(value || '').trim()).filter(Boolean)))
                .sort((a, b) => a.localeCompare(b, 'pt-BR'));
        }

        function splitCargoNivel(cargo) {
            const text = String(cargo || '').trim();
            const niveis = editorData.niveis || ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'];
            const lastSpace = text.lastIndexOf(' ');
            if (lastSpace < 0) return { cargo: text, nivel: '' };
            const cargoBase = text.slice(0, lastSpace).trim();
            const nivel = text.slice(lastSpace + 1).trim();
            if (niveis.includes(nivel)) return { cargo: cargoBase, nivel: nivel };
            return { cargo: text, nivel: '' };
        }

        function joinCargoNivel(cargo, nivel) {
            const cargoBase = String(cargo || '').trim();
            const nivelText = String(nivel || '').trim();
            return [cargoBase, nivelText].filter(Boolean).join(' ');
        }

        function allRealNodes() {
            return realGraphNodes().sort((a, b) => {
                const an = ((a.collaborator && a.collaborator.nome) || String(a.id)).toString();
                const bn = ((b.collaborator && b.collaborator.nome) || String(b.id)).toString();
                return an.localeCompare(bn, 'pt-BR');
            });
        }

        function optionHtml(values, selected) {
            const selectedText = String(selected || '');
            const opts = ['<option value=""></option>'];
            sortedUnique([selectedText].concat(values || [])).forEach(value => {
                const safe = escapeHtml(value);
                const isSelected = value === selectedText ? ' selected' : '';
                opts.push('<option value="' + safe + '"' + isSelected + '>' + safe + '</option>');
            });
            return opts.join('');
        }

        function leaderOptionHtml(selectedMat) {
            const selectedText = String(selectedMat || '');
            const opts = ['<option value=""></option>'];
            allRealNodes().forEach(node => {
                const collaborator = node.collaborator || {};
                const mat = String(collaborator.mat || node.id || '');
                const nome = String(collaborator.nome || mat);
                const label = nome + ' (MAT: ' + mat + ')';
                const isSelected = mat === selectedText ? ' selected' : '';
                opts.push('<option value="' + escapeHtml(mat) + '"' + isSelected + '>' + escapeHtml(label) + '</option>');
            });
            return opts.join('');
        }

        function subsetorOptionsForSetor(setor, selected) {
            const mapping = editorData.subsetoresPorSetor || {};
            return optionHtml(mapping[setor] || [], selected);
        }

        function supersetorForSetor(setor) {
            const mapping = editorData.supersetorPorSetor || {};
            return mapping[setor] || '';
        }

        function leaderForOrg(setor, subsetor, excludedMat) {
            const excluded = String(excludedMat || '').trim();
            const subsetorKey = String(setor || '') + '||' + String(subsetor || '');
            const subsetorLeader = (editorData.lideresSubsetor || {})[subsetorKey];
            if (subsetorLeader && subsetorLeader.mat && String(subsetorLeader.mat) !== excluded) return subsetorLeader;
            const sectorLeader = (editorData.lideresSetor || {})[setor || ''];
            if (sectorLeader && sectorLeader.mat && String(sectorLeader.mat) !== excluded) return sectorLeader;
            return { mat: '', nome: '' };
        }

        function autoPositionForCargoNivel(cargo, nivel) {
            const cargoCompleto = joinCargoNivel(cargo, nivel);
            const mapping = editorData.posicaoPorCargo || {};
            return mapping[cargoCompleto] || '';
        }

        function escapeHtml(value) {
            return String(value || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function shortText(value, limit) {
            const text = String(value || '').trim();
            if (text.length <= limit) return text;
            return text.slice(0, Math.max(0, limit - 3)).trimEnd() + '...';
        }

        function baseLabel(details) {
            return shortText(details.nome || 'Sem nome', 24) + '\\n' + shortText(details.cargo || 'Sem cargo', 26);
        }

        function displayLabel(details) {
            const span = Number(details.span || 0);
            const label = baseLabel(details);
            return span > 0 ? label + '\\nSpan: ' + span : label;
        }

        function clearLocalSearchHighlight() {
            const ds = getNodesDataset();
            if (!ds) return;
            realGraphNodes().forEach(node => {
                if (node._searchHighlighted) {
                    ds.update({
                        id: node.id,
                        _searchHighlighted: false,
                        borderWidth: node._previousBorderWidth || 1,
                        color: node._previousColor || node.color,
                        size: node._previousSize || node.size
                    });
                }
            });
        }

        function searchUiElements() {
            const toolbar = document.querySelector('.org-crud-toolbar');
            return {
                toolbar: toolbar,
                input: toolbar ? toolbar.querySelector('[data-action="search"]') : null,
                navigation: toolbar ? toolbar.querySelector('[data-role="search-nav"]') : null,
                previous: toolbar ? toolbar.querySelector('[data-action="search-prev"]') : null,
                next: toolbar ? toolbar.querySelector('[data-action="search-next"]') : null,
                count: toolbar ? toolbar.querySelector('[data-role="search-count"]') : null
            };
        }

        function updateSearchNavigationUi() {
            const ui = searchUiElements();
            const count = localSearchState.matches.length;
            const hasQuery = Boolean(localSearchState.query);
            const canNavigate = count > 1;
            if (ui.navigation) ui.navigation.classList.toggle('is-visible', canNavigate);
            if (ui.previous) ui.previous.disabled = !canNavigate;
            if (ui.next) ui.next.disabled = !canNavigate;
            if (ui.count) {
                ui.count.textContent = hasQuery ? (count ? ((localSearchState.currentIndex + 1) + '/' + count) : '0/0') : '';
            }
        }

        function nodeMatchesSearch(node, query) {
            const details = node.collaborator || {};
            return [details.nome, details.cargo, details.mat, details.setor, details.subsetor]
                .map(value => String(value || '').toLowerCase())
                .some(value => value.includes(query));
        }

        function localSearchMatches(query) {
            if (!query) return [];
            return allRealNodes().filter(node => nodeMatchesSearch(node, query));
        }

        function focusSearchMatch(visNetwork, match) {
            if (!match || !visNetwork || typeof visNetwork.moveTo !== 'function') return;
            const ds = getNodesDataset();
            const current = ds ? ds.get(match.id) : match;
            visNetwork.moveTo({
                position: { x: Number(current && current.x) || Number(match.x) || 0, y: Number(current && current.y) || Number(match.y) || 0 },
                scale: Math.max(0.6, Math.min(1.15, visNetwork.getScale ? visNetwork.getScale() : 0.8)),
                animation: { duration: 550, easingFunction: 'easeInOutQuad' }
            });
        }

        function applyLocalSearchHighlight(activeId) {
            const ds = getNodesDataset();
            if (!ds) return;
            localSearchState.matches.forEach(match => {
                const node = ds.get(match.id) || match;
                const isActive = String(match.id) === String(activeId);
                ds.update({
                    id: match.id,
                    _searchHighlighted: true,
                    _previousColor: node._searchHighlighted ? node._previousColor : node.color,
                    _previousBorderWidth: node._searchHighlighted ? node._previousBorderWidth : node.borderWidth,
                    _previousSize: node._searchHighlighted ? node._previousSize : node.size,
                    color: { background: isActive ? '#2FD68B' : '#C7F7DF', border: '#14315E' },
                    borderWidth: isActive ? 5 : 4,
                    size: Math.max(Number(node._previousSize || node.size) || 22, isActive ? 36 : 32)
                });
            });
        }

        function focusLocalSearch(visNetwork, text, index) {
            const query = String(text || '').trim().toLowerCase();
            clearLocalSearchHighlight();
            localSearchState = { query: query, matches: [], currentIndex: 0 };
            if (!query) {
                updateSearchNavigationUi();
                scheduleRedraw();
                return;
            }
            const matches = localSearchMatches(query);
            if (!matches.length) {
                updateSearchNavigationUi();
                scheduleRedraw();
                return;
            }
            let currentIndex = Number.isInteger(index) ? index : 0;
            currentIndex = ((currentIndex % matches.length) + matches.length) % matches.length;
            localSearchState = { query: query, matches: matches, currentIndex: currentIndex };
            const activeMatch = matches[currentIndex];
            applyLocalSearchHighlight(activeMatch.id);
            focusSearchMatch(visNetwork, activeMatch);
            updateSearchNavigationUi();
            scheduleRedraw();
        }

        function navigateLocalSearch(visNetwork, delta) {
            const ui = searchUiElements();
            const text = ui.input ? ui.input.value : localSearchState.query;
            const query = String(text || '').trim().toLowerCase();
            if (!query) {
                focusLocalSearch(visNetwork, '');
                return;
            }
            const nextIndex = localSearchState.query === query
                ? localSearchState.currentIndex + delta
                : 0;
            focusLocalSearch(visNetwork, text, nextIndex);
        }

        function cleanupBendNodesAround(nodeId, visNetwork) {
            const ds = getNodesDataset();
            if (!ds || !visNetwork || typeof visNetwork.getConnectedNodes !== 'function') return;
            const toRemove = new Set();
            const stack = (visNetwork.getConnectedNodes(nodeId) || []).map(String);
            while (stack.length) {
                const current = stack.pop();
                if (!current.startsWith('__bend_') || toRemove.has(current)) continue;
                toRemove.add(current);
                (visNetwork.getConnectedNodes(current) || []).map(String).forEach(next => {
                    if (next.startsWith('__bend_') && !toRemove.has(next)) stack.push(next);
                });
            }
            if (toRemove.size) ds.remove(Array.from(toRemove));
        }

        function edgeDataset() {
            if (typeof edges !== 'undefined' && edges) return edges;
            return window.edges || null;
        }

        function upsertVisualNode(details, options) {
            if (options && options.persist) {
                const nodeId = String(details && details.mat ? details.mat : '');
                if (!nodeId) return;
                const changes = emptyChanges();
                changes.upserts[nodeId] = details;
                syncParentWithChanges(changes);
                return;
            }
            const ds = getNodesDataset();
            if (!ds || !details || !details.mat) return;
            const nodeId = String(details.mat);
            const existing = ds.get(nodeId);
            const collaborator = Object.assign({}, existing && existing.collaborator ? existing.collaborator : {}, details);
            collaborator.baseLabel = baseLabel(collaborator);
            const payload = {
                id: nodeId,
                label: displayLabel(collaborator),
                title: 'Clique para ver detalhes',
                collaborator: collaborator
            };
            if (existing) {
                ds.update(payload);
            } else {
                const leaderNode = details.liderMat ? ds.get(String(details.liderMat)) : null;
                const x = leaderNode && Number.isFinite(Number(leaderNode.x)) ? Number(leaderNode.x) + 180 : 0;
                const y = leaderNode && Number.isFinite(Number(leaderNode.y)) ? Number(leaderNode.y) + 180 : 0;
                ds.add(Object.assign(payload, {
                    x: x,
                    y: y,
                    fixed: { x: false, y: false },
                    physics: false,
                    size: 22,
                    color: { background: '#b8cbe6', border: '#7f9fc4' },
                    borderWidth: 1
                }));
            }

            const edgeDs = edgeDataset();
            if (edgeDs && details.liderMat && String(details.liderMat) !== nodeId) {
                const edgeId = 'crud_edge_' + String(details.liderMat) + '_' + nodeId;
                if (!edgeDs.get(edgeId)) {
                    edgeDs.add({
                        id: edgeId,
                        from: String(details.liderMat),
                        to: nodeId,
                        arrows: 'to',
                        color: '#7f95b5',
                        width: 2
                    });
                }
            }
            scheduleRedraw();
        }

        function deleteVisualNode(nodeId, visNetwork, persist) {
            if (persist) {
                const changes = emptyChanges();
                if (nodeId) changes.deletes.push(String(nodeId));
                syncParentWithChanges(changes);
                return;
            }
            const ds = getNodesDataset();
            if (!ds || !nodeId || !ds.get(String(nodeId))) return;
            cleanupBendNodesAround(String(nodeId), visNetwork);
            ds.remove(String(nodeId));
            scheduleRedraw();
        }

        function applyStoredChanges(visNetwork) {
            const changes = loadChanges();
            (changes.deletes || []).forEach(nodeId => deleteVisualNode(String(nodeId), visNetwork, false));
            Object.keys(changes.upserts || {}).forEach(nodeId => {
                const details = changes.upserts[nodeId];
                if (details && !changes.deletes.map(String).includes(String(nodeId))) {
                    upsertVisualNode(details, { persist: false });
                }
            });
        }

        function modalMarkup() {
            return `
                <div class="collab-modal" role="dialog" aria-modal="true">
                    <div class="collab-modal-header">
                        <p class="collab-modal-title" data-role="modal-title">Detalhes do colaborador</p>
                        <button type="button" class="collab-button icon" data-action="cancel" aria-label="Fechar">x</button>
                    </div>
                    <div class="collab-modal-body">
                        <div class="collab-field"><label>MAT</label><input data-field="mat"></div>
                        <div class="collab-field"><label>Nome</label><input data-field="nome"></div>
                        <div class="collab-field"><label>Líder</label><select data-field="liderMat"></select></div>
                        <div class="collab-field"><label>Cargo</label><select data-field="cargo"></select></div>
                        <div class="collab-field"><label>Nível</label><select data-field="nivel"></select></div>
                        <div class="collab-field"><label>Posição</label><select data-field="posicao"></select></div>
                        <div class="collab-field"><label>SuperSetor</label><input data-field="supersetor" readonly></div>
                        <div class="collab-field"><label>Setor</label><select data-field="setor"></select></div>
                        <div class="collab-field"><label>Subsetor</label><select data-field="subsetor"></select></div>
                        <div class="collab-field full"><label>Observações</label><textarea data-field="observacoes"></textarea></div>
                        <div class="collab-modal-message" data-role="message"></div>
                    </div>
                    <div class="collab-modal-footer">
                        <button type="button" class="collab-button danger" data-action="delete">Deletar</button>
                        <button type="button" class="collab-button" data-action="cancel">Cancelar</button>
                        <button type="button" class="collab-button primary" data-action="save">Salvar</button>
                    </div>
                </div>
            `;
        }

        function ensureCrudUi(networkDiv, visNetwork) {
            if (modalInstalled) return true;
            if (!visNetwork || typeof visNetwork.on !== 'function') return false;
            modalInstalled = true;

            const toolbar = document.createElement('div');
            toolbar.className = 'org-crud-toolbar';
            toolbar.innerHTML = '<div class="org-chart-search-group"><div class="org-search-nav" data-role="search-nav"><button type="button" class="org-search-nav-button" data-action="search-prev" title="Resultado anterior" aria-label="Resultado anterior" disabled>&lsaquo;</button><span class="org-search-count" data-role="search-count" aria-live="polite"></span><button type="button" class="org-search-nav-button" data-action="search-next" title="Próximo resultado" aria-label="Próximo resultado" disabled>&rsaquo;</button></div><input type="search" class="org-chart-search" data-action="search" placeholder="Buscar no gráfico"></div><button type="button" class="org-crud-button" data-action="create">+ Novo nó</button>';
            networkDiv.appendChild(toolbar);

            const backdrop = document.createElement('div');
            backdrop.id = 'collab-modal-backdrop';
            backdrop.className = 'collab-modal-backdrop';
            backdrop.innerHTML = modalMarkup();
            networkDiv.appendChild(backdrop);

            let currentMode = 'edit';
            let currentNodeId = '';

            function field(name) {
                return backdrop.querySelector('[data-field="' + name + '"]');
            }

            function setMessage(text) {
                const el = backdrop.querySelector('[data-role="message"]');
                if (el) el.textContent = text || '';
            }

            function setInput(name, value) {
                const el = field(name);
                if (el) el.value = value == null ? '' : String(value);
            }

            function getInput(name) {
                const el = field(name);
                return el ? String(el.value || '').trim() : '';
            }

            function setReadOnlyForMode(mode) {
                const isCreate = mode === 'create';
                if (field('mat')) field('mat').readOnly = !isCreate;
                if (field('nome')) field('nome').readOnly = !isCreate;
                if (field('liderMat')) field('liderMat').disabled = !isCreate;
                const del = backdrop.querySelector('[data-action="delete"]');
                if (del) del.style.display = isCreate ? 'none' : '';
            }

            function refreshSubsetores() {
                const setor = getInput('setor');
                const subsetor = getInput('subsetor');
                if (field('subsetor')) field('subsetor').innerHTML = subsetorOptionsForSetor(setor, subsetor);
                setInput('supersetor', supersetorForSetor(setor));
                const leader = leaderForOrg(setor, getInput('subsetor'), getInput('mat'));
                if (leader.mat) setInput('liderMat', leader.mat);
            }

            function refreshPosicaoFromCargoNivel() {
                setInput('posicao', autoPositionForCargoNivel(getInput('cargo'), getInput('nivel')));
            }

            function installOptions(details) {
                const value = details || {};
                const cargoParts = splitCargoNivel(value.cargo || '');
                const selectedCargo = value.cargoBase || cargoParts.cargo;
                const selectedNivel = value.nivel || cargoParts.nivel;
                if (field('cargo')) field('cargo').innerHTML = optionHtml(editorData.cargosBase || editorData.cargos || [], selectedCargo);
                if (field('nivel')) field('nivel').innerHTML = optionHtml(editorData.niveis || [], selectedNivel);
                if (field('setor')) field('setor').innerHTML = optionHtml(editorData.setores || [], value.setor || '');
                if (field('subsetor')) field('subsetor').innerHTML = subsetorOptionsForSetor(value.setor || '', value.subsetor || '');
                if (field('posicao')) field('posicao').innerHTML = optionHtml(editorData.posicoes || [], value.posicao || '');
                if (field('liderMat')) field('liderMat').innerHTML = leaderOptionHtml(value.liderMat || '');
            }

            function openModal(mode, details) {
                currentMode = mode;
                currentNodeId = details && details.mat ? String(details.mat) : '';
                const value = Object.assign({
                    mat: '',
                    nome: '',
                    cargo: '',
                    nivel: '',
                    setor: '',
                    subsetor: '',
                    supersetor: '',
                    liderMat: '',
                    posicao: '',
                    observacoes: '',
                    span: 0
                }, details || {});
                const cargoParts = splitCargoNivel(value.cargo || '');
                const cargoBase = value.cargoBase || cargoParts.cargo;
                const nivel = value.nivel || cargoParts.nivel;

                const title = backdrop.querySelector('[data-role="modal-title"]');
                if (title) title.textContent = mode === 'create' ? 'Criar novo nó' : 'Detalhes do colaborador';
                installOptions(value);
                setReadOnlyForMode(mode);
                setInput('mat', value.mat);
                setInput('nome', value.nome);
                setInput('cargo', cargoBase);
                setInput('nivel', nivel);
                setInput('setor', value.setor);
                setInput('subsetor', value.subsetor);
                setInput('supersetor', value.supersetor || supersetorForSetor(value.setor));
                setInput('liderMat', value.liderMat);
                setInput('posicao', value.posicao);
                setInput('observacoes', value.observacoes);
                setInput('span', value.span || 0);
                setMessage('');
                backdrop.classList.add('is-open');
            }

            function closeModal() {
                backdrop.classList.remove('is-open');
                currentMode = 'edit';
                currentNodeId = '';
                setMessage('');
            }

            function collectDetails() {
                const mat = getInput('mat');
                const setor = getInput('setor');
                const subsetor = getInput('subsetor');
                const cargoBase = getInput('cargo');
                const nivel = getInput('nivel');
                const leader = leaderForOrg(setor, subsetor, mat);
                const existingNode = currentNodeId && getNodesDataset() ? getNodesDataset().get(currentNodeId) : null;
                const existing = existingNode && existingNode.collaborator ? existingNode.collaborator : {};
                const leaderMat = leader.mat || getInput('liderMat') || existing.liderMat || '';
                return Object.assign({}, existing, {
                    mat: mat,
                    nome: getInput('nome'),
                    cargo: joinCargoNivel(cargoBase, nivel),
                    cargoBase: cargoBase,
                    nivel: nivel,
                    setor: setor,
                    subsetor: subsetor,
                    supersetor: getInput('supersetor') || supersetorForSetor(setor),
                    liderMat: leaderMat,
                    lider: leader.nome || (leaderMat === existing.liderMat ? existing.lider : ''),
                    posicao: getInput('posicao'),
                    observacoes: getInput('observacoes'),
                    span: Number(existing.span || 0)
                });
            }

            function validateDetails(details) {
                if (!details.mat) return 'Informe a matrícula.';
                if (!details.nome) return 'Informe o nome.';
                if (currentMode === 'create' && getNodesDataset() && getNodesDataset().get(String(details.mat))) {
                    return 'Já existe um nó com essa matrícula.';
                }
                if (currentMode === 'create' && details.liderMat && String(details.liderMat) === String(details.mat)) {
                    return 'O líder não pode ser o próprio colaborador.';
                }
                return '';
            }

            function saveModal() {
                const details = collectDetails();
                const error = validateDetails(details);
                if (error) {
                    setMessage(error);
                    return;
                }
                upsertVisualNode(details, { persist: true });
                closeModal();
            }

            function deleteModal() {
                if (!currentNodeId) return;
                deleteVisualNode(currentNodeId, visNetwork, true);
                closeModal();
            }

            toolbar.addEventListener('click', function(event) {
                const action = event.target && event.target.dataset ? event.target.dataset.action : '';
                if (action === 'create') {
                    const firstLeader = allRealNodes()[0];
                    const leaderMat = firstLeader && firstLeader.collaborator ? firstLeader.collaborator.mat : '';
                    openModal('create', { liderMat: leaderMat, span: 0 });
                }
                if (action === 'search-prev') {
                    navigateLocalSearch(visNetwork, -1);
                }
                if (action === 'search-next') {
                    navigateLocalSearch(visNetwork, 1);
                }
            });
            const searchInput = toolbar.querySelector('[data-action="search"]');
            if (searchInput) {
                searchInput.addEventListener('keydown', function(event) {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        navigateLocalSearch(visNetwork, event.shiftKey ? -1 : 1);
                    }
                });
                searchInput.addEventListener('input', function() {
                    window.clearTimeout(searchInput._searchTimer);
                    searchInput._searchTimer = window.setTimeout(function() {
                        focusLocalSearch(visNetwork, searchInput.value);
                    }, 220);
                });
            }

            backdrop.addEventListener('click', function(event) {
                if (event.target === backdrop) closeModal();
                const action = event.target && event.target.dataset ? event.target.dataset.action : '';
                if (action === 'cancel') closeModal();
                if (action === 'save') saveModal();
                if (action === 'delete') deleteModal();
            });

            ['setor', 'subsetor'].forEach(name => {
                const el = field(name);
                if (el) el.addEventListener('change', refreshSubsetores);
            });
            ['cargo', 'nivel'].forEach(name => {
                const el = field(name);
                if (el) el.addEventListener('change', refreshPosicaoFromCargoNivel);
            });

            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape' && backdrop.classList.contains('is-open')) closeModal();
            });

            visNetwork.on('click', function(params) {
                const nodeId = params.nodes && params.nodes[0] ? String(params.nodes[0]) : '';
                if (!nodeId || nodeId.startsWith('__bend_')) return;
                const ds = getNodesDataset();
                const node = ds && ds.get(nodeId);
                if (!node || !node.collaborator) return;
                openModal('edit', node.collaborator);
            });

            return true;
        }

        function bindNetworkEvents(visNetwork) {
            if (eventsBound || !visNetwork || typeof visNetwork.on !== 'function') return;
            eventsBound = true;
            visNetwork.on('beforeDrawing', function(ctx) {
                drawContainers(ctx, currentContainers(), visNetwork);
            });
            ['zoom', 'dragEnd', 'animationFinished', 'stabilized', 'resize'].forEach(function(eventName) {
                visNetwork.on(eventName, function() {
                    if (eventName === 'zoom') clampZoom(visNetwork);
                    scheduleRedraw();
                });
            });
            window.addEventListener('resize', scheduleRedraw);
        }

        function applyInitialView(visNetwork) {
            if (initialViewApplied || !Number.isFinite(initialScale) || initialScale <= 0) return;
            initialViewApplied = true;
            window.setTimeout(function() {
                if (visNetwork && typeof visNetwork.fit === 'function') {
                    visNetwork.fit({
                        animation: false,
                        minZoomLevel: MIN_ZOOM_LEVEL,
                        maxZoomLevel: MAX_ZOOM_LEVEL
                    });
                }
                clampZoom(visNetwork);
                scheduleRedraw();
            }, 80);
        }

        function setupContainers() {
            const visNetwork = getVisNetwork();
            const networkDiv = document.getElementById('mynetwork');
            if (!visNetwork || !networkDiv) return false;
            networkDiv.style.position = 'relative';
            installWheelZoomControl(visNetwork, networkDiv);
            bindNetworkEvents(visNetwork);
            if (crudEnabled) {
                if (!ensureCrudUi(networkDiv, visNetwork)) return false;
                syncStoredChangesToParent();
            }
            applyInitialView(visNetwork);
            if (typeof visNetwork.redraw === 'function') visNetwork.redraw();
            return true;
        }

        const waitForNetwork = window.setInterval(function() {
            if (setupContainers()) {
                window.clearInterval(waitForNetwork);
            }
        }, 100);

        window.setTimeout(function() {
            window.clearInterval(waitForNetwork);
            setupContainers();
        }, 10000);
    })();
    </script>
    """
    
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", f"{container_styles}</body>")
    else:
        html_content = html_content.replace("</head>", f"{container_styles}</head>")
    
    if enable_crud:
        return ORG_CHART_COMPONENT(
            html=html_content,
            height=height,
            default=None,
            key=f"org_chart_component_{height}",
        )
    st.components.v1.html(html_content, height=height, scrolling=True)
    return None


def request_sidebar_open() -> None:
    st.components.v1.html(
        """
        <script>
        (function() {
            function isSidebarOpen(doc) {
                const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                return sidebar && sidebar.getBoundingClientRect().width > 160;
            }

            function clickOpenControl() {
                const doc = window.parent.document;
                if (isSidebarOpen(doc)) return true;

                const selectors = [
                    '[data-testid="collapsedControl"] button',
                    '[data-testid="stSidebarCollapsedControl"] button',
                    'button[aria-label="Open sidebar"]',
                    'button[aria-label="Expand sidebar"]',
                    'button[title="Open sidebar"]',
                    'button[title="Expand sidebar"]'
                ];
                for (const selector of selectors) {
                    const button = doc.querySelector(selector);
                    if (button) {
                        button.click();
                        return true;
                    }
                }
                return false;
            }

            let attempts = 0;
            const timer = window.setInterval(function() {
                attempts += 1;
                if (clickOpenControl() || attempts >= 25) {
                    window.clearInterval(timer);
                }
            }, 120);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def render_brand_header() -> None:
    logo_path = ICON_PATH
    logo_html = ""
    if logo_path.exists():
        logo_bytes = logo_path.read_bytes()
        logo_html = (
            '<img class="brand-logo" '
            f'src="data:image/png;base64,{base64.b64encode(logo_bytes).decode()}" '
            'alt="Logo" />'
        )

    st.markdown(
        f"""
        <div class="brand-header">
                <div class="brand-header-logo">{logo_html}</div>
                <h1 class="brand-title">Organograma da Empresa</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_collaborator_editor(
    df: pd.DataFrame,
    setores_df: pd.DataFrame,
    supersetores_df: pd.DataFrame,
    subsetores_df: pd.DataFrame,
) -> None:
    cargo_options = sorted(
        {split_cargo_nivel_value(str(value))[0] for value in df["CARGO"].tolist() if split_cargo_nivel_value(str(value))[0]},
        key=str.casefold,
    )
    cargo_position_map = cargo_position_map_from_df(df)
    posicao_options = sorted({str(value).strip() for value in df["POSICAO"].tolist() if str(value).strip()}, key=str.casefold)
    setor_options = sorted(
        (
            {str(value).strip() for value in df.get("SETOR", pd.Series(dtype=str)).tolist() if str(value).strip()}
            | ({str(value).strip() for value in setores_df["SETOR"].tolist() if str(value).strip()} if not setores_df.empty else set())
        ),
        key=str.casefold,
    )
    setor_to_supersetor = setor_supersetor_map(supersetores_df)
    subsetor_map = subsetores_by_setor(subsetores_df, df)
    valid_subsetor_leaders, valid_sector_leaders = build_org_leader_lookup(df, setores_df, subsetores_df)

    def current_org_leader_mat_for(setor: str, subsetor: str, excluded_mat: str = "") -> str:
        return org_leader_mat_for(setor, subsetor, excluded_mat, valid_subsetor_leaders, valid_sector_leaders)

    leader_options = [""] + [
        f"{str(row.get('NOME', '')).strip()} (MAT: {str(row.get('MAT', '')).strip()})"
        for _, row in df.sort_values(["NOME", "MAT"]).iterrows()
        if str(row.get("MAT", "")).strip()
    ]
    leader_by_label = {"": ""}
    for label in leader_options[1:]:
        leader_by_label[label] = label.rsplit("(MAT: ", 1)[-1].rstrip(")")

    def leader_label_for(mat: str) -> str:
        mat = str(mat or "").strip()
        if not mat:
            return ""
        person = df[df["MAT"].astype(str) == mat]
        if person.empty:
            return ""
        return f"{str(person.iloc[0].get('NOME', '')).strip()} (MAT: {mat})"

    def option_index(options: list[str], value: str) -> int:
        value = str(value or "").strip()
        return options.index(value) if value in options else 0

    @st.dialog("Detalhes do colaborador")
    def collaborator_dialog() -> None:
        mode = st.session_state.get("collab_dialog_mode", "create")
        mat = str(st.session_state.get("collab_dialog_mat", "")).strip()
        existing = {}
        if mode == "edit" and mat:
            matches = df[df["MAT"].astype(str) == mat]
            if not matches.empty:
                existing = matches.iloc[0].to_dict()

        cargo_base, nivel = split_cargo_nivel_value(str(existing.get("CARGO", "")))
        selected_setor_key = f"collab_setor_{mode}_{mat or 'new'}"
        current_setor = str(st.session_state.get(selected_setor_key, existing.get("SETOR", ""))).strip()
        subsetor_options = [""] + subsetor_map.get(current_setor, [])
        current_supersetor = setor_to_supersetor.get(current_setor, str(existing.get("SUPERSETOR", "")).strip())

        col1, col2, col3 = st.columns(3)
        with col1:
            input_mat = st.text_input("MAT", value=str(existing.get("MAT", "")), disabled=(mode == "edit"), key=f"collab_mat_{mode}_{mat or 'new'}")
        with col2:
            input_nome = st.text_input("Nome", value=str(existing.get("NOME", "")), key=f"collab_nome_{mode}_{mat or 'new'}")
        with col3:
            current_leader_label = leader_label_for(str(existing.get("LIDER", "")))
            input_lider_label = st.selectbox(
                "Lider",
                options=leader_options,
                index=option_index(leader_options, current_leader_label),
                key=f"collab_lider_{mode}_{mat or 'new'}",
            )

        col4, col5, col6 = st.columns(3)
        cargo_key = f"collab_cargo_{mode}_{mat or 'new'}"
        nivel_key = f"collab_nivel_{mode}_{mat or 'new'}"
        posicao_key = f"collab_posicao_{mode}_{mat or 'new'}"
        cargo_combo_state_key = f"collab_cargo_combo_{mode}_{mat or 'new'}"
        with col4:
            input_cargo_base = st.selectbox(
                "Cargo",
                options=[""] + cargo_options,
                index=option_index([""] + cargo_options, cargo_base),
                key=cargo_key,
            )
        with col5:
            input_nivel = st.selectbox(
                "Nivel",
                options=[""] + NIVEL_OPTIONS,
                index=option_index([""] + NIVEL_OPTIONS, nivel),
                key=nivel_key,
            )

        cargo_combo = join_cargo_nivel(input_cargo_base, input_nivel)
        if cargo_combo_state_key not in st.session_state:
            st.session_state[cargo_combo_state_key] = cargo_combo
        elif st.session_state.get(cargo_combo_state_key) != cargo_combo:
            st.session_state[cargo_combo_state_key] = cargo_combo
            st.session_state[posicao_key] = cargo_position_map.get(cargo_combo, "")

        with col6:
            input_posicao = st.selectbox(
                "Posicao",
                options=[""] + posicao_options,
                index=option_index([""] + posicao_options, str(existing.get("POSICAO", ""))),
                key=posicao_key,
            )

        col7, col8, col9 = st.columns(3)
        with col7:
            st.text_input("SuperSetor", value=current_supersetor, disabled=True, key=f"collab_supersetor_{mode}_{mat or 'new'}")
        with col8:
            input_setor = st.selectbox(
                "Setor",
                options=[""] + setor_options,
                index=option_index([""] + setor_options, str(existing.get("SETOR", ""))),
                key=selected_setor_key,
            )
        with col9:
            if str(existing.get("SUBSETOR", "")).strip() and str(existing.get("SUBSETOR", "")).strip() not in subsetor_options:
                subsetor_options.append(str(existing.get("SUBSETOR", "")).strip())
            input_subsetor = st.selectbox(
                "Subsetor",
                options=subsetor_options,
                index=option_index(subsetor_options, str(existing.get("SUBSETOR", ""))),
                key=f"collab_subsetor_{mode}_{mat or 'new'}",
            )

        input_observacoes = st.text_area(
            "Observacoes",
            value=str(existing.get("OBSERVACOES", "")),
            key=f"collab_obs_{mode}_{mat or 'new'}",
        )

        action_cols = st.columns([1, 1, 1, 3])
        with action_cols[0]:
            save_clicked = st.button("Salvar", type="primary", use_container_width=True)
        with action_cols[1]:
            cancel_clicked = st.button("Cancelar", use_container_width=True)
        with action_cols[2]:
            delete_clicked = mode == "edit" and st.button("Deletar", use_container_width=True)

        if cancel_clicked:
            st.session_state["collab_dialog_open"] = False
            st.rerun()

        if delete_clicked:
            errors = persist_crud_changes_to_db({"upserts": {}, "deletes": [mat]})
            if errors:
                st.error(" | ".join(errors))
            else:
                st.session_state["collab_dialog_open"] = False
                st.rerun()

        if save_clicked:
            final_mat = mat if mode == "edit" else str(input_mat).strip()
            org_leader_mat = current_org_leader_mat_for(input_setor, input_subsetor, final_mat)
            payload = {
                "mat": final_mat,
                "nome": str(input_nome).strip(),
                "cargo": join_cargo_nivel(input_cargo_base, input_nivel),
                "supersetor": setor_to_supersetor.get(str(input_setor).strip(), current_supersetor),
                "setor": str(input_setor).strip(),
                "subsetor": str(input_subsetor).strip(),
                "liderMat": org_leader_mat or leader_by_label.get(input_lider_label, ""),
                "posicao": str(input_posicao).strip(),
                "observacoes": str(input_observacoes).strip(),
            }
            valid_ids = set(df["MAT"].astype(str).tolist())
            validation_error = validate_collaborator_row(
                normalize_collaborator_payload(payload),
                valid_ids | ({final_mat} if final_mat else set()),
                allow_existing=(mode == "edit"),
            )
            if mode == "create" and final_mat in valid_ids:
                validation_error = "Ja existe um colaborador com essa MAT."
            if validation_error:
                st.error(validation_error)
            else:
                errors = persist_crud_changes_to_db({"upserts": {final_mat: payload}, "deletes": []})
                if errors:
                    st.error(" | ".join(errors))
                else:
                    st.session_state["collab_dialog_open"] = False
                    st.rerun()

    with st.container(border=True):
        st.markdown('<p class="filter-card-title">CRUD de colaboradores</p>', unsafe_allow_html=True)
        crud_col1, crud_col2, crud_col3 = st.columns([1, 2.4, 1])
        with crud_col1:
            if st.button("Criar colaborador", use_container_width=True):
                st.session_state["collab_dialog_mode"] = "create"
                st.session_state["collab_dialog_mat"] = ""
                st.session_state["collab_dialog_open"] = True
                st.rerun()
        with crud_col2:
            editable_labels = [
                f"{str(row.get('NOME', '')).strip()} (MAT: {str(row.get('MAT', '')).strip()})"
                for _, row in df.sort_values(["NOME", "MAT"]).iterrows()
            ]
            selected_label = st.selectbox("Colaborador para editar", options=editable_labels, key="collab_selected_label")
        with crud_col3:
            if st.button("Editar selecionado", use_container_width=True, disabled=not bool(editable_labels)):
                selected_mat = selected_label.rsplit("(MAT: ", 1)[-1].rstrip(")")
                st.session_state["collab_dialog_mode"] = "edit"
                st.session_state["collab_dialog_mat"] = selected_mat
                st.session_state["collab_dialog_open"] = True
                st.rerun()

    if st.session_state.get("collab_dialog_open"):
        collaborator_dialog()


def all_kalk_sectors(df: pd.DataFrame, setores_df: pd.DataFrame, subsetores_df: pd.DataFrame) -> list[str]:
    ordered: list[str] = []

    def add(value: str) -> None:
        value = str(value or "").strip()
        if value and value not in ordered:
            ordered.append(value)

    if setores_df is not None and not setores_df.empty:
        for value in setores_df.get("SETOR", pd.Series(dtype=str)).tolist():
            add(value)
    if subsetores_df is not None and not subsetores_df.empty:
        for value in subsetores_df.get("SETORPAI", pd.Series(dtype=str)).tolist():
            add(value)
    if "SETOR" in df.columns:
        for value in sorted({str(value).strip() for value in df["SETOR"].tolist() if str(value).strip()}, key=str.casefold):
            add(value)
    return ordered


def select_kalk_scope(scope_type: str, setor: str, subsetor: str = "") -> None:
    st.session_state["kalk_bo_scope_type"] = scope_type
    st.session_state["kalk_bo_scope_setor"] = str(setor or "").strip()
    st.session_state["kalk_bo_scope_subsetor"] = str(subsetor or "").strip()


def consume_kalk_bo_query() -> None:
    scope_type = st.query_params.get("kalk_bo_scope_type", "")
    setor = st.query_params.get("kalk_bo_setor", "")
    subsetor = st.query_params.get("kalk_bo_subsetor", "")
    if isinstance(scope_type, list):
        scope_type = scope_type[0] if scope_type else ""
    if isinstance(setor, list):
        setor = setor[0] if setor else ""
    if isinstance(subsetor, list):
        subsetor = subsetor[0] if subsetor else ""
    scope_type = str(scope_type or "").strip()
    setor = str(setor or "").strip()
    subsetor = str(subsetor or "").strip()
    if scope_type in {"setor", "subsetor"} and setor:
        st.session_state["kalk_bo_open"] = True
        select_kalk_scope(scope_type, setor, subsetor)
        for key in ["kalk_bo_scope_type", "kalk_bo_setor", "kalk_bo_subsetor"]:
            if key in st.query_params:
                del st.query_params[key]
        st.rerun()


def kalk_detail_href(scope_type: str, setor: str, subsetor: str = "") -> str:
    params = {
        "kalk_bo_scope_type": scope_type,
        "kalk_bo_setor": str(setor or "").strip(),
        "kalk_bo_subsetor": str(subsetor or "").strip(),
    }
    return "?" + urllib.parse.urlencode(params)


def render_kalk_result_table(editor_df: pd.DataFrame, config: dict) -> None:
    driver_label = str(config.get("DRIVER_LABEL", "")).strip() or "Driver"
    indicator_label = str(config.get("INDICATOR_LABEL", "")).strip() or "Indicador"
    rows_html = []
    for _, row in editor_df.iterrows():
        indicator_value = parse_optional_float(row.get("INDICADOR"))
        status = kalk_status_for_average(indicator_value, config, True)
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('NOME', '')).strip())}</td>"
            f"<td>{format_kalk_number(parse_optional_float(row.get('DRIVER')))} {status_dot_html(status)}</td>"
            f"<td>{format_kalk_number(indicator_value)} {status_dot_html(status)}</td>"
            "</tr>"
        )
    if not rows_html:
        rows_html.append('<tr><td colspan="3">Nenhum colaborador encontrado no organograma.</td></tr>')
    st.markdown(
        f"""
        <table class="kalk-bo-table">
            <thead>
                <tr>
                    <th>Colaborador</th>
                    <th>{html.escape(driver_label)}</th>
                    <th>{html.escape(indicator_label)}</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_kalk_bo_detail(
    df: pd.DataFrame,
    values_df: pd.DataFrame,
    configs: dict[tuple[str, str], dict],
    scope_type: str,
    setor: str,
    subsetor: str = "",
    *,
    editor_mode: bool = True,
    show_settings_button: bool = False,
    show_visualization: bool = True,
) -> None:
    scope_key = kalk_scope_key(scope_type, setor, subsetor)
    config = kalk_config_for_scope(configs, scope_type, setor, subsetor)
    title = subsetor if scope_type == "subsetor" else setor
    collaborators_df = collaborators_for_kalk_scope(df, scope_type, setor, subsetor)
    editor_base = build_kalk_editor_df(collaborators_df, values_df, scope_type, scope_key)

    title_col, settings_col = st.columns([0.9, 0.1], vertical_alignment="center")
    with title_col:
        st.markdown(
            f"""
            <div class="kalk-bo-detail-title">
                {status_dot_html(kalk_scope_metrics(editor_base, config, not collaborators_df.empty)["status"])}
                <h3>{html.escape(title)}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with settings_col:
        if show_settings_button:
            if st.button(
                " ",
                key=f"kalk_bo_settings_detail_{scope_type}_{scope_key}",
                help="Configurar produtividade",
                use_container_width=True,
                type="tertiary",
                icon=":material/settings:",
            ):
                st.session_state["kalk_bo_modal_open"] = True
                st.rerun()

    if editor_mode:
        close_col, _ = st.columns([0.18, 0.82])

        with st.form(f"kalk_bo_config_form_{scope_type}_{scope_key}"):
            form_col1, form_col2 = st.columns(2)
            with form_col1:
                driver_label = st.text_input(
                    "Driver",
                    value=str(config.get("DRIVER_LABEL", "")).strip(),
                    placeholder="Ex.: N de chamados",
                )
            with form_col2:
                indicator_label = st.text_input(
                    "Indicador",
                    value=str(config.get("INDICATOR_LABEL", "")).strip(),
                    placeholder="Ex.: SLA do chamado",
                )
            range_col1, range_col2 = st.columns(2)
            with range_col1:
                yellow_min = st.number_input(
                    "Minimo para amarelo",
                    value=float(config.get("YELLOW_MIN", 3.5) or 3.5),
                    step=0.1,
                    format="%.2f",
                )
            with range_col2:
                green_min = st.number_input(
                    "Minimo para verde",
                    value=float(config.get("GREEN_MIN", 4.5) or 4.5),
                    step=0.1,
                    format="%.2f",
                )
            save_config = st.form_submit_button("Salvar configuracao", type="primary", use_container_width=True)

        if save_config:
            if yellow_min > green_min:
                st.error("O minimo para amarelo deve ser menor ou igual ao minimo para verde.")
            else:
                persist_kalk_bo_config(
                    {
                        "SCOPE_TYPE": scope_type,
                        "SCOPE_KEY": scope_key,
                        "SETOR": setor,
                        "SUBSETOR": subsetor,
                        "DRIVER_LABEL": driver_label,
                        "INDICATOR_LABEL": indicator_label,
                        "YELLOW_MIN": yellow_min,
                        "GREEN_MIN": green_min,
                    }
                )
                st.success("Configuracao do KALK BO salva.")
                st.rerun()

    driver_label = str(config.get("DRIVER_LABEL", "")).strip()
    indicator_label = str(config.get("INDICATOR_LABEL", "")).strip()
    if not driver_label or not indicator_label:
        st.markdown(
            """
            <div class="kalk-bo-empty">
                Aguardando cadastro de driver e indicador para ativar este setor/subsetor.
            </div>
            """,
            unsafe_allow_html=True,
        )
    if collaborators_df.empty:
        st.markdown(
            """
            <div class="kalk-bo-empty">
                Nenhum colaborador foi encontrado no organograma para este recorte.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if editor_mode:
        edited_values = st.data_editor(
            editor_base,
            use_container_width=True,
            hide_index=True,
            disabled=["MAT", "NOME", "CARGO"],
            key=f"kalk_bo_values_editor_{scope_type}_{scope_key}",
            column_config={
                "MAT": st.column_config.TextColumn("MAT"),
                "NOME": st.column_config.TextColumn("Colaborador"),
                "CARGO": st.column_config.TextColumn("Cargo"),
                "DRIVER": st.column_config.NumberColumn(driver_label or "Driver", step=1.0, format="%.2f"),
                "INDICADOR": st.column_config.NumberColumn(indicator_label or "Indicador", step=0.1, format="%.2f"),
            },
        )
        save_values = st.button(
            "Salvar lancamentos",
            type="primary",
            use_container_width=True,
            key=f"kalk_bo_save_values_{scope_type}_{scope_key}",
            disabled=collaborators_df.empty,
        )
        if save_values:
            persist_kalk_bo_values(scope_type, scope_key, edited_values)
            st.success("Lancamentos de produtividade salvos.")
            st.rerun()
    else:
        edited_values = editor_base

    if show_visualization:
        metrics = kalk_scope_metrics(edited_values, config, not collaborators_df.empty)
        st.markdown(
            f"""
            <div class="kalk-bo-summary-grid">
                <div class="kalk-bo-summary-card">
                    <p class="kalk-bo-summary-label">Driver total do setor (soma)</p>
                    <p class="kalk-bo-summary-value">{format_kalk_number(metrics["driver_total"])} {status_dot_html(metrics["status"])}</p>
                </div>
                <div class="kalk-bo-summary-card">
                    <p class="kalk-bo-summary-label">Indicador total do setor (media)</p>
                    <p class="kalk-bo-summary-value">{format_kalk_number(metrics["indicator_avg"])} {status_dot_html(metrics["status"])}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_kalk_result_table(edited_values, config)


def render_kalk_bo_sector_list(
    df: pd.DataFrame,
    values_df: pd.DataFrame,
    configs: dict[tuple[str, str], dict],
    setores: list[str],
    subsetores_map: dict[str, list[str]],
) -> None:
    if not setores:
        st.html(
            '<div class="kalk-bo-empty">Nenhum setor encontrado.</div>',
        )
        return

    st.html(
        """
        <style>
        div[class*="st-key-kalk_"][class*="_card"] {
            margin-bottom: 0.25rem;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #c7d3e5;
            border-radius: 8px;
            background: #ffffff;
            padding: 0 !important;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
            width: 100%;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="stVerticalBlock"] {
            gap: 0;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="stHorizontalBlock"] {
            min-height: 44px;
            padding: 0 !important;
            align-items: center !important;
            gap: 0.35rem !important;
        }
        div[class*="st-key-kalk_"][class*="_child_card"] div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #edf3fb;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="column"] {
            min-height: 2rem;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }
        div[class*="st-key-kalk_"][class*="_card"] div[data-testid="stElementContainer"] {
            margin: 0 !important;
            min-height: 1.8rem;
            display: flex;
            align-items: center;
        }
        .kalk-card-dot-wrap,
        .kalk-card-name,
        .kalk-card-meta {
            min-height: 1.8rem;
            display: flex;
            align-items: center;
        }
        .kalk-card-dot-wrap {
            justify-content: center;
        }
        .kalk-card-dot-wrap .kalk-bo-dot {
            width: 18px;
            height: 18px;
            margin: 0;
        }
        .kalk-card-name {
            color: #052966;
            font-size: 18px;
            font-weight: 900;
            line-height: 1.2;
            text-align: left;
            justify-content: flex-start;
            overflow-wrap: anywhere;
        }
        .kalk-card-meta {
            color: #53657f;
            font-size: 14px;
            font-weight: 800;
            line-height: 1.2;
            white-space: nowrap;
            text-align: right;
            justify-content: flex-end;
        }
        div[class*="st-key-kalk_"][class*="_toggle"] button,
        div[class*="st-key-kalk_"][class*="_detail"] button,
        div[class*="st-key-kalk_"][class*="_settings"] button,
        div[class*="st-key-kalk_"][class*="_close"] button,
        div[class*="st-key-kalk_bo_close"] button {
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
            min-height: 2rem !important;
            color: #2f686b !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[class*="st-key-kalk_"][class*="_toggle"] button:hover,
        div[class*="st-key-kalk_"][class*="_detail"] button:hover,
        div[class*="st-key-kalk_"][class*="_settings"] button:hover,
        div[class*="st-key-kalk_"][class*="_close"] button:hover,
        div[class*="st-key-kalk_bo_close"] button:hover {
            background: rgba(47, 104, 107, 0.08) !important;
        }
        div[class*="st-key-kalk_"][class*="_toggle"] button p,
        div[class*="st-key-kalk_"][class*="_detail"] button p,
        div[class*="st-key-kalk_"][class*="_settings"] button p,
        div[class*="st-key-kalk_"][class*="_close"] button p,
        div[class*="st-key-kalk_bo_close"] button p {
            display: none;
        }
        div[class*="st-key-kalk_"][class*="_toggle"] button span,
        div[class*="st-key-kalk_"][class*="_detail"] button span,
        div[class*="st-key-kalk_"][class*="_settings"] button span,
        div[class*="st-key-kalk_"][class*="_close"] button span,
        div[class*="st-key-kalk_bo_close"] button span {
            font-size: 1.45rem !important;
        }
        </style>
        """
    )

    expanded_key = "kalk_bo_expanded_setores"
    expanded = set(st.session_state.get(expanded_key, []))

    def render_card(
        *,
        name: str,
        status: str,
        meta: str,
        key_prefix: str,
        scope_type: str | None = None,
        setor: str = "",
        subsetor: str = "",
        has_children: bool = False,
        child: bool = False,
    ) -> None:
        suffix = "_child_card" if child else "_card"
        with st.container(border=True, key=f"{key_prefix}{suffix}"):
            cols = st.columns([0.06, 0.66, 0.2, 0.08], vertical_alignment="center")
            with cols[0]:
                st.html(f'<div class="kalk-card-dot-wrap">{status_dot_html(status)}</div>')
            with cols[1]:
                st.html(f'<div class="kalk-card-name">{html.escape(name)}</div>')
            with cols[2]:
                st.html(f'<div class="kalk-card-meta">{html.escape(meta)}</div>')
            with cols[3]:
                if has_children:
                    is_expanded = setor in expanded
                    icon = ":material/keyboard_arrow_up:" if is_expanded else ":material/keyboard_arrow_down:"
                    if st.button(
                        " ",
                        key=f"{key_prefix}_toggle",
                        help="Abrir subsetores",
                        use_container_width=True,
                        type="tertiary",
                        icon=icon,
                    ):
                        if is_expanded:
                            expanded.discard(setor)
                        else:
                            expanded.add(setor)
                        st.session_state[expanded_key] = sorted(expanded)
                        st.rerun()
                elif scope_type:
                    if st.button(
                        " ",
                        key=f"{key_prefix}_detail",
                        help="Ver detalhes",
                        use_container_width=True,
                        type="tertiary",
                        icon=":material/visibility:",
                    ):
                        st.session_state["kalk_bo_modal_open"] = False
                        select_kalk_scope(scope_type, setor, subsetor)
                        st.rerun()

    for idx, setor in enumerate(setores):
        subsetores = subsetores_map.get(setor, [])
        if subsetores:
            child_statuses = [
                kalk_status_for_scope(df, values_df, configs, "subsetor", setor, subsetor)["status"]
                for subsetor in subsetores
            ]
            render_card(
                name=setor,
                status=aggregate_kalk_sector_status(child_statuses),
                meta=f"{len(subsetores)} subsetores",
                key_prefix=f"kalk_sector_{idx}",
                setor=setor,
                has_children=True,
            )
            if setor in expanded:
                for child_idx, subsetor in enumerate(subsetores):
                    status_info = kalk_status_for_scope(df, values_df, configs, "subsetor", setor, subsetor)
                    _, child_col = st.columns([0.06, 0.94])
                    with child_col:
                        render_card(
                            name=subsetor,
                            status=status_info["status"],
                            meta=f'{status_info["collaborator_count"]} colab.',
                            key_prefix=f"kalk_subsetor_{idx}_{child_idx}",
                            scope_type="subsetor",
                            setor=setor,
                            subsetor=subsetor,
                            child=True,
                        )
        else:
            status_info = kalk_status_for_scope(df, values_df, configs, "setor", setor)
            render_card(
                name=setor,
                status=status_info["status"],
                meta=f'{status_info["collaborator_count"]} colab.',
                key_prefix=f"kalk_sector_{idx}",
                scope_type="setor",
                setor=setor,
            )


def render_kalk_bo(
    df: pd.DataFrame,
    setores_df: pd.DataFrame,
    supersetores_df: pd.DataFrame,
    subsetores_df: pd.DataFrame,
) -> None:
    try:
        configs = load_kalk_bo_configs()
        values_df = load_kalk_bo_values()
    except Exception as exc:
        st.error(f"Nao foi possivel carregar dados do KALK BO: {exc}")
        return

    subsetores_map = subsetores_by_setor(subsetores_df, df)
    setores = all_kalk_sectors(df, setores_df, subsetores_df)

    @st.dialog("KALK BO", width="large")
    def kalk_bo_modal() -> None:
        scope_type = str(st.session_state.get("kalk_bo_scope_type", "")).strip()
        setor = str(st.session_state.get("kalk_bo_scope_setor", "")).strip()
        subsetor = str(st.session_state.get("kalk_bo_scope_subsetor", "")).strip()
        if scope_type and setor:
            render_kalk_bo_detail(
                df,
                values_df,
                configs,
                scope_type,
                setor,
                subsetor,
                editor_mode=True,
                show_settings_button=False,
                show_visualization=False,
            )
        else:
            st.caption("Selecione um setor ou subsetor para configurar.")

    with st.container(border=True):
        header_col, close_col = st.columns([30, 1])
        with header_col:
            st.markdown(
                f"""
                <div class="kalk-bo-header">
                    <div class="kalk-bo-title-wrap">
                        {kalk_logo_html()}
                        <div>
                            <p class="kalk-bo-title">KALK BO</p>
                            <p class="kalk-bo-subtitle">Produtividade por setor, subsetor e colaborador</p>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button(
                " ",
                key="kalk_bo_close",
                help="Fechar KALK BO",
                use_container_width=True,
                type="tertiary",
                icon=":material/close:",
            ):
                st.session_state["kalk_bo_open"] = False
                st.rerun()

        left_col, right_col = st.columns([1.05, 1])
        with left_col:
            st.markdown("**Setores**")
            render_kalk_bo_sector_list(df, values_df, configs, setores, subsetores_map)

        with right_col:
            scope_type = str(st.session_state.get("kalk_bo_scope_type", "")).strip()
            setor = str(st.session_state.get("kalk_bo_scope_setor", "")).strip()
            subsetor = str(st.session_state.get("kalk_bo_scope_subsetor", "")).strip()
            if scope_type and setor:
                render_kalk_bo_detail(
                    df,
                    values_df,
                    configs,
                    scope_type,
                    setor,
                    subsetor,
                    editor_mode=False,
                    show_settings_button=True,
                    show_visualization=True,
                )
            else:
                st.markdown(
                    """
                    <div class="kalk-bo-empty">
                        Selecione um setor sem subsetores ou abra um setor com subsetores para detalhar um subsetor.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if st.session_state.get("kalk_bo_modal_open"):
        kalk_bo_modal()


def build_hierarchy_network(
    setores_df: pd.DataFrame,
    supersetores_df: pd.DataFrame,
    subsetores_df: pd.DataFrame,
) -> Network:
    net = Network(
        height="540px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
    )

    setor_to_supersetor = setor_supersetor_map(supersetores_df)
    subsetores_map = subsetores_by_setor(subsetores_df, pd.DataFrame(columns=COLLABORATOR_COLUMNS))

    all_setores = sorted(
        {
            str(value).strip()
            for value in setores_df.get("SETOR", pd.Series(dtype=str)).tolist()
            if str(value).strip()
        }
        | {
            str(value).strip()
            for value in supersetores_df.get("SETORFILHO", pd.Series(dtype=str)).tolist()
            if str(value).strip()
        }
        | {
            str(value).strip()
            for value in subsetores_df.get("SETORPAI", pd.Series(dtype=str)).tolist()
            if str(value).strip()
        },
        key=str.casefold,
    )

    supersetor_children: dict[str, list[str]] = defaultdict(list)
    for setor in all_setores:
        supersetor = setor_to_supersetor.get(setor, "") or "Nao definido"
        supersetor_children[supersetor].append(setor)

    supersetor_order = [
        str(value).strip()
        for value in supersetores_df.get("SUPERSETOR", pd.Series(dtype=str)).tolist()
        if str(value).strip()
    ]
    supersetores = []
    for value in supersetor_order + sorted(supersetor_children.keys(), key=str.casefold):
        if value not in supersetores and value in supersetor_children:
            supersetores.append(value)

    positions: dict[str, tuple[float, float]] = {}
    leaf_gap = 230.0
    sector_gap = 0.45
    super_gap = 0.75
    y_levels = {
        "supersetor": 0.0,
        "setor": 185.0,
        "subsetor": 370.0,
    }
    cursor = 0.0

    def node_id(kind: str, name: str) -> str:
        return f"{kind}::{name}"

    for supersetor in supersetores:
        first_cursor = cursor
        sectors = sorted(supersetor_children.get(supersetor, []), key=str.casefold)
        for sector_index, setor in enumerate(sectors):
            subsetores = sorted(subsetores_map.get(setor, []), key=str.casefold)
            if subsetores:
                subsetor_slots = []
                for subsetor in subsetores:
                    x = cursor * leaf_gap
                    positions[node_id("subsetor", f"{setor}||{subsetor}")] = (x, y_levels["subsetor"])
                    subsetor_slots.append(x)
                    cursor += 1.0
                positions[node_id("setor", setor)] = (sum(subsetor_slots) / len(subsetor_slots), y_levels["setor"])
            else:
                x = cursor * leaf_gap
                positions[node_id("setor", setor)] = (x, y_levels["setor"])
                cursor += 1.0
            if sector_index < len(sectors) - 1:
                cursor += sector_gap

        if sectors:
            sector_positions = [positions[node_id("setor", setor)][0] for setor in sectors]
            positions[node_id("supersetor", supersetor)] = (sum(sector_positions) / len(sector_positions), y_levels["supersetor"])
        else:
            positions[node_id("supersetor", supersetor)] = (first_cursor * leaf_gap, y_levels["supersetor"])
            cursor += 1.0
        cursor += super_gap

    if not positions:
        positions[node_id("supersetor", "Nao definido")] = (0.0, y_levels["supersetor"])

    def add_node(kind: str, name: str) -> str:
        name = str(name or "").strip()
        nid = node_id(kind, name)
        if kind == "subsetor" and "||" in name:
            display_name = name.split("||", 1)[1]
        else:
            display_name = name
        existing = {str(node.get("id")) for node in net.nodes}
        if nid in existing:
            return nid
        color_by_kind = {
            "supersetor": {"background": "#14315E", "border": "#0f274a"},
            "setor": {"background": "#2FD68B", "border": "#1f9d66"},
            "subsetor": {"background": "#D8E6F8", "border": "#7f9fc4"},
        }
        label_prefix = {
            "supersetor": "SuperSetor",
            "setor": "Setor",
            "subsetor": "Subsetor",
        }.get(kind, kind)
        x, y = positions.get(nid, (0.0, 0.0))
        net.add_node(
            nid,
            label=f"{label_prefix}\n{display_name}",
            title=display_name,
            shape="box",
            margin=12,
            color=color_by_kind.get(kind, color_by_kind["subsetor"]),
            font={"color": "#FFFFFF" if kind == "supersetor" else "#14315E", "size": 16, "face": "Arial"},
            x=x,
            y=y,
            fixed={"x": True, "y": True},
            physics=False,
            widthConstraint={"minimum": 150, "maximum": 210},
        )
        return nid

    bend_seq = 0

    def add_elbow_edge(parent: str, child: str, *, dashed: bool = False) -> None:
        nonlocal bend_seq
        px, py = positions.get(parent, (0.0, 0.0))
        cx, cy = positions.get(child, (0.0, 0.0))
        mid_y = (py + cy) / 2.0
        b1 = f"hierarchy_bend::{bend_seq}::1"
        b2 = f"hierarchy_bend::{bend_seq}::2"
        bend_seq += 1
        bend_style = {
            "size": 0.1,
            "shape": "dot",
            "label": "",
            "title": "",
            "font": {"size": 1, "color": "rgba(0,0,0,0)"},
            "color": {"background": "rgba(0,0,0,0)", "border": "rgba(0,0,0,0)"},
            "borderWidth": 0,
            "fixed": {"x": True, "y": True},
            "physics": False,
        }
        net.add_node(b1, x=px, y=mid_y, **bend_style)
        net.add_node(b2, x=cx, y=mid_y, **bend_style)
        edge_style = {"color": "#7f95b5", "width": 2, "dashes": dashed}
        net.add_edge(parent, b1, arrows="", **edge_style)
        net.add_edge(b1, b2, arrows="", **edge_style)
        net.add_edge(b2, child, arrows="to", **edge_style)

    for supersetor in supersetores:
        parent = add_node("supersetor", supersetor)
        for setor in sorted(supersetor_children.get(supersetor, []), key=str.casefold):
            child = add_node("setor", setor)
            add_elbow_edge(parent, child, dashed=(supersetor == "Nao definido"))
            for subsetor in sorted(subsetores_map.get(setor, []), key=str.casefold):
                subsetor_key = f"{setor}||{subsetor}"
                subsetor_node = add_node("subsetor", subsetor_key)
                add_elbow_edge(child, subsetor_node)

    options = {
        "layout": {"hierarchical": {"enabled": False}},
        "physics": {"enabled": False},
        "edges": {"smooth": {"enabled": False}},
        "interaction": {"hover": True, "dragView": True, "zoomView": True, "zoomSpeed": 0.35, "navigationButtons": True},
    }
    net.set_options(json.dumps(options))
    return net


def render_hierarchy_manager(
    df: pd.DataFrame,
    setores_df: pd.DataFrame,
    supersetores_df: pd.DataFrame,
    subsetores_df: pd.DataFrame,
) -> None:
    with st.container(border=True):
        header_col, close_col = st.columns([5, 1])
        with header_col:
            st.subheader("Hierarquia de SuperSetores, Setores e Subsetores")
        with close_col:
            if st.button("Fechar hierarquia", use_container_width=True):
                st.session_state["hierarchy_open"] = False
                st.rerun()

        tree_tab, editor_tab = st.tabs(["Arvore", "Editar relacoes"])

        with tree_tab:
            net = build_hierarchy_network(setores_df, supersetores_df, subsetores_df)
            st.components.v1.html(net.generate_html(notebook=False), height=560, scrolling=True)

        with editor_tab:
            st.markdown("**Setores**")
            setores_edit = st.data_editor(
                setores_df,
                num_rows="dynamic",
                use_container_width=True,
                key="hierarchy_setores_editor",
                column_order=["SETOR", "LIDERMAT"],
            )
            if st.button("Salvar setores", type="primary", key="save_hierarchy_setores"):
                persist_hierarchy_setores(setores_edit)
                st.success("Setores salvos.")
                st.rerun()

            st.markdown("**SuperSetores -> Setores**")
            supersetores_edit = st.data_editor(
                supersetores_df,
                num_rows="dynamic",
                use_container_width=True,
                key="hierarchy_supersetores_editor",
                column_order=["SUPERSETOR", "SETORFILHO", "LIDERMAT"],
            )
            if st.button("Salvar relacoes de SuperSetor", type="primary", key="save_hierarchy_supersetores"):
                persist_hierarchy_supersetores(supersetores_edit)
                st.success("Relacoes de SuperSetor salvas.")
                st.rerun()

            st.markdown("**Setores -> Subsetores**")
            subsetores_edit = st.data_editor(
                subsetores_df,
                num_rows="dynamic",
                use_container_width=True,
                key="hierarchy_subsetores_editor",
                column_order=["SETORPAI", "SUBSETOR", "LIDERMAT"],
            )
            if st.button("Salvar relacoes de Subsetor", type="primary", key="save_hierarchy_subsetores"):
                persist_hierarchy_subsetores(subsetores_edit)
                st.success("Relacoes de Subsetor salvas.")
                st.rerun()


def main():
    render_brand_header()

    path = COLLABORATORS_CSV_PATH
    setores_path = SETORES_CSV_PATH
    supersetores_path = SUPERSETORES_CSV_PATH
    subsetores_path = SUBSETORES_CSV_PATH
    
    try:
        init_collaborator_db(path)
        init_hierarchy_db(setores_path, supersetores_path, subsetores_path)
        init_kalk_bo_db()
        consume_crud_query()
        consume_kalk_bo_query()
        df = load_collaborators_from_db()
    except Exception as exc:
        st.error(f"Erro ao carregar colaboradores: {exc}")
        return

    try:
        setores_df, supersetores_df, subsetores_df = load_hierarchy_from_db()
    except Exception as exc:
        st.warning(f"Nao foi possivel carregar hierarquia do banco: {exc}")
        setores_df = pd.DataFrame(columns=["SETOR", "LIDERMAT"])
        supersetores_df = pd.DataFrame(columns=["SUPERSETOR", "SETORFILHO", "LIDERMAT"])
        subsetores_df = pd.DataFrame(columns=["SUBSETOR", "SETORPAI", "LIDERMAT"])

    posicoes = sorted([p for p in df["POSICAO"].dropna().unique() if p])
    setores = sorted([s for s in setores_df["SETOR"].dropna().unique() if s]) if not setores_df.empty else []

    if "sidebar_view" not in st.session_state:
        st.session_state["sidebar_view"] = "none"
    if "selected_setores" not in st.session_state:
        st.session_state["selected_setores"] = []
    if "selected_posicoes" not in st.session_state:
        st.session_state["selected_posicoes"] = posicoes
    if "selected_suggestion_idx" not in st.session_state:
        st.session_state["selected_suggestion_idx"] = 0
    if "hierarchy_open" not in st.session_state:
        st.session_state["hierarchy_open"] = False
    if "kalk_bo_open" not in st.session_state:
        st.session_state["kalk_bo_open"] = False
    if "horizontal_view" not in st.session_state:
        st.session_state["horizontal_view"] = False
    if st.session_state.get("crud_errors"):
        st.error("Nao foi possivel salvar uma ou mais alteracoes: " + " | ".join(st.session_state["crud_errors"]))
    if st.session_state.get("leader_redistribution_message"):
        st.success(str(st.session_state["leader_redistribution_message"]))
        del st.session_state["leader_redistribution_message"]

    sidebar_view = str(st.session_state.get("sidebar_view", "none"))
    if sidebar_view in {"ranking", "suggestions"}:
        request_sidebar_open()

    with st.container(border=True):
        st.markdown('<p class="filter-card-title">Filtros</p>', unsafe_allow_html=True)
        filter_col1, filter_col2 = st.columns([1.2, 1.25])
        with filter_col1:
            selected_setores = st.multiselect(
                "Setor",
                options=setores,
                default=st.session_state.get("selected_setores", []),
                key="selected_setores",
                help="Mostra lider do setor, todos os liderados e o caminho de lideranca ate o CEO.",
            )
        with filter_col2:
            selected_posicoes = st.multiselect(
                "Posicao",
                options=posicoes,
                default=st.session_state.get("selected_posicoes", posicoes),
                key="selected_posicoes",
                help="Filtre por nivel/posicao no organograma (aplicado quando Setor nao estiver selecionado).",
            )
        search = ""

        if selected_setores and not setores_df.empty:
            sector_ids = get_sector_descendant_ids(df, setores_df, selected_setores)
            cargos_setor = sorted(
                [c for c in df[df["MAT"].isin(sector_ids)]["CARGO"].dropna().unique() if c]
            )
            if cargos_setor:
                st.markdown(
                    f'<p class="filter-card-caption"><b>Cargos existentes no(s) setor(es):</b> {html.escape(", ".join(cargos_setor))}</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<p class="filter-card-caption">Nenhum cargo encontrado para o(s) setor(es) selecionado(s).</p>',
                    unsafe_allow_html=True,
                )

    action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns([1.35, 1.7, 1.75, 1.75, 1.35])
    with action_col1:
        if st.button("Mostrar ranking de span", use_container_width=True):
            st.session_state["sidebar_view"] = "ranking"
            st.rerun()
    with action_col2:
        if st.button("Mostrar sugestoes de split/merge", use_container_width=True):
            st.session_state["sidebar_view"] = "suggestions"
            st.rerun()
    with action_col3:
        if st.button("Hierarquia de setores", use_container_width=True):
            st.session_state["hierarchy_open"] = not bool(st.session_state.get("hierarchy_open"))
            st.rerun()
    with action_col4:
        if st.button("Redistribuir liderados", use_container_width=True):
            invalid_leaders = out_of_area_leader_ids(df, setores_df, subsetores_df)
            updated, errors = redistribute_collaborator_leaders(
                setores_df,
                subsetores_df,
                only_current_leaders=invalid_leaders,
            ) if invalid_leaders else (0, [])
            if errors:
                st.session_state["crud_errors"] = errors
            else:
                if updated:
                    message = f"{updated} liderado(s) redistribuido(s)."
                elif invalid_leaders:
                    message = "Nenhum liderado foi redistribuido; confira se ha lider de subsetor ou setor cadastrado."
                else:
                    message = "Nenhum liderado precisava de redistribuicao."
                st.session_state["leader_redistribution_message"] = message
            st.rerun()
    with action_col5:
        if st.button(kalk_button_label(), use_container_width=True, key="open_kalk_bo_button"):
            st.session_state["kalk_bo_open"] = not bool(st.session_state.get("kalk_bo_open"))
            st.rerun()

    filtered, edge_count, highlighted_ids = build_graph(
        df,
        selected_posicoes,
        search,
        setores_df=setores_df,
        selected_setores=selected_setores,
    )
    horizontal_view = bool(st.session_state.get("horizontal_view", False))
    direction = "LR" if horizontal_view else "UD"
    ranking_df = build_span_ranking(filtered)
    suggestions = generate_reorg_suggestions(filtered)

    if sidebar_view == "ranking":
        st.sidebar.header("Ranking de Span")
        if st.sidebar.button("Fechar painel", use_container_width=True):
            st.session_state["sidebar_view"] = "none"
            st.rerun()
        if st.sidebar.button("Ir para sugestoes", use_container_width=True):
            st.session_state["sidebar_view"] = "suggestions"
            st.rerun()
        st.sidebar.markdown("**Lideres por span (maior para menor)**")
        if ranking_df.empty:
            st.sidebar.caption("Nenhum lider com span encontrado no recorte atual.")
        else:
            st.sidebar.markdown(
                """
                <style>
                .span-card {
                    border: 1px solid rgba(20, 49, 94, 0.15);
                    border-left: 6px solid #14315E;
                    border-radius: 10px;
                    padding: 0.6rem 0.7rem;
                    margin-bottom: 0.55rem;
                    background: linear-gradient(180deg, rgba(47,214,139,0.08), rgba(20,49,94,0.02));
                }
                .span-card-name {
                    color: #14315E;
                    font-weight: 700;
                    margin: 0;
                    font-size: 0.94rem;
                    line-height: 1.25;
                }
                .span-card-role {
                    color: #2b3f66;
                    margin: 0.2rem 0 0.4rem 0;
                    font-size: 0.82rem;
                    line-height: 1.25;
                }
                .span-card-badge {
                    display: inline-block;
                    background: #14315E;
                    color: #FFFFFF;
                    border-radius: 999px;
                    padding: 0.14rem 0.52rem;
                    font-size: 0.78rem;
                    font-weight: 700;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            for _, row in ranking_df.iterrows():
                nome = html.escape(str(row.get("NOME", "")))
                cargo = html.escape(str(row.get("CARGO", "")))
                span = int(row.get("SPAN", 0))
                st.sidebar.markdown(
                    f"""
                    <div class="span-card">
                        <p class="span-card-name">{nome}</p>
                        <p class="span-card-role">{cargo}</p>
                        <span class="span-card-badge">Span: {span}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    elif sidebar_view == "suggestions":
        st.sidebar.header("Sugestoes")
        if st.sidebar.button("Fechar painel", use_container_width=True):
            st.session_state["sidebar_view"] = "none"
            st.rerun()
        if st.sidebar.button("Ir para ranking", use_container_width=True):
            st.session_state["sidebar_view"] = "ranking"
            st.rerun()
        st.sidebar.markdown("**Sugestoes de split/merge (baseado em span e estrutura atual)**")
        if not suggestions:
            st.sidebar.caption("Nenhuma sugestao encontrada para o recorte atual.")
        else:
            selected_idx = int(st.session_state.get("selected_suggestion_idx", 0))
            if selected_idx < 0 or selected_idx >= len(suggestions):
                selected_idx = 0
                st.session_state["selected_suggestion_idx"] = 0

            for idx, suggestion in enumerate(suggestions):
                title = str(suggestion.get("title", "Sugestao"))
                summary = str(suggestion.get("summary", ""))
                impact = int(suggestion.get("impact", 0))
                is_selected = idx == selected_idx
                button_label = f"{idx + 1}. {title}"
                if st.sidebar.button(button_label, key=f"suggestion_btn_{idx}", use_container_width=True):
                    st.session_state["selected_suggestion_idx"] = idx
                    st.rerun()
                st.sidebar.caption(f"{'Selecionada' if is_selected else 'Clique para abrir'} | Impacto: {impact}")
                st.sidebar.caption(summary)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de pessoas", f"{len(df)}")
    c2.metric("Pessoas no grafico", f"{len(filtered)}")
    c3.metric("Conexoes", f"{edge_count}")
    if search.strip():
        st.caption(f"Busca ativa: {len(highlighted_ids)} destaque(s) no organograma.")

    if st.session_state.get("hierarchy_open"):
        render_hierarchy_manager(df, setores_df, supersetores_df, subsetores_df)

    if st.session_state.get("kalk_bo_open"):
        render_kalk_bo(df, setores_df, supersetores_df, subsetores_df)

    if filtered.empty:
        st.warning("Nenhum resultado para os filtros selecionados.")
        return

    if sidebar_view == "suggestions" and suggestions:
        selected_idx = int(st.session_state.get("selected_suggestion_idx", 0))
        if selected_idx < 0 or selected_idx >= len(suggestions):
            selected_idx = 0
            st.session_state["selected_suggestion_idx"] = 0

        selected_suggestion = suggestions[selected_idx]
        st.subheader("Sugestao de reorganizacao")
        suggestion_title = html.escape(str(selected_suggestion.get("title", "")))
        suggestion_summary = html.escape(str(selected_suggestion.get("summary", "")))
        suggestion_kind = html.escape(str(selected_suggestion.get("kind", ""))).title()
        suggestion_impact = int(selected_suggestion.get("impact", 0))
        st.markdown(
            f"""
            <div class="detail-card">
                <p class="detail-card-title">{suggestion_title}</p>
                <p class="detail-card-subtitle">{suggestion_summary}</p>
                <div class="detail-card-grid">
                    <div class="detail-card-field">
                        <p class="detail-card-label">Tipo</p>
                        <p class="detail-card-value">{suggestion_kind}</p>
                    </div>
                    <div class="detail-card-field">
                        <p class="detail-card-label">Impacto estimado</p>
                        <p class="detail-card-value">{suggestion_impact}</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_focus_ids = build_focus_scope(filtered, list(selected_suggestion.get("focus_ids", [])))
        current_focus = filtered[filtered["MAT"].isin(current_focus_ids)].copy()

        proposed = apply_reorg_suggestion(filtered, selected_suggestion)
        proposed_focus_ids = build_focus_scope(proposed, list(selected_suggestion.get("focus_ids", [])))
        proposed_focus = proposed[proposed["MAT"].isin(proposed_focus_ids)].copy()

        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**Como esta hoje (foco na area da mudanca)**")
            net_current, containers_current = build_pyvis_network(
                current_focus,
                direction=direction,
                highlighted_ids=highlighted_ids,
                editor_df=df,
                setores_df=setores_df,
                supersetores_df=supersetores_df,
                subsetores_df=subsetores_df,
            )
            render_pyvis(net_current, containers=containers_current, height=520, enable_crud=False)
        with right_col:
            st.markdown("**Como ficaria com a sugestao aplicada**")
            net_proposed, containers_proposed = build_pyvis_network(
                proposed_focus,
                direction=direction,
                highlighted_ids=highlighted_ids,
                editor_df=df,
                setores_df=setores_df,
                supersetores_df=supersetores_df,
                subsetores_df=subsetores_df,
            )
            render_pyvis(net_proposed, containers=containers_proposed, height=520, enable_crud=False)

    view_title_col, view_toggle_col = st.columns([0.78, 0.22], vertical_alignment="center")
    with view_title_col:
        st.markdown(
            '<div class="visualization-header"><h3>Visualização</h3></div>',
            unsafe_allow_html=True,
        )
    with view_toggle_col:
        st.toggle("Modo horizontal", key="horizontal_view")

    net, containers = build_pyvis_network(
        filtered,
        direction=direction,
        highlighted_ids=highlighted_ids,
        editor_df=df,
        setores_df=setores_df,
        supersetores_df=supersetores_df,
        subsetores_df=subsetores_df,
    )
    graph_event = render_pyvis(net, containers=containers, enable_crud=True)
    if isinstance(graph_event, dict):
        nonce = str(graph_event.get("nonce", ""))
        if nonce and nonce != st.session_state.get("last_org_chart_event_nonce"):
            st.session_state["last_org_chart_event_nonce"] = nonce
            changes = graph_event.get("changes", {})
            errors = persist_crud_changes_to_db(changes) if isinstance(changes, dict) else ["Evento invalido do organograma."]
            if errors:
                st.session_state["crud_errors"] = errors
            elif "crud_errors" in st.session_state:
                del st.session_state["crud_errors"]
            st.rerun()

    st.caption(
        "Dica: use scroll para zoom, arraste o fundo para navegar e arraste nos para reorganizar localmente."
    )

    st.subheader("Tabela")
    st.dataframe(filtered[["MAT", "NOME", "CARGO", "LIDER", "POSICAO"]], use_container_width=True)

    csv = filtered.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        "Baixar dados filtrados (CSV)",
        data=csv,
        file_name="organograma_filtrado.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
