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
    email_usuario = usuario_actual.email.strip().lower()
    email_corto = email_usuario.split("@")[0]
    
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

    # PESTAÑA 1: Ver tus bolsos
    with tab_mis_bolsos:
        st.subheader("Tus Bolsos Activos")
        
        try:
            response = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
            bolsos = response.data
            
            if bolsos:
                for bolso in bolsos:
                    bolso_id = bolso['id']
                    total_puestos = int(bolso['total_puestos'])
                    monto_cuota = float(bolso['monto_cuota'])
                    pozo_total = monto_cuota * total_puestos
                    
                    with st.expander(f"📦 {bolso['nombre']} — Monto Cuota: ${monto_cuota:,.2f} ({bolso['frecuencia']})"):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Cuota por Persona", f"${monto_cuota:,.2f}")
                        col2.metric("Total Puestos", total_puestos)
                        col3.metric("Pozo a Recibir", f"${pozo_total:,.2f}")
                        col4.metric("Frecuencia", bolso['frecuencia'])
                        
                        # Edición general del bolso
                        with st.popover("✏️ Editar configuración de este Bolso"):
                            with st.form(f"form_editar_{bolso_id}"):
                                nuevo_nombre = st.text_input("Nombre del Bolso", value=bolso['nombre'])
                                nuevo_monto = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=monto_cuota)
                                idx_freq = ["Quincenal", "Semanal", "Mensual"].index(bolso['frecuencia']) if bolso['frecuencia'] in ["Quincenal", "Semanal", "Mensual"] else 0
                                nueva_freq = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"], index=idx_freq)
                                nuevo_puestos = st.number_input("Número Total de Puestos", min_value=1, value=total_puestos, step=1)
                                
                                btn_actualizar_bolso = st.form_submit_button("Guardar Cambios Generales", type="primary")
                                
                                if btn_actualizar_bolso:
                                    try:
                                        supabase.table("bolsos").update({
                                            "nombre": nuevo_nombre,
                                            "monto_cuota": nuevo_monto,
                                            "frecuencia": nueva_freq,
                                            "total_puestos": int(nuevo_puestos)
                                        }).eq("id", bolso_id).execute()
                                        st.success("¡Configuración actualizada con éxito!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al actualizar: {e}")
                        
                        st.markdown("---")
                        st.markdown("### 🗓️ Cronograma, Participantes y Estados")
                        
                        fechas_quincenales = ["15-sept", "30-sept", "15-oct", "30-oct", "15-nov", "30-nov", "15-dic"]
                        
                        resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", bolso_id).execute()
                        datos_existentes = resp_det.data if resp_det.data else []
                        
                        if not datos_existentes or len(set(r["nro_puesto"] for r in datos_existentes)) != total_puestos:
                            for i in range(1, total_puestos + 1):
                                for idx, fecha in enumerate(fechas_quincenales):
                                    existe = any(d["nro_puesto"] == i and d["fecha"] == fecha for d in datos_existentes)
                                    if not existe:
                                        estado_inicial = "🟢 Toca Cobrar" if (idx + 1) == i else "⏳ Pendiente"
                                        supabase.table("detalles_bolso").insert({
                                            "bolso_id": bolso_id,
                                            "nro_puesto": i,
                                            "participante": f"Participante {i}",
                                            "fecha": fecha,
                                            "estado": estado_inicial,
                                            "actualizado_por": email_corto
                                        }).execute()
                            resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", bolso_id).execute()
                            datos_existentes = resp_det.data
                        
                        matriz_dict = {}
                        for row in datos_existentes:
                            puesto = row["nro_puesto"]
                            if puesto <= total_puestos:
                                if puesto not in matriz_dict:
                                    matriz_dict[puesto] = {
                                        "Nro. Puesto": puesto,
                                        "Participante": row["participante"]
                                    }
                                matriz_dict[puesto][row["fecha"]] = row["estado"]
                        
                        df_matriz = pd.DataFrame(list(matriz_dict.values()))
                        opciones_estado = ["⏳ Pendiente", "🟢 Toca Cobrar", f"✅ Pagado ({email_corto})"]
                        
                        column_config_dict = {
                            "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                            "Participante": st.column_config.TextColumn("Participante", width="medium"),
                        }
                        
                        for fecha in fechas_quincenales:
                            column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                label=fecha, options=opciones_estado, required=True, width="medium"
                            )

                        df_editado = st.data_editor(df_matriz, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_{bolso_id}")
                        
                        if st.button("Guardar Cambios del Cronograma", key=f"btn_save_{bolso_id}", type="primary"):
                            try:
                                for index, row in df_editado.iterrows():
                                    puesto = row["Nro. Puesto"]
                                    nombre_part = row["Participante"]
                                    for fecha in fechas_quincenales:
                                        if fecha in row:
                                            supabase.table("detalles_bolso").update({
                                                "participante": nombre_part,
                                                "estado": row[fecha],
                                                "actualizado_por": email_corto
                                            }).eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                st.success("¡Cambios guardados exitosamente!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar los cambios: {e}")
            else:
                st.info("Aún no tienes bolsos creados.")
        except Exception as e:
            st.error(f"Error al cargar los bolsos: {e}")

    # PESTAÑA 2: Crear un nuevo bolso
    with tab_crear:
        st.subheader("Crear un Nuevo Bolso / San")
        
        with st.form("form_nuevo_bolso", clear_on_submit=True):
            nombre_bolso = st.text_input("Nombre del Bolso")
            monto_cuota = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=50.0)
            frecuencia = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"])
            total_puestos = st.number_input("Número Total de Puestos", min_value=1, value=7, step=1)
            
            submit_bolso = st.form_submit_button("Guardar Bolso", type="primary")
            
            if submit_bolso:
                if nombre_bolso:
                    try:
                        supabase.table("bolsos").insert({
                            "nombre": nombre_bolso,
                            "monto_cuota": monto_cuota,
                            "frecuencia": frecuencia,
                            "total_puestos": int(total_puestos),
                            "creador_id": usuario_actual.id
                        }).execute()
                        st.success(f"¡Bolso '{nombre_bolso}' creado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar en Supabase: {e}")
                else:
                    st.warning("Por favor ingresa al menos el nombre del bolso.")

    # PESTAÑA 3: Bolsos compartidos conmigo
    with tab_compartidos:
        st.subheader("🤝 Bolsos Compartidos Conmigo")
        try:
            resp_comp = supabase.table("compartidos").select("bolso_id, nivel").eq("email_colaborador", email_usuario).execute()
            shared_records = resp_comp.data if resp_comp.data else []
            
            if shared_records:
                for rec in shared_records:
                    b_id = rec["bolso_id"]
                    nivel_acceso = rec["nivel"]
                    
                    b_info_resp = supabase.table("bolsos").select("*").eq("id", b_id).execute()
                    if b_info_resp.data:
                        bolso = b_info_resp.data[0]
                        total_puestos = int(bolso['total_puestos'])
                        monto_cuota = float(bolso['monto_cuota'])
                        pozo_total = monto_cuota * total_puestos
                        
                        with st.expander(f"📦 {bolso['nombre']} (Compartido - {nivel_acceso})"):
                            st.info(f"Tienes nivel de acceso: **{nivel_acceso}**")
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Cuota", f"${monto_cuota:,.2f}")
                            col2.metric("Puestos", total_puestos)
                            col3.metric("Pozo Total", f"${pozo_total:,.2f}")
                            col4.metric("Frecuencia", bolso['frecuencia'])
                            
                            st.markdown("---")
                            fechas_quincenales = ["15-sept", "30-sept", "15-oct", "30-oct", "15-nov", "30-nov", "15-dic"]
                            resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", b_id).execute()
                            datos_existentes = resp_det.data if resp_det.data else []
                            
                            matriz_dict = {}
                            for row in datos_existentes:
                                puesto = row["nro_puesto"]
                                if puesto <= total_puestos:
                                    if puesto not in matriz_dict:
                                        matriz_dict[puesto] = {
                                            "Nro. Puesto": puesto,
                                            "Participante": row["participante"]
                                        }
                                    matriz_dict[puesto][row["fecha"]] = row["estado"]
                            
                            if matriz_dict:
                                df_matriz = pd.DataFrame(list(matriz_dict.values()))
                                opciones_estado = ["⏳ Pendiente", "🟢 Toca Cobrar", f"✅ Pagado ({email_corto})"]
                                
                                column_config_dict = {
                                    "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                                    "Participante": st.column_config.TextColumn("Participante", disabled=(nivel_acceso == "Lectura"), width="medium"),
                                }
                                for fecha in fechas_quincenales:
                                    column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                        label=fecha, options=opciones_estado, required=True, width="medium", disabled=(nivel_acceso == "Lectura")
                                    )

                                df_editado = st.data_editor(df_matriz, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_shared_{b_id}")
                                
                                if nivel_acceso == "Editor":
                                    if st.button("Guardar Cambios Compartidos", key=f"btn_save_shared_{b_id}", type="primary"):
                                        try:
                                            for index, row in df_editado.iterrows():
                                                puesto = row["Nro. Puesto"]
                                                for fecha in fechas_quincenales:
                                                    if fecha in row:
                                                        supabase.table("detalles_bolso").update({
                                                            "participante": row["Participante"],
                                                            "estado": row[fecha],
                                                            "actualizado_por": email_corto
                                                        }).eq("bolso_id", b_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                            st.success("¡Cambios guardados con éxito!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al guardar: {e}")
            else:
                st.info("No tienes ningún bolso compartido conmigo actualmente.")
        except Exception as e:
            st.error(f"Error al cargar bolsos compartidos: {e}")

    # PESTAÑA 4: Gestión de permisos
    with tab_permisos:
        st.subheader("Configuración de Colaboradores")
        st.write("Comparte el acceso a tus bolsos ingresando el correo exacto del colaborador.")
        
        with st.form("form_permisos", clear_on_submit=True):
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
                    bolso_id_seleccionado = mis_b_nombres[selected_nombre]
                    correo_limpio = correo_colaborador.strip().lower()
                    try:
                        # Guardar el permiso en la tabla 'compartidos'
                        supabase.table("compartidos").insert({
                            "bolso_id": bolso_id_seleccionado,
                            "email_colaborador": correo_limpio,
                            "nivel": nivel_permiso
                        }).execute()
                        st.success(f"¡Acceso otorgado exitosamente a {correo_limpio} para el bolso '{selected_nombre}'!")
                    except Exception as e:
                        st.error(f"Error al otorgar acceso: {e}")
                else:
                    st.warning("Verifica el correo y que tengas bolsos creados.")
