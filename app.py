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
    email_corto = usuario_actual.email.split("@")[0] # Extraer un identificador corto del correo
    
    st.sidebar.markdown(f"👤 **Usuario:** {email_corto}")
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

    # PESTAÑA 1: Ver bolsos y matriz interactiva con selectores desplegables
    with tab_mis_bolsos:
        st.subheader("Tus Bolsos Activos")
        
        try:
            response = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
            bolsos = response.data
            
            if bolsos:
                for bolso in bolsos:
                    bolso_id = bolso['id']
                    total_puestos = int(bolso['total_puestos'])
                    
                    with st.expander(f"📦 {bolso['nombre']} — Monto: ${bolso['monto_cuota']} ({bolso['frecuencia']})"):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Monto por Cuota", f"${bolso['monto_cuota']}")
                        col2.metric("Frecuencia", bolso['frecuencia'])
                        col3.metric("Total Puestos", total_puestos)
                        
                        st.markdown("---")
                        st.markdown("### 🗓️ Cronograma, Participantes y Estados")
                        st.info("Escribe los nombres de los participantes y utiliza los menús desplegables en cada fecha para cambiar los estados.")
                        
                        fechas_quincenales = ["15-sept", "30-sept", "15-oct", "30-oct", "15-nov", "30-nov", "15-dic"]
                        
                        # Consultar si ya existen registros en detalles_bolso para este bolso
                        resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", bolso_id).execute()
                        datos_existentes = resp_det.data if resp_det.data else []
                        
                        # Si no hay registros creados aún, inicializarlos en blanco/automático con nombres genéricos
                        if not datos_existentes:
                            nuevos_filas = []
                            for i in range(1, total_puestos + 1):
                                for idx, fecha in enumerate(fechas_quincenales):
                                    estado_inicial = "🟢 Toca Cobrar" if (idx + 1) == i else "⏳ Pendiente"
                                    nuevos_filas.append({
                                        "bolso_id": bolso_id,
                                        "nro_puesto": i,
                                        "participante": f"Participante {i}",
                                        "fecha": fecha,
                                        "estado": estado_inicial,
                                        "actualizado_por": email_corto
                                    })
                            supabase.table("detalles_bolso").insert(nuevos_filas).execute()
                            resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", bolso_id).execute()
                            datos_existentes = resp_det.data
                        
                        # Reorganizar los datos en formato de matriz para mostrar en pantalla
                        matriz_dict = {}
                        for row in datos_existentes:
                            puesto = row["nro_puesto"]
                            if puesto not in matriz_dict:
                                matriz_dict[puesto] = {
                                    "Nro. Puesto": puesto,
                                    "Participante": row["participante"]
                                }
                            matriz_dict[puesto][row["fecha"]] = row["estado"]
                        
                        df_matriz = pd.DataFrame(list(matriz_dict.values()))
                        
                        # Opciones exactas para el menú desplegable en cada celda de fecha (Solo Pendiente, Toca Cobrar y Pagado)
                        opciones_estado = [
                            "⏳ Pendiente", 
                            "🟢 Toca Cobrar", 
                            f"✅ Pagado ({email_corto})"
                        ]
                        
                        # Configurar columnas (Nro bloqueado, Participante texto, Fechas con selectores)
                        column_config_dict = {
                            "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                            "Participante": st.column_config.TextColumn("Participante", width="medium"),
                        }
                        
                        for fecha in fechas_quincenales:
                            column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                label=fecha,
                                options=opciones_estado,
                                required=True,
                                width="medium"
                            )

                        # Editor interactivo con menús desplegables
                        df_editado = st.data_editor(
                            df_matriz, 
                            column_config=column_config_dict,
                            use_container_width=True, 
                            hide_index=True,
                            key=f"editor_{bolso_id}"
                        )
                        
                        if st.button("Guardar Cambios del Cronograma", key=f"btn_save_{bolso_id}", type="primary"):
                            try:
                                for index, row in df_editado.iterrows():
                                    puesto = row["Nro. Puesto"]
                                    nombre_part = row["Participante"]
                                    for fecha in fechas_quincenales:
                                        if fecha in row:
                                            estado_actual = row[fecha]
                                            # Actualizar en Supabase
                                            supabase.table("detalles_bolso").update({
                                                "participante": nombre_part,
                                                "estado": estado_actual,
                                                "actualizado_por": email_corto
                                            }).eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                
                                st.success("¡Cambios guardados exitosamente!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar los cambios: {e}")
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
                        st.success(f"¡Bolso '{nombre_bolso}' creado exitosamente! Ya puedes configurarlo en 'Mis Bolsos'.")
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
        st.write("Comparte el acceso a tus bolsos ingresando el correo del colaborador.")
        
        with st.form("form_permisos"):
            correo_colaborador = st.text_input("Correo electrónico del colaborador")
            try:
                resp_b = supabase.table("bolsos").select("id, nombre").eq("creador_id", usuario_actual.id).execute()
                mis_b_nombres = {b["nombre"]: b["id"] for b in resp_b.data} if resp_b.data else {}
            except:
                mis_b_nombres = {}
                
            selected_nombre = st.selectbox("Selecciona el Bolso a compartir", list(mis_b_nombres.keys()) if mis_b_nombres else ["No hay bolsos"])
            nivel_permiso = st.selectbox("Nivel de Acceso", ["Editor", "Lectura"])
            
            submit_permiso = st.form_submit_button("Conceder Acceso")
            
            if submit_permiso:
                if correo_colaborador and selected_nombre != "No hay bolsos":
                    st.success(f"¡Acceso otorgado a {correo_colaborador} para el bolso '{selected_nombre}'!")
                else:
                    st.warning("Verifica el correo y que tengas bolsos creados.")
