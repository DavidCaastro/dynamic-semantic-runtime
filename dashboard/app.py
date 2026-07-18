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

    ---

    ### Donde se usa cada enfoque en el mundo real?

    | Caso de uso | Mejor enfoque | Por que |
    |-------------|---------------|---------|
    | Panel de control en planta industrial con 10,000 sensores | Graph DB / Vector DB | Necesita respuestas instantaneas, el servidor tiene memoria de sobra |
    | Drone agricola con 256 KB de RAM monitoreando cultivos | **DSR** | No cabe un grafo ni un indice de vectores en tan poca memoria |
    | Flota de 5,000 camiones enviando telemetria por red 3G lenta | **DSR** | Sincronizar grafos completos por red lenta es impracticable; los atomos compactos si viajan bien |
    | App de recomendaciones buscando productos similares | Vector DB (FAISS) | La busqueda por similitud en milisegundos es exactamente lo que hace FAISS |
    | Red de sensores marinos en boyas sin conexion estable | **DSR** | Cada boya procesa localmente con almacenamiento minimo y sincroniza cuando tiene senal |
    | Sistema de alerta sismica distribuido en zonas remotas | **DSR** | Cada estacion necesita autonomia total con hardware minimo |
    | Base de conocimiento medico con millones de relaciones entre sintomas | Graph DB (NetworkX/Neo4j) | Las relaciones entre conceptos son el valor principal, vale la pena almacenarlas |
    | Satelites de observacion terrestre con capacidad limitada | **DSR** | Almacenamiento a bordo es carisimo; DSR guarda solo las reglas de procesamiento |
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

    ---

    ### Donde se usa cada enfoque en el mundo real?

    | Caso de uso | Mejor enfoque | Por que |
    |-------------|---------------|---------|
    | ERP centralizado con 100 usuarios consultando permisos en tiempo real | Graph DB / Vector DB | Necesita respuestas instantaneas, el servidor es potente |
    | App de campo para inspectores que trabajan sin internet | **DSR** | El telefono lleva las reglas compactas y las evalua localmente sin conexion |
    | Franquicia con 500 sucursales que deben sincronizar politicas | **DSR** | Enviar atomos de 250 bytes cada uno es mucho mas rapido que sincronizar grafos completos |
    | Motor de busqueda legal que encuentra contratos similares | Vector DB (FAISS) | Busqueda semantica por similitud es el fuerte de los vectores |
    | Dispositivo medico portatil con reglas de diagnostico en firmware | **DSR** | Solo tiene 64 KB de flash; DSR cabe, un grafo con relaciones no |
    | Videojuego con NPCs que siguen reglas de comportamiento dinamicas | **DSR** | Cada NPC lleva sus reglas minimas y genera comportamiento segun el contexto del momento |
    | Plataforma fintech con arbol de decisiones de credito | Graph DB (NetworkX/Neo4j) | Las dependencias entre reglas son complejas y vale la pena mapearlas explicitamente |
    | Red de cajeros automaticos en zonas rurales con conectividad intermitente | **DSR** | Cada cajero opera autonomo con reglas minimas y sincroniza cuando tiene conexion |
    """)

st.markdown("""
---

### Y para crear modelos de IA / Machine Learning?

DSR no reemplaza a TensorFlow o PyTorch para entrenar redes neuronales,
pero si tiene aplicaciones practicas en el ecosistema de ML:

| Caso de uso en ML/IA | Enfoque | Como funciona |
|----------------------|---------|---------------|
| **Preprocesar datos en el edge antes de enviar al modelo** | DSR | Un sensor con DSR aplica operadores de normalizacion y filtrado localmente, y solo envia los resultados compactos al modelo central. Ahorra ancho de banda. |
| **Feature engineering ligero en dispositivos** | DSR | Cada atomo define como transformar datos crudos en features. El dispositivo genera features bajo demanda sin cargar un pipeline completo de sklearn. |
| **Knowledge distillation compacta** | DSR | Un modelo grande en la nube "destila" su conocimiento en atomos con operadores. El dispositivo edge usa esos atomos para hacer inferencia local sin el modelo pesado. |
| **Embeddings contextuales sin modelo pre-entrenado** | DSR | DSR genera embeddings diferentes segun el contexto (dominio, condiciones) sin necesitar un modelo como BERT o Sentence-Transformers. Util cuando no cabe un LLM en el dispositivo. |
| **RAG (Retrieval-Augmented Generation) en el edge** | DSR + FAISS | Los atomos almacenan conocimiento compacto. Cuando hay conexion, se genera un indice FAISS temporal para busqueda rapida. Sin conexion, DSR genera bajo demanda. |
| **Versionado de conocimiento para reentrenamiento** | DSR | Cada atomo tiene version y provenance. Facil rastrear que conocimiento cambio entre versiones del modelo para reentrenamiento incremental. |
| **Federated Learning con bajo ancho de banda** | DSR | En vez de enviar gradientes pesados, cada nodo envia atomos actualizados (~250 bytes). El servidor central los agrega y redistribuye. |
| **Busqueda semantica completa en servidor** | FAISS / Vector DB | Si tienes un servidor con GPU y millones de documentos, FAISS con embeddings de un modelo pre-entrenado es la mejor opcion. DSR no compite aqui. |
| **Grafo de conocimiento para LLMs (knowledge graph)** | Graph DB | Si alimentas un LLM con un knowledge graph estructurado (ej: Wikidata), NetworkX o Neo4j son la opcion natural. |
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
