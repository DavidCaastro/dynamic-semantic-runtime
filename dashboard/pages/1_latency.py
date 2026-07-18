"""Pagina de comparativa de latencia en tiempo real."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dashboard.runners import dsr_runner, networkx_runner, vectordb_runner

st.set_page_config(page_title="Latencia - DSR Benchmark", layout="wide")

params = st.session_state.get("bench_params", {
    "n": 100, "dims": 64, "relations_per_node": 5, "domain": "telemetry"
})
is_telemetry = params["domain"] == "telemetry"
thing = "termometros" if is_telemetry else "reglas"
n = params["n"]

st.title("Quien contesta mas rapido?")

if is_telemetry:
    st.markdown(f"""
    Alguien pregunta: **"Dame la informacion de los {n} termometros de la fabrica"**.

    Los tres estudiantes reciben la misma pregunta. Vamos a medir cuanto tarda cada uno en responder:

    - **DSR**: Saca sus formulas y **calcula** la respuesta de cada termometro desde cero
    - **NetworkX**: Abre su mapa gigante y **recorre** las conexiones entre los {n} termometros
    - **FAISS**: Abre su album de fotos y **busca** las {min(10, n)} fotos mas parecidas a la pregunta

    Lo repetimos **50 veces** y sacamos el promedio, para que sea justo.
    """)
else:
    st.markdown(f"""
    Alguien pregunta: **"Necesito consultar las {n} reglas de negocio"**.

    Los tres bibliotecarios reciben la misma consulta. Vamos a medir cuanto tarda cada uno:

    - **DSR**: Busca sus recetas basicas y **reconstruye** cada regla paso a paso
    - **NetworkX**: Abre su arbol de conexiones y **navega** por las {n} reglas enlazadas
    - **FAISS**: Abre su fichero numerico y **busca** las {min(10, n)} fichas mas similares

    Lo repetimos **50 veces** y sacamos el promedio, para que sea justo.
    """)

st.markdown("---")
st.sidebar.markdown(f"**{n} {thing}** | detalle={params['dims']} | conexiones={params['relations_per_node']}")

ROUNDS = 50

if st.button("Hacer la prueba de velocidad", type="primary"):
    with st.spinner("DSR esta calculando desde sus formulas..."):
        dsr_stats = dsr_runner.run(n, params["dims"], params["domain"], rounds=ROUNDS)
    with st.spinner("NetworkX esta recorriendo su mapa..."):
        nx_stats = networkx_runner.run(n, params["relations_per_node"], rounds=ROUNDS)
    with st.spinner("FAISS esta buscando en su album..."):
        faiss_stats = vectordb_runner.run(n, params["dims"], rounds=ROUNDS)

    st.session_state["latency_results"] = {
        "DSR": dsr_stats,
        "NetworkX": nx_stats,
        "FAISS": faiss_stats,
    }

results = st.session_state.get("latency_results")

if results:
    dsr_mean = results["DSR"]["mean"]
    nx_mean = results["NetworkX"]["mean"]
    faiss_mean = results["FAISS"]["mean"]

    def to_human_time(us):
        """Convert microseconds to a human-readable string."""
        if us < 1000:
            return f"{us:,.1f} microsegundos"
        elif us < 1_000_000:
            return f"{us / 1000:,.1f} milisegundos"
        else:
            return f"{us / 1_000_000:,.2f} segundos"

    # Metric cards
    st.subheader("Resultados: tiempo promedio en responder")
    col1, col2, col3 = st.columns(3)
    col1.metric("DSR (calcula todo)", to_human_time(dsr_mean))
    col2.metric("NetworkX (recorre mapa)", to_human_time(nx_mean))
    col3.metric("FAISS (busca en album)", to_human_time(faiss_mean))

    # Story interpretation
    ratio_vs_nx = dsr_mean / nx_mean if nx_mean > 0 else 0
    ratio_vs_faiss = dsr_mean / faiss_mean if faiss_mean > 0 else 0

    if is_telemetry:
        st.markdown(f"""
        **Que paso?** DSR tardo **{ratio_vs_nx:,.0f} veces mas** que NetworkX
        y **{ratio_vs_faiss:,.0f} veces mas** que FAISS.

        Es como si le preguntaras a los tres estudiantes "cuanto es 847 x 293":
        - FAISS ya tenia la respuesta anotada, solo la leyo (**{to_human_time(faiss_mean)}**)
        - NetworkX la tenia en su mapa, solo tuvo que buscarla (**{to_human_time(nx_mean)}**)
        - DSR tuvo que hacer la multiplicacion a mano (**{to_human_time(dsr_mean)}**)

        DSR es mas lento porque **no guarda respuestas precalculadas**. Genera todo al momento.
        Pero su ventaja esta en otro lugar: ve la pagina de **Memoria** para descubrirla.

        **Cuando esta lentitud NO importa:**
        - Un sensor en un invernadero que revisa la temperatura **cada 30 segundos** (le sobra tiempo)
        - Un drone que procesa datos de vuelo **entre misiones**, no en pleno vuelo
        - Un dispositivo IoT que analiza lecturas **una vez por minuto** y duerme el resto
        - Un sistema de alerta sismica que evalua **cada 5 segundos** (200ms es suficiente)

        **Cuando SI importa y NO conviene DSR:**
        - Un chatbot que debe responder en menos de 100ms
        - Un buscador de productos que necesita resultados instantaneos
        - Trading algoritmico donde cada microsegundo cuenta
        """)
    else:
        st.markdown(f"""
        **Que paso?** DSR tardo **{ratio_vs_nx:,.0f} veces mas** que NetworkX
        y **{ratio_vs_faiss:,.0f} veces mas** que FAISS.

        Es como si los tres bibliotecarios buscaran un libro:
        - FAISS ya tenia el codigo del libro memorizado, solo fue al estante (**{to_human_time(faiss_mean)}**)
        - NetworkX siguio las flechas de su arbol hasta encontrarlo (**{to_human_time(nx_mean)}**)
        - DSR tuvo que reconstruir la ficha del libro desde las instrucciones basicas (**{to_human_time(dsr_mean)}**)

        DSR es mas lento porque **reconstruye todo** en cada consulta.
        Pero su archivador es mucho mas pequeno: ve la pagina de **Memoria**.

        **Cuando esta lentitud NO importa:**
        - Un inspector de campo que consulta reglas **una por una** mientras revisa un local
        - Una sucursal que valida politicas de descuento **al cierre del dia**
        - Un cajero automatico que verifica reglas de retiro **cada transaccion** (unos segundos esta bien)
        - Un dispositivo medico que evalua protocolos de diagnostico **entre pacientes**

        **Cuando SI importa y NO conviene DSR:**
        - Una pasarela de pagos que valida miles de transacciones por segundo
        - Un sistema de recomendaciones en tiempo real para e-commerce
        - Un motor de reglas en trading de alta frecuencia
        """)

    # Pipeline: que pasa por dentro
    st.markdown("---")
    st.subheader("Que paso por dentro? (el proceso paso a paso)")

    col_dsr, col_nx, col_faiss = st.columns(3)

    with col_dsr:
        st.markdown("**DSR - Genera bajo demanda**")
        st.code(f"""
