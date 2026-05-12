import tempfile
import json
import base64
import html
import statistics
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


ICON_PATH = Path("assets/logoOrganograma.png")
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
    }
    .brand-subtitle {
        color: #14315E;
        opacity: 0.85;
        margin-top: 0.35rem;
        margin-bottom: 0;
        text-align: center;
    }
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.15rem 0 0.5rem 0;
    }
    .brand-header-left,
    .brand-header-right {
        width: 220px;
        min-width: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .brand-header-center {
        flex: 1;
        text-align: center;
    }
    .brand-title-block {
        padding-bottom: 0.4rem;
    }
    .brand-logo {
        max-height: 110px;
        max-width: 100%;
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
        color: #14315E;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def logo_data_uri(path: Path, mime: str) -> str | None:
    if not path.exists():
        return None
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_brand_header() -> None:
    gentil_uri = logo_data_uri(Path("assets/logoGentil.png"), "image/png")
    nex_uri = logo_data_uri(Path("assets/logoNEX.svg"), "image/svg+xml")

    gentil_html = (
        f'<img src="{gentil_uri}" class="brand-logo" alt="Logo Gentil">' if gentil_uri else ""
    )
    nex_html = f'<img src="{nex_uri}" class="brand-logo" alt="Logo NEX">' if nex_uri else ""

    st.markdown(
        f"""
        <div class="brand-header">
            <div class="brand-header-left">{gentil_html}</div>
            <div class="brand-header-center"></div>
            <div class="brand-header-right">{nex_html}</div>
        </div>
        <div class="brand-title-block" style="text-align:center; padding-bottom:0.4rem;">
            <h1 style="margin:0.35rem 0 0 0; color:#14315E; font-size:6rem !important; line-height:1.05; font-weight:800;">
                Organograma da Empresa
            </h1>
            <p style="margin:0.4rem 0 0 0; color:#14315E; opacity:0.85; font-size:1.25rem; font-weight:600;">
                Visualizacao baseada no arquivo organograma.csv
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    return df.drop_duplicates(subset=["MAT"], keep="first").reset_index(drop=True)


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
    if not supersetores_df.empty:
        for _, row in supersetores_df.iterrows():
            setor_to_supersetor[row["SETORFILHO"]] = row["SUPERSETOR"]
    
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
        setor = str(row.get("SETOR", "")).strip()
        subsetor = str(row.get("SUBSETOR", "")).strip()
        supersetor = str(row.get("SUPERSETOR", "")).strip()
        if not setor and subsetor in subsetor_to_setor:
            setor = subsetor_to_setor[subsetor]
        if not supersetor and setor in setor_to_supersetor:
            supersetor = setor_to_supersetor[setor]
        return {
            "supersetor": supersetor,
            "setor": setor,
            "subsetor": subsetor,
            "nome": str(row.get("NOME", "")).strip(),
            "cargo": str(row.get("CARGO", "")).strip(),
            "posicao": str(row.get("POSICAO", "")).strip(),
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

    def most_common_position(cargo: str) -> str:
        if "CARGO" not in editor_source.columns or "POSICAO" not in editor_source.columns:
            return ""
        matches = [
            str(value).strip()
            for value in editor_source.loc[editor_source["CARGO"].astype(str).str.strip() == cargo, "POSICAO"].tolist()
            if str(value).strip()
        ]
        if not matches:
            return ""
        return max(sorted(set(matches)), key=matches.count)

    sectors_for_editor = unique_sorted("SETOR")
    cargos_for_editor = unique_sorted("CARGO")
    positions_for_editor = unique_sorted("POSICAO")
    cargo_position_map = {cargo: most_common_position(cargo) for cargo in cargos_for_editor}

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

    sector_leaders: dict[str, dict[str, str]] = {}
    if not setores_df.empty:
        for _, row in setores_df.iterrows():
            setor = str(row.get("SETOR", "")).strip()
            lider_id = str(row.get("LIDERMAT", "")).strip()
            if setor and lider_id:
                sector_leaders[setor] = {"mat": lider_id, "nome": name_by_id.get(lider_id, lider_id)}

    subsetor_leaders: dict[str, dict[str, str]] = {}
    if not subsetores_df.empty:
        for _, row in subsetores_df.iterrows():
            setor = str(row.get("SETORPAI", "")).strip()
            subsetor = str(row.get("SUBSETOR", "")).strip()
            lider_id = str(row.get("LIDERMAT", "")).strip()
            if setor and subsetor and lider_id:
                subsetor_leaders[f"{setor}||{subsetor}"] = {
                    "mat": lider_id,
                    "nome": name_by_id.get(lider_id, lider_id),
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
        radius_by_node = {node_id: node_primary_half_width(node_id) for node_id in graph.nodes}

        def make_box(name: str, nodes: list[str]) -> dict[str, float | str]:
            primary_values: list[float] = []
            secondary_values: list[float] = []
            radii: list[float] = []
            for node_id in nodes:
                if node_id not in slot or node_id not in depth:
                    continue
                primary_values.append(slot[node_id] * sibling_gap)
                secondary_values.append(depth[node_id] * level_gap)
                radii.append(radius_by_node.get(node_id, 58.0))
            if not primary_values or not secondary_values:
                return {}
            max_radius = max(radii or [58.0])
            return {
                "name": name,
                "primary_min": min(primary_values) - max_radius - primary_padding,
                "primary_max": max(primary_values) + max_radius + primary_padding,
                "secondary_min": min(secondary_values) - max_radius - secondary_padding_before,
                "secondary_max": max(secondary_values) + max_radius + secondary_padding_after,
            }

        for _ in range(4):
            boxes = [box for name, nodes in groups.items() if (box := make_box(name, nodes))]
            boxes.sort(key=lambda box: ((box["primary_min"] + box["primary_max"]) / 2, sort_text(str(box["name"]))))
            moved = False
            for index in range(1, len(boxes)):
                previous = boxes[index - 1]
                current = boxes[index]
                secondary_overlap = previous["secondary_max"] > current["secondary_min"] and current["secondary_max"] > previous["secondary_min"]
                if not secondary_overlap:
                    continue
                overlap = previous["primary_max"] + gap - current["primary_min"]
                if overlap <= 0:
                    continue
                delta_slots = overlap / sibling_gap
                for node_id in groups.get(str(current["name"]), []):
                    slot[node_id] = slot.get(node_id, 0.0) + delta_slots
                moved = True
            if not moved:
                break

    compact_subsetor_roots()
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    separate_group_slots(
        subsetor_nodes(),
        primary_padding=18,
        secondary_padding_before=18,
        secondary_padding_after=30,
        gap=18,
    )
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    separate_group_slots(
        sector_nodes(),
        primary_padding=26,
        secondary_padding_before=24,
        secondary_padding_after=42,
        gap=24,
    )
    enforce_sibling_text_spacing()
    enforce_level_spacing()
    separate_group_slots(
        supersetor_nodes(),
        primary_padding=30,
        secondary_padding_before=28,
        secondary_padding_after=44,
        gap=36,
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
                "baseLabel": attrs["label"],
                "span": span,
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
) -> None:
    html_content = net.generate_html(notebook=False)
    def json_for_script(value: object) -> str:
        return (
            json.dumps(value, ensure_ascii=False)
            .replace("</", "<\\/")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    container_json = json_for_script(containers or {})
    editor_json = json_for_script(getattr(net, "org_editor_data", {}))
    initial_scale_json = json.dumps(initial_scale)
    
    # Adicionar CSS e JavaScript customizados para renderizar containers
    container_styles = """
    <style>
    .collab-modal-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(15, 39, 74, 0.24);
        z-index: 20;
        display: none;
        align-items: center;
        justify-content: center;
        pointer-events: auto;
    }

    .collab-modal-backdrop.is-open {
        display: flex;
    }

    .collab-modal {
        width: min(560px, calc(100% - 32px));
        background: #FFFFFF;
        border: 1px solid rgba(20, 49, 94, 0.16);
        border-radius: 8px;
        box-shadow: 0 18px 54px rgba(15, 39, 74, 0.22);
        font-family: Arial, sans-serif;
        color: #14315E;
    }

    .collab-modal-header,
    .collab-modal-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 14px 16px;
        border-bottom: 1px solid rgba(20, 49, 94, 0.1);
    }

    .collab-modal-footer {
        border-top: 1px solid rgba(20, 49, 94, 0.1);
        border-bottom: 0;
        justify-content: flex-end;
    }

    .collab-modal-title {
        margin: 0;
        font-size: 16px;
        font-weight: 700;
    }

    .collab-modal-body {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        padding: 16px;
    }

    .collab-field.full {
        grid-column: 1 / -1;
    }

    .collab-field label {
        display: block;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 5px;
        text-transform: uppercase;
        color: #53657f;
    }

    .collab-field input,
    .collab-field select {
        width: 100%;
        box-sizing: border-box;
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 8px 9px;
        color: #14315E;
        background: #FFFFFF;
        font-size: 13px;
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
        font-weight: 700;
    }

    .collab-button {
        border: 1px solid rgba(20, 49, 94, 0.22);
        border-radius: 6px;
        padding: 8px 12px;
        background: #FFFFFF;
        color: #14315E;
        cursor: pointer;
        font-weight: 700;
    }

    .collab-button.primary {
        background: #14315E;
        color: #FFFFFF;
    }

    .collab-button.danger {
        border-color: rgba(190, 18, 60, 0.35);
        color: #BE123C;
    }

    .collab-button.icon {
        border: 0;
        padding: 4px 6px;
        font-size: 18px;
    }
    </style>
    
    <script>
    (function() {
        const editorData = """ + editor_json + """;
        const initialScale = """ + initial_scale_json + """;
        const MIN_ZOOM_LEVEL = 0.18;
        const MAX_ZOOM_LEVEL = 2.5;
        let eventsBound = false;
        let initialViewApplied = false;
        let modalInstalled = false;
        let isClampingZoom = false;

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
                const details = node.collaborator || {};
                const item = {
                    id: node.id,
                    x: Number(node.x) || 0,
                    y: Number(node.y) || 0,
                    size: Number(node.size) || 22
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
            try {
                if (visNetwork && typeof visNetwork.getBoundingBox === 'function') {
                    const box = visNetwork.getBoundingBox(node.id);
                    if (box && Number.isFinite(box.left) && Number.isFinite(box.right) && Number.isFinite(box.top) && Number.isFinite(box.bottom)) {
                        return box;
                    }
                }
            } catch (err) {
                // Fallback below.
            }
            const radius = Math.max(42, (Number(node.size) || 22) * 1.7);
            const x = Number(node.x) || 0;
            const y = Number(node.y) || 0;
            return { left: x - radius, right: x + radius, top: y - radius, bottom: y + radius };
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

            return {
                type,
                name,
                left: minX - padding.x,
                right: maxX + padding.x,
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

        function clampZoom(visNetwork) {
            if (!visNetwork || typeof visNetwork.getScale !== 'function' || typeof visNetwork.moveTo !== 'function') return;
            if (isClampingZoom) return;
            const scale = visNetwork.getScale();
            if (!Number.isFinite(scale)) return;
            if (scale >= MIN_ZOOM_LEVEL && scale <= MAX_ZOOM_LEVEL) return;
            isClampingZoom = true;
            const targetScale = Math.min(Math.max(scale, MIN_ZOOM_LEVEL), MAX_ZOOM_LEVEL);
            const position = typeof visNetwork.getViewPosition === 'function' ? visNetwork.getViewPosition() : undefined;
            visNetwork.moveTo({
                position: position,
                scale: targetScale,
                animation: false
            });
            window.setTimeout(function() {
                isClampingZoom = false;
            }, 0);
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

        function modalMarkup() {
            return `
                <div class="collab-modal" role="dialog" aria-modal="true">
                    <div class="collab-modal-header">
                        <p class="collab-modal-title">Detalhes do colaborador</p>
                        <button type="button" class="collab-button icon" data-action="close" aria-label="Fechar">x</button>
                    </div>
                    <div class="collab-modal-body">
                        <div class="collab-field"><label>Matrícula</label><input data-field="mat" readonly></div>
                        <div class="collab-field"><label>Nome</label><input data-field="nome" readonly></div>
                        <div class="collab-field"><label>Cargo</label><input data-field="cargo" readonly></div>
                        <div class="collab-field"><label>Setor</label><input data-field="setor" readonly></div>
                        <div class="collab-field"><label>Subsetor</label><input data-field="subsetor" readonly></div>
                        <div class="collab-field"><label>Supersetor</label><input data-field="supersetor" readonly></div>
                        <div class="collab-field"><label>Líder</label><input data-field="lider" readonly></div>
                        <div class="collab-field"><label>Posição</label><input data-field="posicao" readonly></div>
                        <div class="collab-field full"><label>Span</label><input data-field="span" readonly></div>
                    </div>
                    <div class="collab-modal-footer">
                        <button type="button" class="collab-button" data-action="close">Fechar</button>
                    </div>
                </div>
            `;
        }

        function ensureDetailsModal(networkDiv, visNetwork) {
            if (modalInstalled) return true;
            if (!visNetwork || typeof visNetwork.on !== 'function') return false;
            modalInstalled = true;

            const backdrop = document.createElement('div');
            backdrop.id = 'collab-modal-backdrop';
            backdrop.className = 'collab-modal-backdrop';
            backdrop.innerHTML = modalMarkup();
            networkDiv.appendChild(backdrop);

            function field(name) {
                return backdrop.querySelector('[data-field="' + name + '"]');
            }

            function openModal(details) {
                const value = details || {};
                if (field('mat')) field('mat').value = value.mat || '';
                if (field('nome')) field('nome').value = value.nome || '';
                if (field('cargo')) field('cargo').value = value.cargo || '';
                if (field('setor')) field('setor').value = value.setor || '';
                if (field('subsetor')) field('subsetor').value = value.subsetor || '';
                if (field('supersetor')) field('supersetor').value = value.supersetor || '';
                if (field('lider')) field('lider').value = value.lider || '';
                if (field('posicao')) field('posicao').value = value.posicao || '';
                if (field('span')) field('span').value = String(value.span || 0);
                backdrop.classList.add('is-open');
            }

            function closeModal() {
                backdrop.classList.remove('is-open');
            }

            backdrop.addEventListener('click', function(event) {
                if (event.target === backdrop || (event.target && event.target.dataset && event.target.dataset.action === 'close')) {
                    closeModal();
                }
            });

            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') closeModal();
            });

            visNetwork.on('click', function(params) {
                const nodeId = params.nodes && params.nodes[0] ? String(params.nodes[0]) : '';
                if (!nodeId || nodeId.startsWith('__bend_')) return;
                const ds = getNodesDataset();
                const node = ds && ds.get(nodeId);
                if (!node || !node.collaborator) return;
                openModal(node.collaborator);
            });

            return true;
        }

        function setupContainers() {
            const visNetwork = getVisNetwork();
            const networkDiv = document.getElementById('mynetwork');
            if (!visNetwork || !networkDiv) return false;
            networkDiv.style.position = 'relative';
            bindNetworkEvents(visNetwork);
            if (!ensureDetailsModal(networkDiv, visNetwork)) return false;
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
    
    st.components.v1.html(html_content, height=height, scrolling=True)


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


def main():
    render_brand_header()

    path = "organograma.csv"
    setores_path = "setores.csv"
    supersetores_path = "supersetor.csv"
    subsetores_path = "subsetor.csv"
    
    try:
        df = load_data(path)
    except Exception as exc:
        st.error(f"Erro ao carregar {path}: {exc}")
        return

    try:
        setores_df = load_setores(setores_path)
    except Exception as exc:
        st.warning(f"Nao foi possivel carregar {setores_path}: {exc}")
        setores_df = pd.DataFrame(columns=["SETOR", "LIDERMAT"])
    
    try:
        supersetores_df = load_supersetores(supersetores_path)
    except Exception as exc:
        st.warning(f"Nao foi possivel carregar {supersetores_path}: {exc}")
        supersetores_df = pd.DataFrame(columns=["SUPERSETOR", "SETORFILHO", "LIDERMAT"])
    
    try:
        subsetores_df = load_subsetores(subsetores_path)
    except Exception as exc:
        st.warning(f"Nao foi possivel carregar {subsetores_path}: {exc}")
        subsetores_df = pd.DataFrame(columns=["SUBSETOR", "SETORPAI", "LIDERMAT"])

    posicoes = sorted([p for p in df["POSICAO"].dropna().unique() if p])
    setores = sorted([s for s in setores_df["SETOR"].dropna().unique() if s]) if not setores_df.empty else []

    if "sidebar_view" not in st.session_state:
        st.session_state["sidebar_view"] = "none"
    if "selected_setores" not in st.session_state:
        st.session_state["selected_setores"] = []
    if "selected_posicoes" not in st.session_state:
        st.session_state["selected_posicoes"] = posicoes
    if "search_text" not in st.session_state:
        st.session_state["search_text"] = ""
    if "selected_suggestion_idx" not in st.session_state:
        st.session_state["selected_suggestion_idx"] = 0

    sidebar_view = str(st.session_state.get("sidebar_view", "none"))
    if sidebar_view in {"ranking", "suggestions"}:
        request_sidebar_open()

    _, top_right = st.columns([8, 2])
    with top_right:
        horizontal_view = st.toggle("Modo horizontal", value=False)

    with st.container(border=True):
        st.markdown('<p class="filter-card-title">Filtros</p>', unsafe_allow_html=True)
        filter_col1, filter_col2, filter_col3 = st.columns([1.2, 1.25, 1.55])
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
        with filter_col3:
            search = st.text_input("Buscar por nome, cargo ou MAT", key="search_text")

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

    action_col1, action_col2, _ = st.columns([1.35, 1.7, 4.5])
    with action_col1:
        if st.button("Mostrar ranking de span", use_container_width=True):
            st.session_state["sidebar_view"] = "ranking"
            st.rerun()
    with action_col2:
        if st.button("Mostrar sugestoes de split/merge", use_container_width=True):
            st.session_state["sidebar_view"] = "suggestions"
            st.rerun()

    filtered, edge_count, highlighted_ids = build_graph(
        df,
        selected_posicoes,
        search,
        setores_df=setores_df,
        selected_setores=selected_setores,
    )
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
            render_pyvis(net_current, containers=containers_current, height=520)
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
            render_pyvis(net_proposed, containers=containers_proposed, height=520)

    st.subheader("Visualizacao")
    net, containers = build_pyvis_network(
        filtered,
        direction=direction,
        highlighted_ids=highlighted_ids,
        editor_df=df,
        setores_df=setores_df,
        supersetores_df=supersetores_df,
        subsetores_df=subsetores_df,
    )
    render_pyvis(net, containers=containers)

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

