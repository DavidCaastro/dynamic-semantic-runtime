"""Pagina de footprint de memoria/almacenamiento."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner

st.set_page_config(page_title="Memoria - DSR Benchmark", layout="wide")

params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})
is_telemetry = params["domain"] == "telemetry"
thing = "termometros" if is_telemetry else "reglas"
n = params["n"]

st.title("Cuanto espacio necesita cada mochila?")

if is_telemetry:
    st.markdown(f"""
    Los tres estudiantes tienen que guardar la informacion de **{n} termometros**.
    Pero cada uno guarda las cosas de forma diferente:

    - **DSR** solo guarda una **receta corta** por cada termometro:
      "este sensor mide de 0 a 100 grados, esta en la zona 3, y asi se calcula su alerta".
      Su mochila es la mas liviana.

    - **NetworkX** guarda cada termometro **mas un mapa de conexiones**:
      "el termometro A esta conectado con B, C, D, E y F".
      Con {params['relations_per_node']} conexiones por termometro, su mochila pesa bastante.

    - **FAISS** guarda una **foto numerica** (un vector de {params['dims']} numeros) de cada termometro
      mas una ficha con sus datos. Su mochila tambien pesa.

    Vamos a pesar las tres mochilas.
    """)
else:
    st.markdown(f"""
    Los tres bibliotecarios tienen que guardar la informacion de **{n} reglas de negocio**.
    Pero cada uno organiza su archivador de forma diferente:

    - **DSR** solo guarda una **ficha minima** por cada regla:
      "esta regla es de categoria X, prioridad Y, y asi se evalua".
      Su archivador es el mas pequeno.

    - **NetworkX** guarda cada regla **mas todas las conexiones** entre reglas:
      "la regla A depende de B, afecta a C, se relaciona con D..."
      Con {params['relations_per_node']} conexiones por regla, su archivador crece mucho.

    - **FAISS** convierte cada regla en un **codigo numerico** de {params['dims']} digitos
      y lo guarda con sus metadatos. Su fichero tambien ocupa bastante.

    Vamos a medir cuanto ocupa cada archivador.
    """)

st.markdown("---")
st.sidebar.markdown(f"**{n} {thing}** | detalle={params['dims']} | conexiones={params['relations_per_node']}")

if st.button("Pesar las mochilas", type="primary"):
    with st.spinner("Pesando el contenido de cada enfoque..."):
        dsr_stats = dsr_runner.run(n, params["dims"], params["domain"], rounds=5)
        nx_stats = networkx_runner.run(n, params["relations_per_node"], rounds=5)
        faiss_stats = vectordb_runner.run(n, params["dims"], rounds=5)

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

    def fmt_bytes(b):
        if b < 1024:
            return f"{b} bytes"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        else:
            return f"{b / (1024 * 1024):.2f} MB"

    # Metric cards
    st.subheader("Peso de cada mochila")
    col1, col2, col3 = st.columns(3)
    col1.metric("DSR (solo recetas)", fmt_bytes(dsr_mem))
    col2.metric("NetworkX (mapa + conexiones)", fmt_bytes(nx_mem))
    col3.metric("FAISS (fotos numericas)", fmt_bytes(faiss_mem))

    # Story interpretation
    ahorro_vs_nx = (1 - dsr_mem / nx_mem) * 100 if nx_mem > 0 else 0
    ahorro_vs_faiss = (1 - dsr_mem / faiss_mem) * 100 if faiss_mem > 0 else 0
    mas_pesado = "NetworkX" if nx_mem > faiss_mem else "FAISS"

    if is_telemetry:
        st.markdown(f"""
        **Resultado:** La mochila del DSR pesa **{fmt_bytes(dsr_mem)}**, mientras que
        la de NetworkX pesa **{fmt_bytes(nx_mem)}** y la de FAISS **{fmt_bytes(faiss_mem)}**.

        DSR ahorra **{ahorro_vs_nx:.0f}%** comparado con el mapa de conexiones
        y **{ahorro_vs_faiss:.0f}%** comparado con el album de fotos.

        Esto importa cuando tienes un **sensor pequeno** (como un Arduino o un dispositivo IoT)
        que solo tiene unos pocos KB de memoria. DSR cabe, los otros quiza no.
        """)
    else:
        st.markdown(f"""
        **Resultado:** El archivador DSR ocupa **{fmt_bytes(dsr_mem)}**, mientras que
        el de NetworkX ocupa **{fmt_bytes(nx_mem)}** y el de FAISS **{fmt_bytes(faiss_mem)}**.

        DSR ahorra **{ahorro_vs_nx:.0f}%** comparado con el arbol de conexiones
        y **{ahorro_vs_faiss:.0f}%** comparado con el fichero numerico.

        Esto importa cuando necesitas **sincronizar reglas entre muchas sucursales** o
        dispositivos con almacenamiento limitado.
        """)

    # Bar chart
    st.subheader("Comparativa visual")
    fig = go.Figure(data=[
        go.Bar(
            x=["DSR\n(recetas minimas)", "NetworkX\n(mapa completo)", "FAISS\n(fotos numericas)"],
            y=[dsr_mem, nx_mem, faiss_mem],
            marker_color=["#2ecc71", "#3498db", "#e74c3c"],
            text=[fmt_bytes(m) for m in [dsr_mem, nx_mem, faiss_mem]],
            textposition="auto",
        )
    ])
    fig.update_layout(
        yaxis_title="Espacio ocupado (bytes)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Ratios
    st.subheader("Cuanto se ahorra?")
    col1, col2 = st.columns(2)
    col1.metric(
        "DSR vs NetworkX",
        f"DSR usa solo el {dsr_mem / nx_mem:.0%}" if nx_mem > 0 else "N/A",
        delta=f"Ahorra {ahorro_vs_nx:.0f}%",
        delta_color="normal",
    )
    col2.metric(
        "DSR vs FAISS",
        f"DSR usa solo el {dsr_mem / faiss_mem:.0%}" if faiss_mem > 0 else "N/A",
        delta=f"Ahorra {ahorro_vs_faiss:.0f}%",
        delta_color="normal",
    )

    # Per-item
    with st.expander(f"Ver cuanto pesa cada {thing[:-1]} individual"):
        breakdown = pd.DataFrame({
            "Quien": ["DSR", "NetworkX", "FAISS"],
            f"Total para {n} {thing}": [fmt_bytes(m) for m in [dsr_mem, nx_mem, faiss_mem]],
            f"Por cada {thing[:-1]}": [f"{m / n:.0f} bytes" for m in [dsr_mem, nx_mem, faiss_mem]],
            "Veces mas grande que DSR": [
                "1x (el mas liviano)",
                f"{nx_mem / dsr_mem:.1f}x" if dsr_mem > 0 else "-",
                f"{faiss_mem / dsr_mem:.1f}x" if dsr_mem > 0 else "-",
            ],
        }).set_index("Quien")
        st.dataframe(breakdown, use_container_width=True)

    st.markdown("---")
    st.markdown("""
    **En resumen:** DSR es mas lento contestando (ver pagina Latencia),
    pero necesita mucho menos espacio para guardar la informacion.
    Es ideal para situaciones donde **el espacio importa mas que la velocidad**:
    dispositivos pequenos, redes con poco ancho de banda, o sistemas con millones de elementos.
    """)
else:
    st.info("Haz clic en 'Pesar las mochilas' para comenzar.")