1. build_atoms({n})
   dashboard/utils.py
   > Crea {n} KnowledgeAtom con sigma,
     operadores y constraints

2. DSRRuntime(dims={params['dims']})
   src/dsr/runtime.py
   > Inicializa el motor con
     RepresentationGenerator,
     AdaptiveCache y EGraph

3. runtime.register_many(atoms)
   > Registra los {n} atomos
     (solo guarda las recetas)

4. runtime.query(query, context)
   src/dsr/runtime.py:query()
   Por cada atomo:
   a) cache.get() - busca en cache
   b) generator.generate(atom, ctx)
      src/dsr/generator.py
      > Calcula embedding efimero
        desde sigma + contexto
   c) cache.put() - guarda resultado
   d) atom.all_terms() + EGraph.add()
      src/dsr/egraph.py
      > Alimenta terminos al E-Graph

5. egraph.discover_relations()
   > Descubre relaciones emergentes
     por unificacion de terminos
        """, language=None)

    with col_nx:
        st.markdown("**NetworkX - Recorre grafo**")
        st.code(f"""
1. _build_graph({n}, {params['relations_per_node']})
   dashboard/runners/networkx_runner.py
   > Crea nx.DiGraph con {n} nodos

2. G.add_node() x {n}
   > Inserta cada nodo con
     sus propiedades (tipo, zona,
     unidad, rango...)

3. G.add_edge() x {n * params['relations_per_node']}
   > Crea {params['relations_per_node']} aristas por nodo
     (co_located, correlated)

--- En cada consulta: ---

4. G.neighbors(node) x {n}
   > Recorre los vecinos de
     cada uno de los {n} nodos

5. nx.shortest_path(G, A, B)
   > Calcula la ruta mas corta
     entre dos nodos (Dijkstra)

6. _estimate_graph_memory(G)
   > Serializa todo el grafo a JSON
     para medir su peso
        """, language=None)

    with col_faiss:
        st.markdown("**FAISS - Busca en indice**")
        st.code(f"""
1. np.random.randn({n}, {params['dims']})
   dashboard/runners/vectordb_runner.py
   > Genera {n} vectores aleatorios
     de {params['dims']} dimensiones (float32)

2. np.linalg.norm() + normalize
   > Normaliza cada vector a
     longitud 1 (norma L2)

3. faiss.IndexFlatL2({params['dims']})
   > Crea indice de busqueda
     por distancia euclidiana

4. index.add(vectors)
   > Inserta los {n} vectores
     en el indice

--- En cada consulta: ---

