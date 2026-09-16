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
                st.error(f"Error al iniciar sesión: Verifique sus credenciales.")
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

    # Pestañas principales de la aplicación
    tab_mis_bolsos, tab_crear, tab_compartidos, tab_permisos = st.tabs([
        "📂 Mis Bolsos", 
        "➕ Nuevo Bolso", 
        "🤝 Bolsos Compartidos", 
        "⚙️ Control de Permisos"
    ])

    # PESTAÑA 1: Ver y gestionar bolsos propios
    with tab_mis_bolsos:
        st.subheader("Tus Bolsos Activos")
        st.info("Aquí podrás visualizar el estado de tus bolsos, turnos y control de pagos.")
        
        # Aquí puedes conectar la consulta a tu tabla 'bolsos' en Supabase:
        # data = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
        # st.dataframe(data.data)
        st.write("*(Espacio preparado para listar tus bolsos desde Supabase)*")

    # PESTAÑA 2: Crear un nuevo bolso
    with tab_crear:
        st.subheader("Crear un Nuevo Bolso / San")
        
        with st.form("form_nuevo_bolso"):
            nombre_bolso = st.text_input("Nombre del Bolso (Ej. Bolso Quincenal)")
            monto_cuota = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f")
            frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
            total_puestos = st.number_input("Número Total de Puestos / Participantes", min_value=1, step=1)
            
            submit_bolso = st.form_submit_button("Guardar Bolso")
            
            if submit_bolso:
                if nombre_bolso:
                    # Aquí insertarías el registro en Supabase en la tabla 'bolsos'
                    st.success(f"¡Bolso '{nombre_bolso}' creado exitosamente!")
                else:
                    st.warning("Por favor ingresa al menos el nombre del bolso.")

    # PESTAÑA 3: Bolsos compartidos por la otra persona
    with tab_compartidos:
        st.subheader("Bolsos Compartidos Conmigo")
        st.info("Aquí verás los bolsos a los que la otra persona te ha dado acceso de colaboración.")
        st.write("*(Los bolsos compartidos aparecerán aquí automáticamente al sincronizar permisos)*")

    # PESTAÑA 4: Gestión de permisos para el segundo organizador
    with tab_permisos:
        st.subheader("Configuración de Colaboradores")
        st.write("Comparte el acceso a tus bolsos con el segundo organizador ingresando su correo electrónico.")
        
        with st.form("form_permisos"):
            correo_colaborador = st.text_input("Correo electrónico del colaborador")
            bolso_a_otorgar = st.selectbox("Selecciona el Bolso a compartir", ["Ej: Bolso 1", "Ej: Bolso 2", "Ej: Bolso 3", "Ej: Bolso 4", "Ej: Bolso 5", "Ej: Bolso 6", "Ej: Bolso 7"])
            nivel_permiso = st.selectbox("Nivel de Acceso", ["Editor (Puede modificar pagos y turnos)", "Lectura (Solo ver)"])
            
            submit_permiso = st.form_submit_button("Conceder Acceso")
            
            if submit_permiso:
                if correo_colaborador:
                    st.success(f"¡Acceso otorgado a {correo_colaborador} para el bolso seleccionado!")
                else:
                    st.warning("Ingresa un correo válido.")
