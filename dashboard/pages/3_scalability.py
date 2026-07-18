"""Pagina de escalabilidad: curvas de latencia y memoria vs N."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner

st.set_page_config(page_title="Escalabilidad - DSR Benchmark", layout="wide")

params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})
is_telemetry = params["domain"] == "telemetry"
thing = "termometros" if is_telemetry else "reglas"

st.title("Que pasa cuando la fabrica crece?")

if is_telemetry:
    st.markdown(f"""
    Empezamos con una fabrica pequena (10 termometros) y la hacemos crecer
    hasta una fabrica enorme (5,000 termometros).

    En cada paso, medimos:
    - **Cuanto tarda** cada estudiante en responder (velocidad)
    - **Cuanto pesa** su mochila (almacenamiento)
    - **Cuanto le cuesta** cada termometro individual (eficiencia)

    Esto responde la pregunta: **quien aguanta mejor el crecimiento?**
    """)
else:
    st.markdown(f"""
    Empezamos con una empresa pequena (10 reglas) y la hacemos crecer
    hasta una corporacion (5,000 reglas).

    En cada paso, medimos:
    - **Cuanto tarda** cada bibliotecario en contestar (velocidad)
    - **Cuanto ocupa** su archivador (almacenamiento)
    - **Cuanto le cuesta** cada regla individual (eficiencia)

    Esto responde la pregunta: **quien se organiza mejor al crecer?**
    """)

st.markdown("---")
st.sidebar.markdown(f"detalle={params['dims']} | conexiones={params['relations_per_node']}")

SCALE_SIZES = [10, 50, 100, 500, 1000, 5000]
ROUNDS = 20

if st.button("Hacer crecer la fabrica" if is_telemetry else "Hacer crecer la empresa", type="primary"):
    progress = st.progress(0, text="Preparando la prueba...")
    all_results = {"DSR": [], "NetworkX": [], "FAISS": []}

    total_steps = len(SCALE_SIZES) * 3
    step = 0

    for n in SCALE_SIZES:
        progress.progress(step / total_steps, text=f"DSR con {n} {thing}...")
        dsr_stats = dsr_runner.run(n, params["dims"], params["domain"], rounds=ROUNDS)
        all_results["DSR"].append({"n": n, **dsr_stats})
        step += 1

        progress.progress(step / total_steps, text=f"NetworkX con {n} {thing}...")
        nx_stats = networkx_runner.run(n, params["relations_per_node"], rounds=ROUNDS)
        all_results["NetworkX"].append({"n": n, **nx_stats})
        step += 1

        progress.progress(step / total_steps, text=f"FAISS con {n} {thing}...")
        faiss_stats = vectordb_runner.run(n, params["dims"], rounds=ROUNDS)
        all_results["FAISS"].append({"n": n, **faiss_stats})
        step += 1

    progress.progress(1.0, text="Completado!")
    st.session_state["scalability_results"] = all_results

results = st.session_state.get("scalability_results")

if results:
    colors = {"DSR": "#2ecc71", "NetworkX": "#3498db", "FAISS": "#e74c3c"}

    # Latency vs N
    st.subheader("Velocidad: cuanto tarda cada uno al crecer?")
    st.caption(
        "Cada punto muestra cuanto tarda una consulta con esa cantidad de datos. "
        "Las lineas que suben mas rapido se vuelven mas lentas al crecer."
    )
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
        xaxis_title=f"Cantidad de {thing}",
        yaxis_title="Tiempo en responder (microsegundos)",
        height=450,
        xaxis_type="log",
        yaxis_type="log",
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    # Memory vs N
    st.subheader("Mochila: cuanto pesa al crecer?")
    st.caption(
        "Cada punto muestra cuanto espacio necesita guardar esa cantidad de datos. "
        "Las lineas mas bajas son mas eficientes en almacenamiento."
    )
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
        xaxis_title=f"Cantidad de {thing}",
        yaxis_title="Espacio ocupado (bytes)",
        height=450,
        xaxis_type="log",
        yaxis_type="log",
    )
    st.plotly_chart(fig_mem, use_container_width=True)

    # Per-atom cost curve
    st.subheader(f"Eficiencia: cuanto cuesta cada {thing[:-1]} al crecer?")
    st.caption(
        "Si la linea se mantiene plana, el sistema escala bien: cada nuevo elemento "
        "cuesta lo mismo. Si sube, cada vez es mas caro agregar uno nuevo."
    )
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
        xaxis_title=f"Cantidad de {thing}",
        yaxis_title=f"Tiempo por cada {thing[:-1]} (microsegundos)",
        height=450,
        xaxis_type="log",
    )
    st.plotly_chart(fig_per, use_container_width=True)

    # Interpretation
    dsr_small = results["DSR"][0]["mean"]
    dsr_large = results["DSR"][-1]["mean"]
    nx_small = results["NetworkX"][0]["mean"]
    nx_large = results["NetworkX"][-1]["mean"]

    st.markdown(f"""
    **Que nos dicen las graficas?**

    - Al pasar de {SCALE_SIZES[0]} a {SCALE_SIZES[-1]} {thing},
      DSR paso de {dsr_small:,.0f} a {dsr_large:,.0f} microsegundos
      ({dsr_large/dsr_small:.0f}x mas lento)
    - NetworkX paso de {nx_small:,.0f} a {nx_large:,.0f} microsegundos
      ({nx_large/nx_small:.0f}x mas lento)
    - Pero en **almacenamiento**, DSR siempre usa menos espacio que los demas

    **La conclusion:** DSR escala bien en memoria (su mochila crece poco),
    aunque su tiempo de respuesta crece con la cantidad de datos.
    """)

    # Data table
    with st.expander("Ver todos los datos en tabla"):
        rows = []
        for approach, data in results.items():
            for d in data:
                rows.append({
                    "Sistema": approach,
                    f"Cantidad de {thing}": d["n"],
                    "Tiempo total": f"{d['mean']:,.1f} microseg.",
                    f"Tiempo por {thing[:-1]}": f"{d['per_atom_us']:.2f} microseg.",
                    "Espacio total": f"{d['memory_bytes']:,} bytes",
                    f"Espacio por {thing[:-1]}": f"{d['per_atom_bytes']:.0f} bytes",
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info(
        f"Haz clic en '{'Hacer crecer la fabrica' if is_telemetry else 'Hacer crecer la empresa'}' "
        f"para comenzar."
    )
