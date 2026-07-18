"""Pagina de footprint de memoria/almacenamiento."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner

st.set_page_config(page_title="Memoria - DSR Benchmark", layout="wide")
st.title("Comparativa de Memoria / Almacenamiento")

params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})

st.sidebar.markdown(f"**N={params['n']}** | dims={params['dims']} | rels={params['relations_per_node']}")

if st.button("Ejecutar benchmark de memoria", type="primary"):
    with st.spinner("Midiendo footprint..."):
        dsr_stats = dsr_runner.run(params["n"], params["dims"], params["domain"], rounds=5)
        nx_stats = networkx_runner.run(params["n"], params["relations_per_node"], rounds=5)
        faiss_stats = vectordb_runner.run(params["n"], params["dims"], rounds=5)

    st.session_state["memory_results"] = {
        "DSR": dsr_stats,
        "NetworkX": nx_stats,
        "FAISS": faiss_stats,
    }

results = st.session_state.get("memory_results")

if results:
    dsr_mem = results["DSR"]["memory_bytes"]
    nx_mem = results["NetworkX"]["memory_bytes"]
    faiss_mem = results["FAISS"]["memory_bytes"]

    # Metric cards
    st.subheader("Footprint total")
    col1, col2, col3 = st.columns(3)

    def fmt_bytes(b):
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        else:
            return f"{b / (1024 * 1024):.2f} MB"

    col1.metric("DSR", fmt_bytes(dsr_mem))
    col2.metric("NetworkX", fmt_bytes(nx_mem))
    col3.metric("FAISS", fmt_bytes(faiss_mem))

    # Bar chart
    st.subheader("Bytes por enfoque")
    approaches = ["DSR", "NetworkX", "FAISS"]
    mem_values = [dsr_mem, nx_mem, faiss_mem]

    fig = go.Figure(data=[
        go.Bar(
            x=approaches,
            y=mem_values,
            marker_color=["#2ecc71", "#3498db", "#e74c3c"],
            text=[fmt_bytes(m) for m in mem_values],
            textposition="auto",
        )
    ])
    fig.update_layout(
        yaxis_title="Bytes",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Ratios
    st.subheader("Ratios de reduccion")
    col1, col2 = st.columns(2)
    ratio_graph = dsr_mem / nx_mem if nx_mem > 0 else 0
    ratio_vector = dsr_mem / faiss_mem if faiss_mem > 0 else 0
    col1.metric("DSR / NetworkX", f"{ratio_graph:.1%}", delta=f"{(1 - ratio_graph) * 100:.0f}% menos", delta_color="normal")
    col2.metric("DSR / FAISS", f"{ratio_vector:.1%}", delta=f"{(1 - ratio_vector) * 100:.0f}% menos", delta_color="normal")

    # Per-atom breakdown
    st.subheader("Costo por atomo")
    n = params["n"]
    breakdown = pd.DataFrame({
        "Enfoque": approaches,
        "Total (bytes)": mem_values,
        "Por atomo (bytes)": [m / n for m in mem_values],
        "Ratio vs DSR": [1.0, nx_mem / dsr_mem if dsr_mem > 0 else 0, faiss_mem / dsr_mem if dsr_mem > 0 else 0],
    }).set_index("Enfoque")
    st.dataframe(breakdown.style.format({
        "Total (bytes)": "{:,.0f}",
        "Por atomo (bytes)": "{:.1f}",
        "Ratio vs DSR": "{:.1f}x",
    }), use_container_width=True)
else:
    st.info("Haz clic en 'Ejecutar benchmark de memoria' para ver los resultados.")
