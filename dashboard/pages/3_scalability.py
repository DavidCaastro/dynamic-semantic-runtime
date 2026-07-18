"""Pagina de escalabilidad: curvas de latencia y memoria vs N."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner

st.set_page_config(page_title="Escalabilidad - DSR Benchmark", layout="wide")
st.title("Curvas de Escalabilidad")

params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})

st.sidebar.markdown(f"dims={params['dims']} | rels={params['relations_per_node']}")

SCALE_SIZES = [10, 50, 100, 500, 1000, 5000]
ROUNDS = 20

if st.button("Ejecutar benchmark de escalabilidad", type="primary"):
    progress = st.progress(0, text="Iniciando...")
    all_results = {"DSR": [], "NetworkX": [], "FAISS": []}

    total_steps = len(SCALE_SIZES) * 3
    step = 0

    for n in SCALE_SIZES:
        progress.progress(step / total_steps, text=f"DSR N={n}...")
        dsr_stats = dsr_runner.run(n, params["dims"], params["domain"], rounds=ROUNDS)
        all_results["DSR"].append({"n": n, **dsr_stats})
        step += 1

        progress.progress(step / total_steps, text=f"NetworkX N={n}...")
        nx_stats = networkx_runner.run(n, params["relations_per_node"], rounds=ROUNDS)
        all_results["NetworkX"].append({"n": n, **nx_stats})
        step += 1

        progress.progress(step / total_steps, text=f"FAISS N={n}...")
        faiss_stats = vectordb_runner.run(n, params["dims"], rounds=ROUNDS)
        all_results["FAISS"].append({"n": n, **faiss_stats})
        step += 1

    progress.progress(1.0, text="Completado!")
    st.session_state["scalability_results"] = all_results

results = st.session_state.get("scalability_results")

if results:
    colors = {"DSR": "#2ecc71", "NetworkX": "#3498db", "FAISS": "#e74c3c"}

    # Latency vs N
    st.subheader("Latencia vs N atomos")
    fig_lat = go.Figure()
    for approach, data in results.items():
        ns = [d["n"] for d in data]
        means = [d["mean"] for d in data]
        fig_lat.add_trace(go.Scatter(
            x=ns, y=means,
            mode="lines+markers",
            name=approach,
            line=dict(color=colors[approach], width=2),
            marker=dict(size=8),
        ))
    fig_lat.update_layout(
        xaxis_title="N atomos",
        yaxis_title="Latencia media (us)",
        height=450,
        xaxis_type="log",
        yaxis_type="log",
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    # Memory vs N
    st.subheader("Memoria vs N atomos")
    fig_mem = go.Figure()
    for approach, data in results.items():
        ns = [d["n"] for d in data]
        mem = [d["memory_bytes"] for d in data]
        fig_mem.add_trace(go.Scatter(
            x=ns, y=mem,
            mode="lines+markers",
            name=approach,
            line=dict(color=colors[approach], width=2),
            marker=dict(size=8),
        ))
    fig_mem.update_layout(
        xaxis_title="N atomos",
        yaxis_title="Memoria (bytes)",
        height=450,
        xaxis_type="log",
        yaxis_type="log",
    )
    st.plotly_chart(fig_mem, use_container_width=True)

    # Per-atom cost curve
    st.subheader("Costo por atomo vs N")
    fig_per = go.Figure()
    for approach, data in results.items():
        ns = [d["n"] for d in data]
        per_atom = [d["per_atom_us"] for d in data]
        fig_per.add_trace(go.Scatter(
            x=ns, y=per_atom,
            mode="lines+markers",
            name=approach,
            line=dict(color=colors[approach], width=2),
            marker=dict(size=8),
        ))
    fig_per.update_layout(
        xaxis_title="N atomos",
        yaxis_title="Latencia por atomo (us)",
        height=450,
        xaxis_type="log",
    )
    st.plotly_chart(fig_per, use_container_width=True)

    # Data table
    st.subheader("Datos completos")
    rows = []
    for approach, data in results.items():
        for d in data:
            rows.append({
                "Enfoque": approach,
                "N": d["n"],
                "Latencia media (us)": f"{d['mean']:.1f}",
                "Por atomo (us)": f"{d['per_atom_us']:.2f}",
                "Memoria (bytes)": f"{d['memory_bytes']:,}",
                "Por atomo (bytes)": f"{d['per_atom_bytes']:.0f}",
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Haz clic en 'Ejecutar benchmark de escalabilidad' para generar las curvas.")
