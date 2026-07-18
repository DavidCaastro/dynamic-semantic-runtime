"""Dashboard Comparativo en Tiempo Real - DSR vs Graph DB vs Vector DB."""

import streamlit as st

st.set_page_config(
    page_title="DSR Benchmark Dashboard",
    page_icon="\u269B",
    layout="wide",
)

# ---- Sidebar ----
st.sidebar.title("Configuracion")
st.sidebar.markdown("---")

n_atoms = st.sidebar.select_slider(
    "Cuantos elementos simular",
    options=[10, 50, 100, 500, 1000, 5000],
    value=100,
)

dims = st.sidebar.selectbox(
    "Nivel de detalle del analisis",
    options=[32, 64, 128, 256, 384],
    index=1,
    help="Mas dimensiones = analisis mas detallado pero mas pesado.",
)

relations_per_node = st.sidebar.slider(
    "Conexiones entre elementos",
    min_value=1,
    max_value=20,
    value=5,
)

domain = st.sidebar.selectbox(
    "Escenario",
    options=["telemetry", "business_rules"],
    format_func=lambda x: "Fabrica con sensores" if x == "telemetry" else "Empresa con reglas",
)

st.session_state["bench_params"] = {
    "n": n_atoms,
    "dims": dims,
    "relations_per_node": relations_per_node,
    "domain": domain,
}

# ---- Main page ----
st.title("Tres formas de recordar conocimiento")

if domain == "telemetry":
    st.markdown(f"""
    ### La historia

    Imagina una **fabrica** con **{n_atoms} termometros** repartidos por todas las salas.
    Cada termometro sabe su rango de temperatura, en que zona esta y como detectar alertas.

    La pregunta es: **como guardamos y consultamos la informacion de todos esos termometros?**

    Hay tres formas de hacerlo, como tres estudiantes que se preparan para un examen:

    ---

    **El estudiante DSR** (el minimalista)
    > "Yo solo memorizo las formulas. Cuando me preguntan algo, calculo la respuesta en el momento.
    > Mi mochila pesa poco, pero tardo mas en responder."

    **El estudiante NetworkX** (el del mapa mental)
    > "Yo dibujo un mapa gigante conectando todo: el termometro A esta cerca del B,
    > el B se relaciona con el C... Cuando me preguntan, recorro mi mapa.
    > Mi mochila pesa mas por todo el papel, pero encuentro conexiones rapido."

    **El estudiante FAISS** (el de las fotos)
    > "Yo le saco una foto numerica a cada termometro y las guardo todas en un album.
    > Cuando me preguntan, busco la foto mas parecida.
    > Mi album ocupa espacio, pero buscar es rapidisimo."

    ---

    Ahora vamos a poner a los tres a competir con **{n_atoms} termometros**.
    Navega a cada pagina del menu lateral para ver los resultados.
    """)
else:
    st.markdown(f"""
    ### La historia

    Imagina una **empresa** con **{n_atoms} reglas de negocio**: quien puede aprobar facturas,
    que pasa cuando un pedido cambia de estado, que departamento maneja cada proceso.

    La pregunta es: **como guardamos y consultamos todas esas reglas?**

    Hay tres formas de hacerlo, como tres bibliotecarios con estilos diferentes:

    ---

    **El bibliotecario DSR** (el que recuerda las recetas)
    > "Yo solo anoto las recetas basicas de cada regla. Cuando alguien pregunta,
    > la reconstruyo paso a paso. Mi archivador es pequeno, pero tardo mas en contestar."

    **El bibliotecario NetworkX** (el del arbol genealogico)
    > "Yo dibujo un arbol gigante: esta regla depende de aquella, aquella se conecta con esta otra...
    > Tengo todo mapeado. Mi archivador es grande, pero navego rapido por las conexiones."

    **El bibliotecario FAISS** (el de las fichas numericas)
    > "Yo convierto cada regla en un codigo numerico y las ordeno por similitud.
    > Cuando preguntan, busco el codigo mas parecido. Mi fichero ocupa bastante, pero buscar es instantaneo."

    ---

    Ahora vamos a poner a los tres a competir con **{n_atoms} reglas**.
    Navega a cada pagina del menu lateral para ver los resultados.
    """)

st.subheader("Datos de la prueba")
col1, col2, col3, col4 = st.columns(4)
if domain == "telemetry":
    col1.metric("Termometros", n_atoms)
    col2.metric("Detalle del analisis", dims)
    col3.metric("Conexiones entre sensores", relations_per_node)
    col4.metric("Escenario", "Fabrica")
else:
    col1.metric("Reglas de negocio", n_atoms)
    col2.metric("Detalle del analisis", dims)
    col3.metric("Conexiones entre reglas", relations_per_node)
    col4.metric("Escenario", "Empresa")
