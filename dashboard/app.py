"""Dashboard Comparativo en Tiempo Real - DSR vs Graph DB vs Vector DB."""

import streamlit as st

st.set_page_config(
    page_title="DSR Benchmark Dashboard",
    page_icon="\u269B",
    layout="wide",
)

# ---- Sidebar: controles interactivos ----
st.sidebar.title("DSR Benchmark")
st.sidebar.markdown("Compara DSR vs NetworkX (Graph) vs FAISS (Vector)")

n_atoms = st.sidebar.select_slider(
    "N Atomos",
    options=[10, 50, 100, 500, 1000, 5000],
    value=100,
)

dims = st.sidebar.selectbox(
    "Dimensiones embedding",
    options=[32, 64, 128, 256, 384],
    index=1,
)

relations_per_node = st.sidebar.slider(
    "Relaciones por nodo (NetworkX)",
    min_value=1,
    max_value=20,
    value=5,
)

domain = st.sidebar.selectbox(
    "Dominio",
    options=["telemetry", "business_rules"],
)

# Store params in session state for pages
st.session_state["bench_params"] = {
    "n": n_atoms,
    "dims": dims,
    "relations_per_node": relations_per_node,
    "domain": domain,
}

# ---- Main page ----
st.title("Dynamic Semantic Runtime - Dashboard Comparativo")

st.markdown("""
Este dashboard compara en tiempo real el rendimiento del **DSR** (Dynamic Semantic Runtime)
contra implementaciones reales de **Graph DB** (NetworkX) y **Vector DB** (FAISS).

### Paginas disponibles

- **Latencia**: Comparativa de latencia media, p50, p95, p99
- **Memoria**: Footprint de almacenamiento side-by-side
- **Escalabilidad**: Curvas de latencia y memoria vs N atomos

Ajusta los parametros en el sidebar y navega a cada pagina para ver los resultados.
""")

# Quick overview with current params
st.subheader("Configuracion actual")
col1, col2, col3, col4 = st.columns(4)
col1.metric("N Atomos", n_atoms)
col2.metric("Dimensiones", dims)
col3.metric("Relaciones/nodo", relations_per_node)
col4.metric("Dominio", domain)
