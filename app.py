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

st.set_page_config(page_title="Organograma Interativo", page_icon=PAGE_ICON, layout="wide")

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


def build_pyvis_network(work: pd.DataFrame, direction: str = "UD", highlighted_ids: set[str] | None = None) -> Network:
    graph = nx.DiGraph()
    node_payload: dict[str, dict] = {}
    highlighted_ids = highlighted_ids or set()

    def short_text(value: str, limit: int) -> str:
        text = (value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    for _, row in work.iterrows():
        mat = row["MAT"]
        nome = row["NOME"] or "Sem nome"
        cargo = row["CARGO"] or "Sem cargo"
        posicao = row["POSICAO"] or "-"

        is_root = mat == "1979" or "glauber" in nome.lower()
        is_highlighted = mat in highlighted_ids

        if is_root:
            size = 34
        else:
            size = 22

        payload = {
            "label": f"{short_text(nome, 24)}\n{short_text(cargo, 26)}",
            "title": f"MAT: {mat}<br>Nome: {nome}<br>Cargo: {cargo}<br>Posicao: {posicao}",
            "is_root": is_root,
            "is_highlighted": is_highlighted,
            "size": size,
        }
        graph.add_node(mat, **payload)
        node_payload[mat] = payload

    id_set = set(work["MAT"].tolist())
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

    def sort_key(node_id: str) -> str:
        return graph.nodes[node_id].get("label", node_id)

    parent_of: dict[str, str] = {}
    for node in graph.nodes:
        preds = sorted(graph.predecessors(node), key=sort_key)
        if preds:
            parent_of[node] = preds[0]

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

    depth: dict[str, int] = {}
    queue = deque((root, 0) for root in roots)
    while queue:
        node, d = queue.popleft()
        if node in depth and depth[node] <= d:
            continue
        depth[node] = d
        for child in children.get(node, []):
            queue.append((child, d + 1))

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
            title_text = f"{title_text}<br>Liderados diretos: {span}"

        net.add_node(
            node_id,
            label=label_text,
            title=title_text,
            color=node_color,
            borderWidth=border_width,
            size=node_size,
            x=x,
            y=y,
            fixed={"x": True, "y": True},
            physics=False,
        )

    bend_seq = 0
    line_color = "#7f95b5"
    for parent, child in graph.edges:
        if parent not in positions or child not in positions:
            continue

        sx, sy = positions[parent]
        tx, ty = positions[child]

        if is_horizontal:
            mid_x = sx + max(120.0, (tx - sx) * 0.5)
            if mid_x > tx - 30:
                mid_x = (sx + tx) / 2
            b1_pos = (mid_x, sy)
            b2_pos = (mid_x, ty)
        else:
            mid_y = sy + max(90.0, (ty - sy) * 0.5)
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

    return net


def render_pyvis(net: Network, height: int = 780) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        net.write_html(f.name)
        html_path = Path(f.name)

    html_content = html_path.read_text(encoding="utf-8")
    st.components.v1.html(html_content, height=height, scrolling=True)
    html_path.unlink(missing_ok=True)


def main():
    render_brand_header()

    path = "organograma.csv"
    setores_path = "setores.csv"
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

    posicoes = sorted([p for p in df["POSICAO"].dropna().unique() if p])
    setores = sorted([s for s in setores_df["SETOR"].dropna().unique() if s]) if not setores_df.empty else []

    if "sidebar_view" not in st.session_state:
        st.session_state["sidebar_view"] = "filters"
    if "selected_setores" not in st.session_state:
        st.session_state["selected_setores"] = []
    if "selected_posicoes" not in st.session_state:
        st.session_state["selected_posicoes"] = posicoes
    if "search_text" not in st.session_state:
        st.session_state["search_text"] = ""
    if "selected_suggestion_idx" not in st.session_state:
        st.session_state["selected_suggestion_idx"] = 0

    sidebar_view = str(st.session_state.get("sidebar_view", "filters"))

    if sidebar_view == "filters":
        st.sidebar.header("Filtros")
        selected_setores = st.sidebar.multiselect(
            "Setor",
            options=setores,
            default=st.session_state.get("selected_setores", []),
            key="selected_setores",
            help="Mostra lider do setor, todos os liderados e o caminho de lideranca ate o CEO.",
        )
        selected_posicoes = st.sidebar.multiselect(
            "Posicao",
            options=posicoes,
            default=st.session_state.get("selected_posicoes", posicoes),
            key="selected_posicoes",
            help="Filtre por nivel/posicao no organograma (aplicado quando Setor nao estiver selecionado).",
        )
        search = st.sidebar.text_input("Buscar por nome, cargo ou MAT", key="search_text")

        if selected_setores and not setores_df.empty:
            sector_ids = get_sector_descendant_ids(df, setores_df, selected_setores)
            cargos_setor = sorted(
                [c for c in df[df["MAT"].isin(sector_ids)]["CARGO"].dropna().unique() if c]
            )
            st.sidebar.markdown("**Cargos existentes no(s) setor(es):**")
            if cargos_setor:
                st.sidebar.caption("\n".join(f"- {cargo}" for cargo in cargos_setor))
            else:
                st.sidebar.caption("Nenhum cargo encontrado para o(s) setor(es) selecionado(s).")

        if st.sidebar.button("Mostrar ranking de span", use_container_width=True):
            st.session_state["sidebar_view"] = "ranking"
            st.rerun()
        if st.sidebar.button("Mostrar sugestoes de split/merge", use_container_width=True):
            st.session_state["sidebar_view"] = "suggestions"
            st.rerun()
    elif sidebar_view == "ranking":
        st.sidebar.header("Ranking de Span")
        selected_setores = st.session_state.get("selected_setores", [])
        selected_posicoes = st.session_state.get("selected_posicoes", posicoes)
        search = st.session_state.get("search_text", "")
        if st.sidebar.button("Voltar para filtros", use_container_width=True):
            st.session_state["sidebar_view"] = "filters"
            st.rerun()
        if st.sidebar.button("Ir para sugestoes", use_container_width=True):
            st.session_state["sidebar_view"] = "suggestions"
            st.rerun()
    else:
        st.sidebar.header("Sugestoes")
        selected_setores = st.session_state.get("selected_setores", [])
        selected_posicoes = st.session_state.get("selected_posicoes", posicoes)
        search = st.session_state.get("search_text", "")
        if st.sidebar.button("Voltar para filtros", use_container_width=True):
            st.session_state["sidebar_view"] = "filters"
            st.rerun()
        if st.sidebar.button("Ir para ranking", use_container_width=True):
            st.session_state["sidebar_view"] = "ranking"
            st.rerun()

    _, top_right = st.columns([8, 2])
    with top_right:
        horizontal_view = st.toggle("Modo horizontal", value=False)

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
        st.write(
            {
                "Titulo": selected_suggestion.get("title", ""),
                "Resumo": selected_suggestion.get("summary", ""),
                "Tipo": selected_suggestion.get("kind", ""),
                "Impacto": int(selected_suggestion.get("impact", 0)),
            }
        )

        current_focus_ids = build_focus_scope(filtered, list(selected_suggestion.get("focus_ids", [])))
        current_focus = filtered[filtered["MAT"].isin(current_focus_ids)].copy()

        proposed = apply_reorg_suggestion(filtered, selected_suggestion)
        proposed_focus_ids = build_focus_scope(proposed, list(selected_suggestion.get("focus_ids", [])))
        proposed_focus = proposed[proposed["MAT"].isin(proposed_focus_ids)].copy()

        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**Como esta hoje (foco na area da mudanca)**")
            net_current = build_pyvis_network(current_focus, direction=direction, highlighted_ids=highlighted_ids)
            render_pyvis(net_current, height=520)
        with right_col:
            st.markdown("**Como ficaria com a sugestao aplicada**")
            net_proposed = build_pyvis_network(proposed_focus, direction=direction, highlighted_ids=highlighted_ids)
            render_pyvis(net_proposed, height=520)

    st.subheader("Visualizacao")
    net = build_pyvis_network(filtered, direction=direction, highlighted_ids=highlighted_ids)
    render_pyvis(net)

    st.caption(
        "Dica: use scroll para zoom, arraste o fundo para navegar e arraste nos para reorganizar localmente."
    )

    st.subheader("Detalhes")
    selected_node = st.selectbox(
        "Escolha uma pessoa para ver os detalhes",
        options=filtered["MAT"].tolist(),
        format_func=lambda x: (
            f"{x} - {filtered.loc[filtered['MAT'] == x, 'NOME'].iloc[0]}"
            if not filtered.loc[filtered["MAT"] == x].empty
            else x
        ),
    )

    person = df[df["MAT"] == selected_node]
    if not person.empty:
        row = person.iloc[0]
        st.write(
            {
                "MAT": row["MAT"],
                "NOME": row["NOME"],
                "CARGO": row["CARGO"],
                "LIDER": row["LIDER"],
                "POSICAO": row["POSICAO"],
            }
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