5. index.search(query_vec, k=10)
   > Busca los 10 vectores mas
     cercanos al vector de consulta
     (fuerza bruta L2 optimizada
      con instrucciones SIMD)
        """, language=None)

    st.caption(
        "Cada columna muestra las funciones y modulos reales que se ejecutan. "
        "DSR tiene mas pasos porque genera todo al momento; los otros solo consultan datos preconstruidos."
    )

    # Bar chart
    st.subheader("Comparativa visual")
    fig = go.Figure(data=[
        go.Bar(
            x=["DSR\n(calcula todo)", "NetworkX\n(recorre mapa)", "FAISS\n(busca en album)"],
            y=[dsr_mean, nx_mean, faiss_mean],
            marker_color=["#2ecc71", "#3498db", "#e74c3c"],
            text=[to_human_time(m) for m in [dsr_mean, nx_mean, faiss_mean]],
            textposition="auto",
        )
    ])
    fig.update_layout(
        yaxis_title="Tiempo en responder (microsegundos)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed stats
    with st.expander("Ver numeros detallados (para los curiosos)"):
        st.caption(
            "**mean**: promedio | **median**: el del medio | "
            "**p95**: el 95% de las veces fue mas rapido que esto | "
            "**min/max**: la vez que fue mas rapido y mas lento"
        )
        stats_keys = ["mean", "median", "p50", "p95", "p99", "min", "max"]
        rows = []
        for approach, stats in results.items():
            row = {"Quien": approach}
            for k in stats_keys:
                row[k] = to_human_time(stats[k])
            rows.append(row)
        df = pd.DataFrame(rows).set_index("Quien")
        st.dataframe(df, use_container_width=True)

    # Per-atom
    st.subheader(f"Cuanto cuesta procesar cada {thing[:-1]}")
    col1, col2, col3 = st.columns(3)
    col1.metric("DSR", f"{results['DSR']['per_atom_us']:.2f} microseg.")
    col2.metric("NetworkX", f"{results['NetworkX']['per_atom_us']:.2f} microseg.")
    col3.metric("FAISS", f"{results['FAISS']['per_atom_us']:.2f} microseg.")

    # ---- Cold vs Warm Cache ----
    st.markdown("---")
    st.subheader("Y si DSR recuerda las respuestas anteriores?")

    if is_telemetry:
        st.markdown("""
        En la vida real, un panel de control de fabrica consulta **los mismos termometros** una y otra vez.
        DSR tiene un **cache** (una memoria rapida): la primera vez calcula todo desde cero,
        pero si le preguntan lo mismo otra vez, **recuerda la respuesta anterior** y va mucho mas rapido.

        Es como el estudiante que la primera vez hace la cuenta a mano,
        pero despues se acuerda del resultado y lo dice de memoria.
        """)
    else:
        st.markdown("""
        En una empresa real, las **mismas reglas** se consultan muchas veces al dia.
        DSR tiene un **cache** (una memoria rapida): la primera vez reconstruye la regla desde cero,
        pero si le preguntan lo mismo otra vez, **la tiene fresca en la memoria**.

        Es como el bibliotecario que la primera vez busca el libro en la bodega,
        pero despues lo deja en su escritorio por si se lo vuelven a pedir.
        """)

if st.button("Probar efecto del cache", type="primary", key="cache_btn"):
    with st.spinner("Midiendo: primera vez vs veces siguientes..."):
        cache_results = dsr_runner.run_cache_comparison(
            n, params["dims"], params["domain"], rounds=ROUNDS
        )
    st.session_state["cache_results"] = cache_results

cache_results = st.session_state.get("cache_results")

if cache_results:
    cold = cache_results["cold"]
    warm = cache_results["warm"]
    speedup = cold["mean"] / warm["mean"] if warm["mean"] > 0 else float("inf")

    def to_human_time(us):
        if us < 1000:
            return f"{us:,.1f} microsegundos"
        elif us < 1_000_000:
            return f"{us / 1000:,.1f} milisegundos"
        else:
            return f"{us / 1_000_000:,.2f} segundos"

    col1, col2, col3 = st.columns(3)
    col1.metric("Primera vez (calcula todo)", to_human_time(cold["mean"]))
    col2.metric("Veces siguientes (recuerda)", to_human_time(warm["mean"]))
    col3.metric("Cuanto mas rapido?", f"{speedup:.1f}x")

    fig_cache = go.Figure(data=[
        go.Bar(
            x=["Primera vez\n(calcula desde cero)", "Veces siguientes\n(recuerda la respuesta)"],
            y=[cold["mean"], warm["mean"]],
            marker_color=["#e67e22", "#2ecc71"],
            text=[to_human_time(cold["mean"]), to_human_time(warm["mean"])],
            textposition="auto",
        )
    ])
    fig_cache.update_layout(
        yaxis_title="Tiempo en responder (microsegundos)",
        height=400,
    )
    st.plotly_chart(fig_cache, use_container_width=True)

    if speedup > 1.5:
        st.success(
            f"Con el cache, DSR responde **{speedup:.1f} veces mas rapido** "
            f"en consultas repetidas. En un sistema real donde se consultan los mismos "
            f"datos frecuentemente, esta diferencia es significativa."
        )
    else:
        st.info(
            f"El cache mejora el rendimiento en **{speedup:.1f}x**. "
            f"La mejora depende del tipo y cantidad de datos. Con mas atomos "
            f"y operadores mas costosos, el beneficio del cache crece."
        )
else:
    if not results:
        st.info("Haz clic en 'Hacer la prueba de velocidad' para comenzar.")
