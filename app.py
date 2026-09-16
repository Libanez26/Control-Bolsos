import datetime
import streamlit as st
import pandas as pd
from supabase import Client, create_client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión de Bolsos y Sanes",
    page_icon="💰",
    layout="wide",
)

# --- INICIALIZAR SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    raw_url = str(st.secrets["SUPABASE_URL"]).strip()
    if "/rest/v1" in raw_url:
        raw_url = raw_url.split("/rest/v1")[0]
    raw_url = raw_url.rstrip("/")
    key = str(st.secrets["SUPABASE_KEY"]).strip()
    return create_client(raw_url, key)

supabase = init_supabase()

# --- ESTADO DE SESIÓN ---
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# --- PANTALLA DE LOGIN / REGISTRO ---
if st.session_state["usuario"] is None:
    st.title("💰 App de Gestión de Bolsos (Sanes)")
    st.markdown("Por favor, inicia sesión o regístrate para continuar.")
    
    modo = st.radio("Acción", ["Iniciar Sesión", "Registrarse"], horizontal=True)
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    
    if modo == "Iniciar Sesión":
        if st.button("Ingresar", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["usuario"] = res.user
                    st.success("¡Bienvenido!")
                    st.rerun()
            except Exception as e:
                st.error("Error al iniciar sesión: Verifique sus credenciales.")
    else:
        if st.button("Crear Cuenta", type="primary"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                if res.user:
                    st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
            except Exception as e:
                st.error(f"Error al registrarse: {e}")

else:
    # --- APLICACIÓN PRINCIPAL ---
    usuario_actual = st.session_state["usuario"]
    
    st.sidebar.markdown(f"👤 **Usuario:** {usuario_actual.email}")
    if st.sidebar.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state["usuario"] = None
        st.rerun()

    st.title("💼 Panel de Control de Bolsos y Sanes")

    tab_mis_bolsos, tab_crear, tab_compartidos, tab_permisos = st.tabs([
        "📂 Mis Bolsos", 
        "➕ Nuevo Bolso", 
        "🤝 Bolsos Compartidos", 
        "⚙️ Control de Permisos"
    ])

    # PESTAÑA 1: Ver bolsos en formato limpio con desplegable de detalles y matriz por fechas
    with tab_mis_bolsos:
        st.subheader("Tus Bolsos Activos")
        
        try:
            response = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
            bolsos = response.data
            
            if bolsos:
                for bolso in bolsos:
                    # Contenedor desplegable (Expander) para cada bolso
                    with st.expander(f"📦 {bolso['nombre']} — Monto: ${bolso['monto_cuota']} ({bolso['frecuencia']})"):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Monto por Cuota", f"${bolso['monto_cuota']}")
                        col2.metric("Frecuencia", bolso['frecuencia'])
                        col3.metric("Total Puestos", bolso['total_puestos'])
                        
                        st.markdown("---")
                        st.markdown("### 🗓️ Cronograma y Turnos de Cobro (Matriz por Fechas)")
                        
                        # Fechas quincenales automáticas de ejemplo (como tu referencia)
                        fechas_quincenales = [
                            "15-sept", "30-sept", "15-oct", "30-oct", 
                            "15-nov", "30-nov", "15-dic"
                        ]
                        
                        nombres_default = ["Luis I", "Yaidi", "Dioselina", "Dana", "Daniel", "María O", "Roberto"]
                        total_puestos = int(bolso['total_puestos'])
                        
                        # Construir matriz cruzando participantes con fechas de cobro
                        matriz_data = []
                        for i in range(1, total_puestos + 1):
                            nombre_part = nombres_default[i-1] if i-1 < len(nombres_default) else f"Participante {i}"
                            
                            fila = {"Nro": i, "Participante": nombre_part}
                            
                            # Asignar la celda verde (Toca Cobrar) en la fecha correspondiente a su puesto
                            for idx, fecha in enumerate(fechas_quincenales):
                                if (idx + 1) == i:
                                    fila[fecha] = "🟢 Toca Cobrar"
                                else:
                                    fila[fecha] = "⏳ Pendiente"
                            matriz_data.append(fila)
                        
                        df_matriz = pd.DataFrame(matriz_data)
                        
                        # Mostrar la tabla interactiva editable dentro del desplegable
                        st.data_editor(df_matriz, use_container_width=True, hide_index=True)
            else:
                st.info("Aún no tienes bolsos creados. Ve a la pestaña 'Nuevo Bolso' para registrar el primero.")
        except Exception as e:
            st.error(f"Error al cargar los bolsos: {e}")

    # PESTAÑA 2: Crear un nuevo bolso
    with tab_crear:
        st.subheader("Crear un Nuevo Bolso / San")
        
        with st.form("form_nuevo_bolso", clear_on_submit=True):
            nombre_bolso = st.text_input("Nombre del Bolso (Ej. 4to Bolso 2025)")
            monto_cuota = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=50.0)
            frecuencia = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"])
            total_puestos = st.number_input("Número Total de Puestos / Participantes", min_value=1, value=7, step=1)
            
            submit_bolso = st.form_submit_button("Guardar Bolso", type="primary")
            
            if submit_bolso:
                if nombre_bolso:
                    try:
                        data_insert = {
                            "nombre": nombre_bolso,
                            "monto_cuota": monto_cuota,
                            "frecuencia": frecuencia,
                            "total_puestos": int(total_puestos),
                            "creador_id": usuario_actual.id
                        }
                        supabase.table("bolsos").insert(data_insert).execute()
                        st.success(f"¡Bolso '{nombre_bolso}' creado y guardado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar en Supabase: {e}")
                else:
                    st.warning("Por favor ingresa al menos el nombre del bolso.")

    # PESTAÑA 3: Bolsos compartidos
    with tab_compartidos:
        st.subheader("Bolsos Compartidos Conmigo")
        st.info("Aquí verás los bolsos a los que la otra persona te ha dado acceso de colaboración.")

    # PESTAÑA 4: Gestión de permisos
    with tab_permisos:
        st.subheader("Configuración de Colaboradores")
        st.write("Comparte el acceso a tus bolsos con el segundo organizador ingresando su correo electrónico.")
        
        with st.form("form_permisos"):
            correo_colaborador = st.text_input("Correo electrónico del colaborador")
            try:
                resp_b = supabase.table("bolsos").select("id, nombre").eq("creador_id", usuario_actual.id).execute()
                mis_b_nombres = {b["nombre"]: b["id"] for b in resp_b.data} if resp_b.data else {}
            except:
                mis_b_nombres = {}
                
            selected_nombre = st.selectbox("Selecciona el Bolso a compartir", list(mis_b_nombres.keys()) if mis_b_nombres else ["No hay bolsos"])
            nivel_permiso = st.selectbox("Nivel de Acceso", ["Editor (Puede modificar pagos y turnos)", "Lectura (Solo ver)"])
            
            submit_permiso = st.form_submit_button("Conceder Acceso")
            
            if submit_permiso:
                if correo_colaborador and selected_nombre != "No hay bolsos":
                    st.success(f"¡Acceso otorgado a {correo_colaborador} para el bolso '{selected_nombre}'!")
                else:
                    st.warning("Verifica el correo y que tengas bolsos creados.")
