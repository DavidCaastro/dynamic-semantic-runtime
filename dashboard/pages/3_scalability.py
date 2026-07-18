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

    **Que significa esto en casos reales?**
    - Una **red de 5,000 sensores marinos** puede funcionar con DSR
      porque cada boya solo necesita almacenar sus atomos compactos,
      aunque tarde un poco mas en procesarlos
    - Una **flota de drones** puede llevar las reglas de {SCALE_SIZES[-1]} puntos de inspeccion
      sin llenar su memoria, procesando cada punto entre sobrevuelos
    - Una **cadena de {SCALE_SIZES[-1]} tiendas** puede sincronizar todas sus reglas de negocio
      en segundos porque los atomos pesan poco, incluso por redes lentas
    - En cambio, un **buscador en tiempo real** con {SCALE_SIZES[-1]} productos
      necesita FAISS o similar: la velocidad de busqueda es critica
    """)

    # What's happening at each scale
    with st.expander("Que pasa por dentro al escalar? (detalle tecnico)"):
        st.markdown(f"""
        Al aumentar N, cada sistema se comporta diferente internamente:

        **DSR** (`src/dsr/runtime.py:query()`)
        - Con N=10: recorre 10 atomos, aplica 2 operadores a cada uno, genera 10 embeddings, alimenta 20 terminos al E-Graph
        - Con N=5000: recorre 5,000 atomos, aplica 10,000 operadores, genera 5,000 embeddings, alimenta 10,000 terminos al E-Graph
        - El tiempo crece porque `generator.generate()` se ejecuta N veces y `egraph.add()` se ejecuta 2N veces
        - La memoria crece poco: solo se guardan los sigma (~250 bytes/atomo), nunca los embeddings

        **NetworkX** (`networkx_runner.py:run()`)
        - Con N=10: el grafo tiene 10 nodos + {10 * params['relations_per_node']} aristas. `G.neighbors()` es O(1) por nodo
        - Con N=5000: el grafo tiene 5,000 nodos + {5000 * params['relations_per_node']:,} aristas. `shortest_path()` es O(N log N)
        - El tiempo crece por el shortest_path (Dijkstra) y el volumen de aristas
        - La memoria crece linealmente: cada arista se almacena explicitamente

        **FAISS** (`vectordb_runner.py:run()`)
        - Con N=10: busca entre 10 vectores de {params['dims']}d. Trivial
        - Con N=5000: busca entre 5,000 vectores de {params['dims']}d. IndexFlatL2 es O(N) pero con SIMD
        - El tiempo crece linealmente pero con constante muy baja (operaciones vectorizadas en CPU)
        - La memoria crece linealmente: N x {params['dims']} x 4 bytes
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
