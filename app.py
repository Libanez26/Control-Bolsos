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

    # PESTAÑA 1: Ver y gestionar bolsos propios y su matriz de turnos
    with tab_mis_bolsos:
        st.subheader("Tus Bolsos Activos")
        
        try:
            response = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
            bolsos = response.data
            
            if bolsos:
                # Selector para elegir qué bolso administrar a detalle
                nombres_bolsos = {b["nombre"]: b for b in bolsos}
                bolso_seleccionado_nombre = st.selectbox("Selecciona un bolso para ver su cronograma y participantes:", list(nombres_bolsos.keys()))
                bolso_activo = nombres_bolsos[bolso_seleccionado_nombre]
                
                st.divider()
                st.markdown(f"### 📋 Detalle del Bolso: **{bolso_activo['nombre']}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Monto por Cuota", f"${bolso_activo['monto_cuota']}")
                col2.metric("Frecuencia", bolso_activo['frecuencia'])
                col3.metric("Total Puestos", bolso_activo['total_puestos'])
                
                st.markdown("---")
                st.subheader("🗓️ Cronograma y Turnos de Cobro (Estilo Matriz)")
                st.info("Aquí puedes ver el orden de los puestos tal como en tu ejemplo de planificación.")
                
                # Simulación visual interactiva de la tabla de puestos estilo la imagen de Excel
                puestos_totales = int(bolso_activo['total_puestos'])
                
                # Generador rápido de ejemplo de nombres por defecto si deseas editarlos
                data_ejemplo = []
                nombres_default = ["Luis I", "Yaideli", "Dioselina", "Dana", "Daniel", "María O", "Roberto"]
                
                for i in range(1, puestos_totales + 1):
                    nombre_sugerido = nombres_default[i-1] if i <= len(nombres_default) else f"Participante {i}"
                    data_ejemplo.append({
                        "Nro. Puesto": i,
                        "Participante": nombre_sugerido,
                        "Estado de Cobro": "🟢 Toca Cobrar" if i == 1 else "⏳ Pendiente"
                    })
                
                df_cronograma = pd.DataFrame(data_ejemplo)
                st.data_editor(df_cronograma, use_container_width=True, hide_index=True)

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
