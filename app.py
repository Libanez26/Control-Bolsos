import datetime
import json
import streamlit as st
import pandas as pd
from supabase import Client, create_client
import streamlit.components.v1 as components

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión de Bolsos y Sanes",
    page_icon="💰",
    layout="wide",
)

# --- INICIALIZAR SUPABASE (Igual que en Nexus) ---
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

# --- PANTALLA DE LOGIN (Reutilizando patrón de Nexus) ---
if st.session_state["usuario"] is None:
    st.title("💰 App de Gestión de Bolsos (Sanes)")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state["usuario"] = res.user
                st.success("¡Bienvenido!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al iniciar sesión: {e}")
else:
    # --- APLICACIÓN PRINCIPAL ---
    st.sidebar.write(f"👤 **Usuario:** {st.session_state['usuario'].email}")
    if st.sidebar.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state["usuario"] = None
        st.rerun()

    st.title("💼 Panel de Control de Bolsos Activos")

    tab_mis_bolsos, tab_colaboraciones, tab_permisos = st.tabs([
        "📂 Mis Bolsos", 
        "🤝 Bolsos Compartidos conmigo", 
        "⚙️ Gestión de Permisos"
    ])

    # PESTAÑA 1: Tus bolsos creados
    with tab_mis_bolsos:
        st.subheader("Bolsos creados por ti")
        # Aquí cargas con Supabase: supabase.table("bolsos").select("*").eq("creador_id", user_id)
        st.info("Aquí verás los 7 bolsos que administras actualmente.")

    # PESTAÑA 2: Bolsos donde te dieron acceso
    with tab_colaboraciones:
        st.subheader("Bolsos de la otra persona (con permiso)")
        st.info("Aquí aparecerán los bolsos a los que la otra persona te dio acceso.")

    # PESTAÑA 3: Otorgar permisos al segundo organizador
    with tab_permisos:
        st.subheader("Control de Acceso y Colaboradores")
        st.write("Selecciona a qué bolso deseas darle acceso a la otra persona y con qué correo se registra.")
        
        correo_invitado = st.text_input("Correo del segundo organizador")
        bolso_a_compartir = st.selectbox("Selecciona el bolso", ["Bolso 1", "Bolso 2", "Bolso 3", "Bolso 4", "Bolso 5", "Bolso 6", "Bolso 7"])
        
        if st.button("Conceder Permiso"):
            st.success(f"¡Permiso concedido exitosamente a {correo_invitado} para el {bolso_a_compartir}!")
            # Aquí guardarías el registro en la tabla `bolsos_colaboradores` de Supabase.
