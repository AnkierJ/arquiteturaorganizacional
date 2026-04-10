import tempfile
from pathlib import Path

import networkx as nx
import pandas as pd
import streamlit as st
from pyvis.network import Network


st.set_page_config(page_title="Organograma Interativo", layout="wide")
st.title("Organograma da Empresa")
st.caption("Visualizacao baseada no arquivo organograma.csv")

st.markdown(
    """
    <style>
    div[data-testid="stToggle"] label p {
        font-size: 0.85rem;
        color: #5f6368;
    }
    </style>
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


def build_graph(df: pd.DataFrame, selected_posicoes: list[str], search: str):
    work = df.copy()

    if selected_posicoes:
        work = work[work["POSICAO"].isin(selected_posicoes)]

    if search:
        s = search.lower().strip()
        mask = (
            work["NOME"].str.lower().str.contains(s)
            | work["CARGO"].str.lower().str.contains(s)
            | work["MAT"].str.lower().str.contains(s)
        )
        work = work[mask]

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

    return work, edge_count


def build_pyvis_network(work: pd.DataFrame, direction: str = "UD") -> Network:
    graph = nx.DiGraph()

    for _, row in work.iterrows():
        mat = row["MAT"]
        nome = row["NOME"] or "Sem nome"
        cargo = row["CARGO"] or "Sem cargo"
        posicao = row["POSICAO"] or "-"

        is_root = mat == "1979" or "glauber" in nome.lower()
        color = "#e63946" if is_root else "#457b9d"
        size = 34 if is_root else 22

        graph.add_node(
            mat,
            label=f"{nome[:26]}\\n{cargo[:32]}",
            title=f"MAT: {mat}<br>Nome: {nome}<br>Cargo: {cargo}<br>Posicao: {posicao}",
            color=color,
            size=size,
        )

    id_set = set(work["MAT"].tolist())
    for _, row in work.iterrows():
        parent = row["LIDER"]
        child = row["MAT"]
        if parent and parent in id_set and parent != child:
            graph.add_edge(parent, child)

    net = Network(height="760px", width="100%", directed=True, notebook=False)
    net.from_nx(graph)

    net.set_options(
        """
        {
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "direction": """
        + f'"{direction}"'
        + """,
                    "sortMethod": "directed",
                    "levelSeparation": 200,
                    "nodeSpacing": 170,
                    "treeSpacing": 220
                }
            },
            "edges": {
                "smooth": {
                    "type": "cubicBezier",
                    "roundness": 0.45,
                    "forceDirection": """
        + ('"horizontal"' if direction == "LR" else '"vertical"')
        + """
                },
                "color": {"color": "#b8c0cc"},
                "width": 1.3
            },
            "physics": {
                "enabled": false
            },
            "interaction": {
                "hover": true,
                "dragView": true,
                "zoomView": true,
                "navigationButtons": true
            }
        }
        """
    )

    return net


def render_pyvis(net: Network) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        net.write_html(f.name)
        html_path = Path(f.name)

    html_content = html_path.read_text(encoding="utf-8")
    st.components.v1.html(html_content, height=780, scrolling=True)
    html_path.unlink(missing_ok=True)


def main():
    path = "organograma.csv"
    try:
        df = load_data(path)
    except Exception as exc:
        st.error(f"Erro ao carregar {path}: {exc}")
        return

    posicoes = sorted([p for p in df["POSICAO"].dropna().unique() if p])

    st.sidebar.header("Filtros")
    selected_posicoes = st.sidebar.multiselect(
        "Posicao",
        options=posicoes,
        default=posicoes,
        help="Filtre por nivel/posicao no organograma.",
    )
    search = st.sidebar.text_input("Buscar por nome, cargo ou MAT", "")

    _, top_right = st.columns([8, 2])
    with top_right:
        horizontal_view = st.toggle("Modo horizontal", value=False)

    filtered, edge_count = build_graph(df, selected_posicoes, search)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de pessoas", f"{len(df)}")
    c2.metric("Pessoas no grafico", f"{len(filtered)}")
    c3.metric("Conexoes", f"{edge_count}")

    if filtered.empty:
        st.warning("Nenhum resultado para os filtros selecionados.")
        return

    st.subheader("Visualizacao")
    direction = "LR" if horizontal_view else "UD"
    net = build_pyvis_network(filtered, direction=direction)
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
