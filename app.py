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
    net = Network(height="760px", width="100%", directed=True, notebook=False)

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

    def place(node_id: str) -> None:
        nonlocal cursor
        kids = children.get(node_id, [])
        if not kids:
            slot[node_id] = cursor
            cursor += 1.0
            return
        first_cursor = cursor
        for child in kids:
            place(child)
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
        sibling_gap = 360

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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        net.write_html(f.name)
        html_path = Path(f.name)

    html_content = html_path.read_text(encoding="utf-8")
    container_json = json.dumps(containers or {}, ensure_ascii=False).replace("</", "<\\/")
    editor_json = json.dumps(getattr(net, "org_editor_data", {}), ensure_ascii=False).replace("</", "<\\/")
    initial_scale_json = json.dumps(initial_scale)
    
    # Adicionar CSS e JavaScript customizados para renderizar containers
    container_styles = """
    <style>
    .network-container-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 5;
    }
    
    .container-svg {
        width: 100%;
        height: 100%;
        position: absolute;
        top: 0;
        left: 0;
    }
    
    .container-rect-supersetor {
        fill: rgba(20, 49, 94, 0.04);
        stroke: rgba(20, 49, 94, 0.25);
        stroke-width: 2;
        stroke-dasharray: 5,5;
    }
    
    .container-rect-setor {
        fill: rgba(47, 214, 139, 0.08);
        stroke: rgba(47, 214, 139, 0.6);
        stroke-width: 2;
    }
    
    .container-rect-subsetor {
        fill: transparent;
        stroke: rgba(20, 49, 94, 0.35);
        stroke-width: 1.5;
        stroke-dasharray: 3,3;
    }
    
    .container-label {
        font-size: 11px;
        font-weight: 700;
        fill: #14315E;
        font-family: Arial, sans-serif;
        pointer-events: none;
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
        const containerData = """ + container_json + """;
        const editorData = """ + editor_json + """;
        const initialScale = """ + initial_scale_json + """;
        let redrawHandle = null;
        let eventsBound = false;
        let initialViewApplied = false;
        let modalInstalled = false;
        let currentModalId = null;
        const storageKey = 'organograma_colaborador_changes_v1';
        const undoStack = [];

        function getVisNetwork() {
            if (typeof network !== 'undefined' && network && typeof network.canvasToDOM === 'function') {
                return network;
            }
            if (window.network && typeof window.network.canvasToDOM === 'function') {
                return window.network;
            }
            return null;
        }

        function scheduleContainers() {
            if (redrawHandle) {
                window.cancelAnimationFrame(redrawHandle);
            }
            redrawHandle = window.requestAnimationFrame(setupContainers);
        }

        function bindNetworkEvents(visNetwork) {
            if (eventsBound || !visNetwork || typeof visNetwork.on !== 'function') return;
            eventsBound = true;
            ['afterDrawing', 'zoom', 'dragEnd', 'animationFinished', 'stabilized', 'resize'].forEach(eventName => {
                visNetwork.on(eventName, scheduleContainers);
            });
            window.addEventListener('resize', scheduleContainers);
        }

        function getContainerNodeIds() {
            const ids = new Set();
            Object.values(buildCurrentContainerData() || {}).forEach(groups => {
                Object.values(groups || {}).forEach(nodes => {
                    (nodes || []).forEach(node => {
                        if (node && node.id && !String(node.id).startsWith('__bend_')) {
                            ids.add(node.id);
                        }
                    });
                });
            });
            return Array.from(ids);
        }

        function buildCurrentContainerData() {
            const data = { supersetor: {}, setor: {}, subsetor: {} };
            realGraphNodes().forEach(node => {
                const details = node.collaborator || {};
                const item = {
                    id: node.id,
                    x: Number(node.x) || 0,
                    y: Number(node.y) || 0,
                    size: Number(node.size) || 22
                };
                const supersetor = details.supersetor || '';
                if (supersetor) {
                    if (!data.supersetor[supersetor]) data.supersetor[supersetor] = [];
                    data.supersetor[supersetor].push(item);
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

        function applyInitialView(visNetwork) {
            if (initialViewApplied || !Number.isFinite(initialScale) || initialScale <= 0) return;
            initialViewApplied = true;
            window.setTimeout(function() {
                const nodeIds = getContainerNodeIds();
                if (!nodeIds.length || typeof visNetwork.getPositions !== 'function') return;
                const positions = visNetwork.getPositions(nodeIds);
                let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
                Object.values(positions || {}).forEach(pos => {
                    if (!pos || !Number.isFinite(pos.x) || !Number.isFinite(pos.y)) return;
                    minX = Math.min(minX, pos.x);
                    maxX = Math.max(maxX, pos.x);
                    minY = Math.min(minY, pos.y);
                    maxY = Math.max(maxY, pos.y);
                });
                if (!Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) return;
                visNetwork.moveTo({
                    position: { x: (minX + maxX) / 2, y: (minY + maxY) / 2 },
                    scale: initialScale,
                    animation: false
                });
                scheduleContainers();
            }, 80);
        }

        function getNodesDataset() {
            return typeof nodes !== 'undefined' ? nodes : null;
        }

        function getEdgesDataset() {
            return typeof edges !== 'undefined' ? edges : null;
        }

        function loadEditState() {
            try {
                const raw = window.localStorage.getItem(storageKey);
                if (!raw) return { edits: {}, deleted: {} };
                const parsed = JSON.parse(raw);
                return {
                    edits: parsed.edits || {},
                    deleted: parsed.deleted || {}
                };
            } catch (err) {
                return { edits: {}, deleted: {} };
            }
        }

        function saveEditState(state) {
            window.localStorage.setItem(storageKey, JSON.stringify(state));
        }

        function optionMarkup(values, includeBlank) {
            const options = includeBlank ? [''] : [];
            (values || []).forEach(value => {
                if (value && !options.includes(value)) options.push(value);
            });
            return options.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value || '')}</option>`).join('');
        }

        function escapeHtml(value) {
            return String(value || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function subsetorKey(setor, subsetor) {
            return `${setor || ''}||${subsetor || ''}`;
        }

        function resolveLeader(setor, subsetor) {
            const subsetorLeader = subsetor ? editorData.lideresSubsetor?.[subsetorKey(setor, subsetor)] : null;
            if (subsetorLeader && subsetorLeader.nome) return subsetorLeader;
            return editorData.lideresSetor?.[setor] || { mat: '', nome: '' };
        }

        function shortText(value, limit) {
            const text = String(value || '').trim();
            if (text.length <= limit) return text;
            return text.slice(0, Math.max(0, limit - 3)).trimEnd() + '...';
        }

        function buildCollaboratorLabel(details) {
            let label = `${shortText(details.nome, 24)}\n${shortText(details.cargo, 26)}`;
            if (details.span && Number(details.span) > 0) {
                label += `\nSpan: ${details.span}`;
            }
            return label;
        }

        function sortText(value) {
            return String(value || '').trim().toLocaleLowerCase('pt-BR');
        }

        function positionRankFromDetails(details) {
            const posicao = sortText(details?.posicao || '');
            if (posicao.includes('estrat')) return 0;
            if (posicao.includes('tat') || posicao.includes('tát')) return 1;
            if (posicao.includes('operacional')) return 2;
            return 1;
        }

        function nodeSortKey(node) {
            const details = node.collaborator || {};
            const subsetores = editorData.subsetoresPorSetor?.[details.setor] || [];
            const subsetorIndex = details.subsetor ? subsetores.indexOf(details.subsetor) : -1;
            const subsetorGroup = !details.subsetor ? 0 : subsetorIndex >= 0 ? 1 : 2;
            return [
                sortText(details.setor),
                subsetorGroup,
                subsetorIndex >= 0 ? subsetorIndex : 999999,
                sortText(details.subsetor),
                positionRankFromDetails(details),
                sortText(details.nome),
                sortText(details.cargo),
                String(node.id)
            ];
        }

        function compareSortKey(a, b) {
            const ak = Array.isArray(a) ? a : nodeSortKey(a);
            const bk = Array.isArray(b) ? b : nodeSortKey(b);
            for (let i = 0; i < Math.max(ak.length, bk.length); i += 1) {
                if (ak[i] < bk[i]) return -1;
                if (ak[i] > bk[i]) return 1;
            }
            return 0;
        }

        function realGraphNodes() {
            const ds = getNodesDataset();
            if (!ds) return [];
            return ds.get().filter(node => !String(node.id).startsWith('__bend_') && node.collaborator);
        }

        function clone(value) {
            return JSON.parse(JSON.stringify(value));
        }

        function getNodeDetails(nodeId) {
            const ds = getNodesDataset();
            if (!ds) return null;
            const node = ds.get(nodeId);
            if (!node || !node.collaborator) return null;
            return clone(node.collaborator);
        }

        function applyDetailsToNode(nodeId, details) {
            const ds = getNodesDataset();
            if (!ds) return;
            const node = ds.get(nodeId);
            if (!node) return;
            const nextDetails = Object.assign({}, node.collaborator || {}, details || {});
            const leader = resolveLeader(nextDetails.setor || '', nextDetails.subsetor || '');
            nextDetails.lider = leader.nome || '';
            nextDetails.liderMat = leader.mat || '';
            nextDetails.supersetor = editorData.supersetorPorSetor?.[nextDetails.setor] || nextDetails.supersetor || '';
            ds.update({
                id: nodeId,
                label: buildCollaboratorLabel(nextDetails),
                title: 'Clique para ver detalhes',
                collaborator: nextDetails
            });
        }

        function layoutChildLevelGap(parent, child, childrenByParent) {
            const siblings = childrenByParent.get(parent.id) || [];
            const ranks = new Set(siblings.map(node => positionRankFromDetails(node.collaborator)));
            if (ranks.has(1) && ranks.has(2) && positionRankFromDetails(child.collaborator) === 2) {
                return 2;
            }
            return 1;
        }

        function rebuildGraphLayout() {
            const ds = getNodesDataset();
            const edgeDs = getEdgesDataset();
            if (!ds || !edgeDs) return;

            const graphNodes = realGraphNodes();
            const byId = new Map(graphNodes.map(node => [String(node.id), node]));
            const childrenByParent = new Map();
            const parentByChild = new Map();

            graphNodes.forEach(node => {
                const leaderId = String(node.collaborator?.liderMat || '');
                if (leaderId && leaderId !== String(node.id) && byId.has(leaderId)) {
                    parentByChild.set(String(node.id), leaderId);
                    if (!childrenByParent.has(leaderId)) childrenByParent.set(leaderId, []);
                    childrenByParent.get(leaderId).push(node);
                }
            });

            childrenByParent.forEach(list => list.sort(compareSortKey));
            graphNodes.forEach(node => {
                const nodeId = String(node.id);
                const details = Object.assign({}, node.collaborator || {});
                details.span = (childrenByParent.get(nodeId) || []).length;
                ds.update({
                    id: node.id,
                    collaborator: details,
                    label: buildCollaboratorLabel(details),
                    title: 'Clique para ver detalhes'
                });
                node.collaborator = details;
            });
            const roots = graphNodes
                .filter(node => !parentByChild.has(String(node.id)))
                .sort((a, b) => (String(a.id) === '1979' ? -1 : String(b.id) === '1979' ? 1 : compareSortKey(a, b)));

            const depth = new Map();
            const queue = roots.map(root => ({ node: root, depth: 0 }));
            while (queue.length) {
                const item = queue.shift();
                const nodeId = String(item.node.id);
                if (depth.has(nodeId) && depth.get(nodeId) <= item.depth) continue;
                depth.set(nodeId, item.depth);
                (childrenByParent.get(nodeId) || []).forEach(child => {
                    queue.push({ node: child, depth: item.depth + layoutChildLevelGap(item.node, child, childrenByParent) });
                });
            }

            let maxDepth = Math.max(0, ...Array.from(depth.values()));
            graphNodes.sort(compareSortKey).forEach(node => {
                const nodeId = String(node.id);
                if (!depth.has(nodeId)) {
                    maxDepth += 1;
                    depth.set(nodeId, maxDepth);
                }
            });

            const slot = new Map();
            let cursor = 0;
            function place(node) {
                const nodeId = String(node.id);
                const kids = childrenByParent.get(nodeId) || [];
                if (!kids.length) {
                    slot.set(nodeId, cursor);
                    cursor += 1;
                    return;
                }
                const first = cursor;
                kids.forEach(place);
                slot.set(nodeId, (first + (cursor - 1)) / 2);
            }

            roots.forEach((root, index) => {
                place(root);
                if (index < roots.length - 1) cursor += 1.6;
            });
            graphNodes.sort(compareSortKey).forEach(node => {
                const nodeId = String(node.id);
                if (!slot.has(nodeId)) {
                    slot.set(nodeId, cursor);
                    cursor += 1;
                }
            });

            const isHorizontal = editorData.direction === 'LR';
            const levelGap = isHorizontal ? 820 : 340;
            const siblingGap = isHorizontal ? 220 : 360;
            const positions = {};
            graphNodes.forEach(node => {
                const nodeId = String(node.id);
                const branchAxis = slot.get(nodeId) * siblingGap;
                const hierarchyAxis = depth.get(nodeId) * levelGap;
                positions[nodeId] = isHorizontal
                    ? { x: hierarchyAxis, y: branchAxis }
                    : { x: branchAxis, y: hierarchyAxis };
            });

            ds.get()
                .filter(node => String(node.id).startsWith('__bend_'))
                .forEach(node => ds.remove(node.id));
            const existingEdgeIds = typeof edgeDs.getIds === 'function'
                ? edgeDs.getIds()
                : edgeDs.get().map(edge => edge.id);
            edgeDs.remove(existingEdgeIds);

            graphNodes.forEach(node => {
                const pos = positions[String(node.id)] || { x: 0, y: 0 };
                ds.update({ id: node.id, x: pos.x, y: pos.y, fixed: { x: true, y: true }, physics: false });
            });

            let bendSeq = 0;
            function childLevelGap(parent, child) {
                return layoutChildLevelGap(parent, child, childrenByParent);
            }
            function childSubsetorKey(node) {
                const details = node.collaborator || {};
                return details.subsetor ? `${details.setor || ''}||${details.subsetor}` : '';
            }
            function sharesTacticalSubsetorBranch(parent, child) {
                if (positionRankFromDetails(child.collaborator) !== 2) return false;
                const childKey = childSubsetorKey(child);
                if (!childKey) return false;
                const siblings = childrenByParent.get(String(parent.id)) || [];
                const ranks = new Set(
                    siblings
                        .filter(sibling => childSubsetorKey(sibling) === childKey)
                        .map(sibling => positionRankFromDetails(sibling.collaborator))
                );
                return ranks.has(1) && ranks.has(2);
            }
            function branchOffset(parent, child, distance) {
                const siblings = childrenByParent.get(String(parent.id)) || [];
                const ranks = new Set(siblings.map(node => positionRankFromDetails(node.collaborator)));
                if (ranks.has(1) && ranks.has(2)) {
                    const rank = positionRankFromDetails(child.collaborator);
                    if (rank === 1) return Math.min(Math.max(90, distance * 0.35), Math.max(90, distance - 80));
                    if (rank === 2) {
                        if (sharesTacticalSubsetorBranch(parent, child)) {
                            const tacticalDistance = distance / Math.max(1, childLevelGap(parent, child));
                            return Math.min(Math.max(90, tacticalDistance * 0.35), Math.max(90, tacticalDistance - 80));
                        }
                        return Math.max(90, distance - Math.min(130, Math.max(90, distance * 0.35)));
                    }
                }
                return Math.max(90, distance * 0.5);
            }

            childrenByParent.forEach((kids, parentId) => {
                const parent = byId.get(String(parentId));
                if (!parent) return;
                kids.forEach(child => {
                    const parentPos = positions[String(parent.id)];
                    const childPos = positions[String(child.id)];
                    if (!parentPos || !childPos) return;

                    let b1Pos;
                    let b2Pos;
                    if (isHorizontal) {
                        let midX = parentPos.x + branchOffset(parent, child, childPos.x - parentPos.x);
                        if (midX > childPos.x - 30) midX = (parentPos.x + childPos.x) / 2;
                        b1Pos = { x: midX, y: parentPos.y };
                        b2Pos = { x: midX, y: childPos.y };
                    } else {
                        let midY = parentPos.y + branchOffset(parent, child, childPos.y - parentPos.y);
                        if (midY > childPos.y - 20) midY = (parentPos.y + childPos.y) / 2;
                        b1Pos = { x: parentPos.x, y: midY };
                        b2Pos = { x: childPos.x, y: midY };
                    }

                    const b1 = `__bend_live_${bendSeq}_1`;
                    const b2 = `__bend_live_${bendSeq}_2`;
                    bendSeq += 1;
                    const bendStyle = {
                        size: 0.1,
                        shape: 'dot',
                        label: '',
                        title: '',
                        font: { size: 1, color: 'rgba(0,0,0,0)' },
                        color: { background: 'rgba(0,0,0,0)', border: 'rgba(0,0,0,0)' },
                        borderWidth: 0,
                        fixed: { x: true, y: true },
                        physics: false
                    };
                    ds.add([
                        Object.assign({ id: b1, x: b1Pos.x, y: b1Pos.y }, bendStyle),
                        Object.assign({ id: b2, x: b2Pos.x, y: b2Pos.y }, bendStyle)
                    ]);
                    edgeDs.add([
                        { from: parent.id, to: b1, arrows: '', color: '#7f95b5', width: 2 },
                        { from: b1, to: b2, arrows: '', color: '#7f95b5', width: 2 },
                        { from: b2, to: child.id, arrows: 'to', color: '#7f95b5', width: 2 }
                    ]);
                });
            });

            const visNetwork = getVisNetwork();
            if (visNetwork && typeof visNetwork.redraw === 'function') visNetwork.redraw();
            setupContainers();
        }

        function collectNodeAndBends(nodeId) {
            const edgeDs = getEdgesDataset();
            const nodesToRemove = new Set([nodeId]);
            if (!edgeDs) return nodesToRemove;
            let changed = true;
            while (changed) {
                changed = false;
                edgeDs.get().forEach(edge => {
                    const from = String(edge.from);
                    const to = String(edge.to);
                    if (nodesToRemove.has(from) && to.startsWith('__bend_') && !nodesToRemove.has(to)) {
                        nodesToRemove.add(to);
                        changed = true;
                    }
                    if (nodesToRemove.has(to) && from.startsWith('__bend_') && !nodesToRemove.has(from)) {
                        nodesToRemove.add(from);
                        changed = true;
                    }
                });
            }
            return nodesToRemove;
        }

        function removeNodeAndBends(nodeId) {
            const ds = getNodesDataset();
            const edgeDs = getEdgesDataset();
            if (!ds || !edgeDs || !ds.get(nodeId)) return { nodes: [], edges: [] };
            const nodesToRemove = collectNodeAndBends(nodeId);
            const removedNodes = ds.get(Array.from(nodesToRemove));
            const removedEdges = edgeDs.get({ filter: edge => nodesToRemove.has(String(edge.from)) || nodesToRemove.has(String(edge.to)) });
            edgeDs.remove(removedEdges.map(edge => edge.id));
            ds.remove(Array.from(nodesToRemove));
            return { nodes: removedNodes, edges: removedEdges };
        }

        function applyPersistedState() {
            const ds = getNodesDataset();
            const edgeDs = getEdgesDataset();
            if (!ds || !edgeDs) return;
            const state = loadEditState();
            Object.keys(state.edits || {}).forEach(nodeId => {
                if (ds.get(nodeId)) {
                    applyDetailsToNode(nodeId, state.edits[nodeId]);
                }
            });
            Object.keys(state.deleted || {}).forEach(nodeId => {
                if (ds.get(nodeId)) {
                    removeNodeAndBends(nodeId);
                }
            });
            rebuildGraphLayout();
        }

        function modalMarkup() {
            return `
                <div class="collab-modal" role="dialog" aria-modal="true">
                    <div class="collab-modal-header">
                        <p class="collab-modal-title">Colaborador</p>
                        <button type="button" class="collab-button icon" data-action="close" aria-label="Fechar">x</button>
                    </div>
                    <div class="collab-modal-body" style="display:none">
                        <div class="collab-field"><label>Matrícula</label><input data-field="mat" readonly></div>
                        <div class="collab-field"><label>Nome</label><input data-field="nome"></div>
                        <div class="collab-field"><label>Cargo</label><input data-field="cargo"></div>
                        <div class="collab-field"><label>Setor</label><input data-field="setor"></div>
                        <div class="collab-field"><label>Subsetor</label><input data-field="subsetor"></div>
                        <div class="collab-field"><label>Líder</label><input data-field="lider"></div>
                        <div class="collab-field"><label>Posição</label><select data-field="posicao">
                            <option value="ESTRATÉGICO">ESTRATÉGICO</option>
                            <option value="TÁTICO">TÁTICO</option>
                            <option value="OPERACIONAL">OPERACIONAL</option>
                        </select></div>
                    </div>
                    <div class="collab-modal-body">
                        <div class="collab-field"><label>Matricula</label><input data-field="mat" readonly></div>
                        <div class="collab-field"><label>Nome</label><input data-field="nome" readonly></div>
                        <div class="collab-field"><label>Cargo</label><select data-field="cargo">${optionMarkup(editorData.cargos || [], true)}</select></div>
                        <div class="collab-field"><label>Posicao</label><select data-field="posicao">${optionMarkup(editorData.posicoes || [], true)}</select></div>
                        <div class="collab-field"><label>Setor</label><select data-field="setor">${optionMarkup(editorData.setores || [], true)}</select></div>
                        <div class="collab-field"><label>Subsetor</label><select data-field="subsetor"></select></div>
                        <div class="collab-field full"><label>Lider</label><input data-field="lider" readonly></div>
                        <div class="collab-modal-message" data-role="message"></div>
                    </div>
                    <div class="collab-modal-footer">
                        <button type="button" class="collab-button danger" data-action="delete">Deletar</button>
                        <button type="button" class="collab-button" data-action="close">Cancelar</button>
                        <button type="button" class="collab-button primary" data-action="save">Salvar</button>
                    </div>
                </div>
            `;
        }

        function ensureCollaboratorModal(networkDiv, visNetwork) {
            if (modalInstalled) return;
            modalInstalled = true;
            const ds = getNodesDataset();
            const edgeDs = getEdgesDataset();
            if (!ds || !edgeDs) return;

            const backdrop = document.createElement('div');
            backdrop.id = 'collab-modal-backdrop';
            backdrop.className = 'collab-modal-backdrop';
            backdrop.innerHTML = modalMarkup();
            networkDiv.appendChild(backdrop);

            function field(name) {
                const matches = Array.from(backdrop.querySelectorAll(`[data-field="${name}"]`));
                return matches[matches.length - 1] || null;
            }

            function setOpen(open) {
                backdrop.classList.toggle('is-open', open);
            }

            function message(text) {
                const el = backdrop.querySelector('[data-role="message"]');
                if (el) el.textContent = text || '';
            }

            function updateSubsetorOptions(selectedValue) {
                const setor = field('setor')?.value || '';
                const subsetorEl = field('subsetor');
                if (!subsetorEl) return;
                subsetorEl.innerHTML = optionMarkup(editorData.subsetoresPorSetor?.[setor] || [], true);
                subsetorEl.value = selectedValue && Array.from(subsetorEl.options).some(opt => opt.value === selectedValue)
                    ? selectedValue
                    : '';
            }

            function updateLeader() {
                const leader = resolveLeader(field('setor')?.value || '', field('subsetor')?.value || '');
                const leaderEl = field('lider');
                if (leaderEl) leaderEl.value = leader.nome || '';
                return leader;
            }

            function updatePositionFromCargo() {
                const cargo = field('cargo')?.value || '';
                const posicao = editorData.posicaoPorCargo?.[cargo] || '';
                const posicaoEl = field('posicao');
                if (posicaoEl) posicaoEl.value = posicao;
            }

            function validateForm() {
                const required = ['mat', 'nome', 'cargo', 'posicao', 'setor', 'lider'];
                const missing = required.filter(name => !(field(name)?.value || '').trim());
                if (missing.length) {
                    message('Preencha todos os campos obrigatorios antes de salvar.');
                    return false;
                }
                message('');
                return true;
            }

            function fillForm(details) {
                updateSubsetorOptions(details.subsetor || '');
                ['mat', 'nome', 'cargo', 'setor', 'subsetor', 'lider', 'posicao'].forEach(name => {
                    const el = field(name);
                    if (el) el.value = details[name] || '';
                });
                updateSubsetorOptions(details.subsetor || '');
                updateLeader();
                message('');
            }

            function collectForm() {
                const current = getNodeDetails(currentModalId) || {};
                ['mat', 'nome', 'cargo', 'setor', 'subsetor', 'lider', 'posicao'].forEach(name => {
                    const el = field(name);
                    if (el) current[name] = el.value;
                });
            const leader = resolveLeader(current.setor || '', current.subsetor || '');
            current.lider = leader.nome || '';
            current.liderMat = leader.mat || '';
            current.supersetor = editorData.supersetorPorSetor?.[current.setor] || current.supersetor || '';
            return current;
        }

            function openModal(nodeId) {
                const details = getNodeDetails(nodeId);
                if (!details) return;
                currentModalId = nodeId;
                fillForm(details);
                setOpen(true);
            }

            function closeModal() {
                setOpen(false);
                currentModalId = null;
            }

            function saveCurrent() {
                if (!currentModalId) return;
                updateLeader();
                if (!validateForm()) return;
                const before = getNodeDetails(currentModalId);
                const after = collectForm();
                undoStack.push({ type: 'edit', id: currentModalId, before, after });
                applyDetailsToNode(currentModalId, after);
                rebuildGraphLayout();
                const state = loadEditState();
                state.edits[currentModalId] = after;
                delete state.deleted[currentModalId];
                saveEditState(state);
                closeModal();
                setupContainers();
            }

            function deleteCurrent() {
                if (!currentModalId) return;
                const nodeId = currentModalId;
                const node = ds.get(nodeId);
                if (!node) return;
                if (!window.confirm('Deletar este colaborador do organograma?')) return;

                const removed = removeNodeAndBends(nodeId);
                undoStack.push({ type: 'delete', id: nodeId, nodes: clone(removed.nodes), edges: clone(removed.edges) });
                const state = loadEditState();
                state.deleted[nodeId] = true;
                delete state.edits[nodeId];
                saveEditState(state);
                closeModal();
                setupContainers();
            }

            function undoLastChange() {
                const item = undoStack.pop();
                if (!item) return;
                const state = loadEditState();
                if (item.type === 'edit') {
                    applyDetailsToNode(item.id, item.before);
                    rebuildGraphLayout();
                    state.edits[item.id] = item.before;
                    delete state.deleted[item.id];
                } else if (item.type === 'delete') {
                    ds.update(item.nodes || []);
                    edgeDs.update(item.edges);
                    delete state.deleted[item.id];
                    const restoredNode = (item.nodes || []).find(node => String(node.id) === String(item.id));
                    if (restoredNode && restoredNode.collaborator) {
                        state.edits[item.id] = restoredNode.collaborator;
                    }
                    rebuildGraphLayout();
                }
                saveEditState(state);
                closeModal();
                setupContainers();
            }

            backdrop.addEventListener('click', event => {
                if (event.target === backdrop || event.target.dataset.action === 'close') closeModal();
                if (event.target.dataset.action === 'save') saveCurrent();
                if (event.target.dataset.action === 'delete') deleteCurrent();
            });

            const cargoEl = field('cargo');
            const setorEl = field('setor');
            const subsetorEl = field('subsetor');
            const posicaoEl = field('posicao');
            if (cargoEl) cargoEl.addEventListener('change', () => {
                updatePositionFromCargo();
                validateForm();
            });
            if (setorEl) setorEl.addEventListener('change', () => {
                updateSubsetorOptions('');
                updateLeader();
                validateForm();
            });
            if (subsetorEl) subsetorEl.addEventListener('change', () => {
                updateLeader();
                validateForm();
            });
            if (posicaoEl) posicaoEl.addEventListener('change', validateForm);

            document.addEventListener('keydown', event => {
                if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
                    event.preventDefault();
                    undoLastChange();
                }
                if (event.key === 'Escape') closeModal();
            });

            visNetwork.on('click', params => {
                const nodeId = params.nodes && params.nodes[0] ? String(params.nodes[0]) : '';
                if (!nodeId || nodeId.startsWith('__bend_')) return;
                openModal(nodeId);
            });

            applyPersistedState();
            setupContainers();
        }
        
        function setupContainers() {
            const visNetwork = getVisNetwork();
            const networkDiv = document.getElementById('mynetwork') || document.querySelector('canvas')?.parentElement;
            if (!visNetwork || !networkDiv) return false;
            
            // Criar SVG overlay para containers
            let overlayDiv = document.getElementById('container-overlay');
            if (!overlayDiv) {
                overlayDiv = document.createElement('div');
                overlayDiv.id = 'container-overlay';
                overlayDiv.className = 'network-container-overlay';
                networkDiv.style.position = 'relative';
                networkDiv.appendChild(overlayDiv);
            }
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            const bounds = networkDiv.getBoundingClientRect();
            const width = Math.max(1, bounds.width || networkDiv.clientWidth || 1);
            const height = Math.max(1, bounds.height || networkDiv.clientHeight || 1);
            svg.setAttribute('class', 'container-svg');
            svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
            svg.setAttribute('width', width);
            svg.setAttribute('height', height);
            
            // Desenhar containers
            drawContainers(svg, buildCurrentContainerData(), visNetwork);
            
            overlayDiv.innerHTML = '';
            overlayDiv.appendChild(svg);
            bindNetworkEvents(visNetwork);
            ensureCollaboratorModal(networkDiv, visNetwork);
            applyInitialView(visNetwork);
            return true;
        }
        
        function drawContainers(svg, data, visNetwork) {
            if (!data || !visNetwork) return;
            
            // Desenhar cada tipo de container
            ['supersetor', 'setor', 'subsetor'].forEach(type => {
                if (data[type]) {
                    Object.entries(data[type]).forEach(([containerName, nodes]) => {
                        if (nodes && nodes.length > 0) {
                            drawContainer(svg, type, containerName, nodes, visNetwork);
                        }
                    });
                }
            });
        }
        
        function nodeDomBox(visNetwork, node) {
            if (!node || !node.id) return null;
            const ds = getNodesDataset();
            if (ds && !ds.get(node.id)) return null;

            try {
                if (typeof visNetwork.getBoundingBox === 'function') {
                    const box = visNetwork.getBoundingBox(node.id);
                    if (
                        box &&
                        Number.isFinite(box.left) &&
                        Number.isFinite(box.right) &&
                        Number.isFinite(box.top) &&
                        Number.isFinite(box.bottom)
                    ) {
                        const topLeft = visNetwork.canvasToDOM({ x: box.left, y: box.top });
                        const bottomRight = visNetwork.canvasToDOM({ x: box.right, y: box.bottom });
                        return {
                            left: Math.min(topLeft.x, bottomRight.x),
                            right: Math.max(topLeft.x, bottomRight.x),
                            top: Math.min(topLeft.y, bottomRight.y),
                            bottom: Math.max(topLeft.y, bottomRight.y)
                        };
                    }
                }
            } catch (err) {
                // Fall through to the coordinate fallback below.
            }

            if (!Number.isFinite(Number(node.x)) || !Number.isFinite(Number(node.y))) return null;
            const center = visNetwork.canvasToDOM({ x: Number(node.x), y: Number(node.y) });
            const scale = typeof visNetwork.getScale === 'function' ? visNetwork.getScale() : 1;
            const radius = Math.max(18, (Number(node.size) || 22) * Math.max(scale, 0.2) * 1.8);
            return {
                left: center.x - radius,
                right: center.x + radius,
                top: center.y - radius,
                bottom: center.y + radius
            };
        }

        function drawContainer(svg, type, name, nodes, visNetwork) {
            if (!nodes || nodes.length === 0) return;
            
            // Calcular bounding box dos nós
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            let visibleNodes = 0;
            
            nodes.forEach(node => {
                const box = nodeDomBox(visNetwork, node);
                if (!box) return;
                minX = Math.min(minX, box.left);
                maxX = Math.max(maxX, box.right);
                minY = Math.min(minY, box.top);
                maxY = Math.max(maxY, box.bottom);
                visibleNodes += 1;
            });
            if (!visibleNodes || !Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) {
                return;
            }
            
            // Adicionar padding
            const paddingByType = { supersetor: 38, setor: 28, subsetor: 18 };
            const padding = paddingByType[type] || 20;
            minX -= padding;
            maxX += padding;
            minY -= padding;
            maxY += padding;
            
            // Desenhar retângulo com bordas arredondadas
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', minX);
            rect.setAttribute('y', minY);
            rect.setAttribute('width', maxX - minX);
            rect.setAttribute('height', maxY - minY);
            rect.setAttribute('rx', 8);
            rect.setAttribute('ry', 8);
            rect.setAttribute('class', `container-rect-${type}`);
            
            svg.appendChild(rect);
            
            // Adicionar etiqueta no canto superior esquerdo
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', minX + 10);
            label.setAttribute('y', minY + 16);
            label.setAttribute('class', 'container-label');
            label.textContent = name;
            
            svg.appendChild(label);
        }
        
        // Aguardar carregamento do vis.js
        const waitForNetwork = setInterval(function() {
            if (setupContainers()) {
                clearInterval(waitForNetwork);
            }
        }, 100);

        setTimeout(function() {
            clearInterval(waitForNetwork);
            setupContainers();
        }, 10000);
    })();
    </script>
    """
    
    # Inserir os estilos antes da tag de fechamento do head
    html_content = html_content.replace("</head>", f"{container_styles}</head>")
    
    st.components.v1.html(html_content, height=height, scrolling=True)
    html_path.unlink(missing_ok=True)


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
