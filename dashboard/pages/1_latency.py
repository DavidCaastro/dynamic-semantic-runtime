"""Pagina de comparativa de latencia en tiempo real."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner
from dashboard.utils import compute_stats, stats_to_dataframe

st.set_page_config(page_title="Latencia - DSR Benchmark", layout="wide")
st.title("Comparativa de Latencia")

# Get params from session state
params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})

st.sidebar.markdown(f"**N={params['n']}** | dims={params['dims']} | rels={params['relations_per_node']}")

ROUNDS = 50

if st.button("Ejecutar benchmark de latencia", type="primary"):
    with st.spinner("Ejecutando DSR..."):
        dsr_stats = dsr_runner.run(params["n"], params["dims"], params["domain"], rounds=ROUNDS)
    with st.spinner("Ejecutando NetworkX..."):
        nx_stats = networkx_runner.run(params["n"], params["relations_per_node"], rounds=ROUNDS)
    with st.spinner("Ejecutando FAISS..."):
        faiss_stats = vectordb_runner.run(params["n"], params["dims"], rounds=ROUNDS)

    st.session_state["latency_results"] = {
        "DSR": dsr_stats,
        "NetworkX": nx_stats,
        "FAISS": faiss_stats,
    }

results = st.session_state.get("latency_results")

if results:
    # Metric cards
    st.subheader("Latencia media")
    col1, col2, col3 = st.columns(3)
    col1.metric("DSR", f"{results['DSR']['mean']:.1f} us")
    col2.metric("NetworkX", f"{results['NetworkX']['mean']:.1f} us")
    col3.metric("FAISS", f"{results['FAISS']['mean']:.1f} us")

    # Bar chart
    st.subheader("Latencia media por enfoque")
    approaches = list(results.keys())
    means = [results[a]["mean"] for a in approaches]

    fig = go.Figure(data=[
        go.Bar(
            x=approaches,
            y=means,
            marker_color=["#2ecc71", "#3498db", "#e74c3c"],
            text=[f"{m:.1f}" for m in means],
            textposition="auto",
        )
    ])
    fig.update_layout(
        yaxis_title="Latencia (us)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats table
    st.subheader("Estadisticas detalladas (us)")
    stats_keys = ["mean", "median", "p50", "p95", "p99", "min", "max"]
    rows = []
    for approach, stats in results.items():
        row = {"Enfoque": approach}
        for k in stats_keys:
            row[k] = f"{stats[k]:.1f}"
        rows.append(row)
    df = pd.DataFrame(rows).set_index("Enfoque")
    st.dataframe(df, use_container_width=True)

    # Per-atom cost
    st.subheader("Costo por atomo")
    col1, col2, col3 = st.columns(3)
    col1.metric("DSR", f"{results['DSR']['per_atom_us']:.2f} us/atomo")
    col2.metric("NetworkX", f"{results['NetworkX']['per_atom_us']:.2f} us/atomo")
    col3.metric("FAISS", f"{results['FAISS']['per_atom_us']:.2f} us/atomo")
else:
    st.info("Haz clic en 'Ejecutar benchmark de latencia' para ver los resultados.")
