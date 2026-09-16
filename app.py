import datetime
import uuid
import extra_streamlit_components as st_cookie
import streamlit as st
import pandas as pd
from supabase import Client, create_client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión de Bolsos y Sanes",
    page_icon="💰",
    layout="wide",
)

# --- GESTOR DE COOKIES ---
cookie_manager = st_cookie.CookieManager()
device_token_cookie = cookie_manager.get(cookie="dispositivo_confiable_token_bolsos")

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

# --- RECUPERAR SESIÓN POR DISPOSITIVO (COOKIE) ---
if st.session_state["usuario"] is None:
    if device_token_cookie:
        try:
            verificacion_disp = (
                supabase.table("dispositivos_confiados")
                .select("*")
                .eq("device_token", device_token_cookie)
                .execute()
            )
            if verificacion_disp.data and len(verificacion_disp.data) > 0:
                user_id_asociado = verificacion_disp.data[0]["user_id"]
                correo_asociado = verificacion_disp.data[0].get("email", "usuario@bolsos.com")
                
                class UserDummy:
                    def __init__(self, uid, uemail):
                        self.id = uid
                        self.email = uemail

                st.session_state["usuario"] = UserDummy(user_id_asociado, correo_asociado)
                st.rerun()
        except Exception:
            pass

    # Verificación estándar de Supabase por si acaso
    try:
        session_data = supabase.auth.get_session()
        if session_data and session_data.user:
            st.session_state["usuario"] = session_data.user
    except Exception:
        pass

# --- PANTALLA DE LOGIN / REGISTRO ---
if st.session_state["usuario"] is None:
    st.title("💰 App de Gestión de Bolsos (Sanes)")
    st.markdown("Por favor, inicia sesión o regístrate para continuar.")
    
    modo = st.radio("Acción", ["Iniciar Sesión", "Registrarse"], horizontal=True)
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    
    recordar_dispositivo = st.checkbox(
        "Confiar en este dispositivo (Mantener sesión abierta solo aquí)",
        value=True
    )
    
    if modo == "Iniciar Sesión":
        if st.button("Ingresar", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["usuario"] = res.user
                    
                    if recordar_dispositivo:
                        nuevo_token = str(uuid.uuid4())
                        cookie_manager.set(
                            "dispositivo_confiable_token_bolsos", nuevo_token, max_age=31536000
                        )
                        try:
                            supabase.table("dispositivos_confiados").insert({
                                "user_id": res.user.id,
                                "device_token": nuevo_token,
                                "email": res.user.email,
                                "nombre_dispositivo": "Dispositivo Confiable Bolsos",
                            }).execute()
                        except Exception:
                            pass
                            
                    st.success("¡Bienvenido!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al iniciar sesión: Verifique sus credenciales. ({e})")
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
    
    # --- BARRA LATERAL ---
    st.sidebar.markdown(f"👤 **Usuario:** {email_corto}")
    
    if st.sidebar.button("Cerrar Sesión en este equipo"):
        if device_token_cookie:
            try:
                supabase.table("dispositivos_confiados").delete().eq(
                    "device_token", device_token_cookie
                ).execute()
            except Exception:
                pass
            cookie_manager.delete("dispositivo_confiable_token_bolsos")
            
        # Nota: Se omite supabase.auth.signOut() para evitar que afecte a otros dispositivos.
            
        st.session_state["usuario"] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Zona de Peligro")
    with st.sidebar.popover("🗑️ Eliminar mi cuenta"):
        st.warning("⚠️ **Atención:** Esta acción es totalmente irreversible. Borrará tu cuenta de forma definitiva y todos iyong bolsos y datos asociados desaparecerán para siempre.")
        confirmar_eliminacion = st.checkbox("Confirmo que deseo eliminar mi cuenta para siempre")
        
        if st.button("Eliminar Permanentemente", type="primary"):
            if confirmar_eliminacion:
                try:
                    supabase.rpc("eliminar_cuenta_usuario").execute()
                    if device_token_cookie:
                        try:
                            supabase.table("dispositivos_confiados").delete().eq(
                                "device_token", device_token_cookie
                            ).execute()
                        except:
                            pass
                        cookie_manager.delete("dispositivo_confiable_token_bolsos")
                    
                    st.session_state["usuario"] = None
                    st.success("Tu cuenta ha sido eliminada permanentemente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar la cuenta: {e}")
            else:
                st.error("Debes marcar la casilla de confirmación.")

    st.title("💼 Panel de Control de Bolsos y Sanes")

    tab_mis_bolsos, tab_crear, tab_compartidos, tab_permisos = st.tabs([
        "📂 Mis Bolsos", 
        "➕ Nuevo Bolso", 
        "🤝 Bolsos Compartidos", 
        "⚙️ Control de Permisos"
    ])

    # PESTAÑA 1: Ver tus bolsos
    with tab_mis_bolsos:
        col_cabecera_1, col_cabecera_2 = st.columns([3, 1])
        with col_cabecera_1:
            st.subheader("Tus Bolsos Activos")
        with col_cabecera_2:
            if st.button("🔄 Actualizar Tabla", key="btn_refrescar_mis_bolsos"):
                st.rerun()
        
        try:
            response = supabase.table("bolsos").select("*").eq("creador_id", usuario_actual.id).execute()
            bolsos = response.data
            
            if bolsos:
                for bolso in bolsos:
                    bolso_id = bolso['id']
                    total_puestos = int(bolso['total_puestos'])
                    monto_cuota = float(bolso['monto_cuota'])
                    pozo_total = monto_cuota * total_puestos
                    
                    tipo_moneda = bolso.get('tipo_moneda', 'Divisa')
                    tipo_tasa = bolso.get('tipo_tasa', 'N/A')
                    otra_tasa = bolso.get('otra_tasa_detalle', '')
                    
                    if tipo_moneda == "Divisa":
                        texto_modalidad = "Divisa"
                        simbolo = "$"
                    else:
                        simbolo = "Bs."
                        if tipo_tasa == "BCV (Dólar)":
                            texto_modalidad = "BS - DOLAR"
                        elif tipo_tasa == "BCV (Euro)":
                            texto_modalidad = "BS - EURO"
                        elif tipo_tasa == "Otra":
                            texto_modalidad = f"BS - OTRA: {otra_tasa.upper() if otra_tasa else 'OTRA'}"
                        else:
                            texto_modalidad = "BS"
                    
                    fechas_str = bolso.get('fechas_cronograma')
                    if not fechas_str:
                        fechas_str = "15-sept, 30-sept, 15-oct, 30-oct, 15-nov, 30-nov, 15-dic"
                    fechas_bolso = [f.strip() for f in fechas_str.split(",") if f.strip()]
                    
                    with st.expander(f"📦 {bolso['nombre']} — Cuota: {simbolo}{monto_cuota:,.2f} ({texto_modalidad})"):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Cuota por Persona", f"{simbolo}{monto_cuota:,.2f}")
                        col2.metric("Total Puestos", total_puestos)
                        col3.metric("Pozo a Recibir", f"{simbolo}{pozo_total:,.2f}")
                        col4.metric("Frecuencia", bolso['frecuencia'])
                        
                        st.markdown("---")
                        
                        col_accion_1, col_accion_2 = st.columns([1, 1])
                        
                        with col_accion_1:
                            with st.popover("✏️ Editar configuración y fechas de este Bolso"):
                                nuevo_nombre = st.text_input("Nombre del Bolso", value=bolso['nombre'], key=f"edit_nom_{bolso_id}")
                                nuevo_monto = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=monto_cuota, key=f"edit_mont_{bolso_id}")
                                
                                idx_moneda = ["Divisa", "Bolívares (Bs)"].index(tipo_moneda) if tipo_moneda in ["Divisa", "Bolívares (Bs)"] else 0
                                nueva_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], index=idx_moneda, key=f"edit_moneda_{bolso_id}")
                                
                                nueva_tasa = "N/A"
                                nuevo_detalle_tasa = ""
                                
                                if nueva_moneda == "Bolívares (Bs)":
                                    opciones_tasas = ["BCV (Dólar)", "BCV (Euro)", "Otra"]
                                    idx_tasa = opciones_tasas.index(tipo_tasa) if tipo_tasa in opciones_tasas else 0
                                    nueva_tasa = st.selectbox("¿A qué tasa?", opciones_tasas, index=idx_tasa, key=f"edit_tasa_{bolso_id}")
                                    
                                    if nueva_tasa == "Otra":
                                        nuevo_detalle_tasa = st.text_input("Especifique cuál tasa", value=otra_tasa, key=f"edit_otra_{bolso_id}")
                                
                                idx_freq = ["Quincenal", "Semanal", "Mensual"].index(bolso['frecuencia']) if bolso['frecuencia'] in ["Quincenal", "Semanal", "Mensual"] else 0
                                nueva_freq = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"], index=idx_freq, key=f"edit_freq_{bolso_id}")
                                nuevo_puestos = st.number_input("Número Total de Puestos", min_value=1, value=total_puestos, step=1, key=f"edit_puest_{bolso_id}")
                                
                                st.markdown("---")
                                st.markdown("📅 **Selecciona la fecha para cada Puesto:**")
                                
                                fechas_editadas = []
                                for p in range(1, int(nuevo_puestos) + 1):
                                    fecha_default = datetime.date.today()
                                    if p - 1 < len(fechas_bolso):
                                        try:
                                            partes = fechas_bolso[p-1].split("-")
                                            if len(partes) == 2:
                                                meses = {"ene":1, "feb":2, "mar":3, "abr":4, "may":5, "jun":6, "jul":7, "ago":8, "sept":9, "oct":10, "nov":11, "dic":12}
                                                m_num = meses.get(partes[1].lower(), 1)
                                                fecha_default = datetime.date(datetime.date.today().year, m_num, int(partes[0]))
                                        except:
                                            pass
                                            
                                    f_sel = st.date_input(f"Fecha para Puesto {p}", value=fecha_default, key=f"edit_date_{bolso_id}_{p}")
                                    fechas_editadas.append(f_sel.strftime("%d-%b"))
                                
                                if st.button("Guardar Cambios Generales", key=f"btn_edit_gen_{bolso_id}", type="primary"):
                                    try:
                                        nuevas_fechas_str = ", ".join(fechas_editadas)
                                        supabase.table("bolsos").update({
                                            "nombre": nuevo_nombre,
                                            "monto_cuota": nuevo_monto,
                                            "tipo_moneda": nueva_moneda,
                                            "tipo_tasa": nueva_tasa,
                                            "otra_tasa_detalle": nuevo_detalle_tasa,
                                            "frecuencia": nueva_freq,
                                            "total_puestos": int(nuevo_puestos),
                                            "fechas_cronograma": nuevas_fechas_str
                                        }).eq("id", bolso_id).execute()
                                        st.success("¡Configuración actualizada con éxito!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al actualizar: {e}")

                        with col_accion_2:
                            with st.popover("🗑️ Eliminar este Bolso"):
                                st.error("⚠️ Esta acción borrará el bolso y todos sus datos de forma permanente.")
                                confirmar_borrado_propietario = st.checkbox("Confirmo que deseo eliminar este bolso permanentemente", key=f"chk_del_{bolso_id}")
                                if st.button("Eliminar Bolso Definitivamente", key=f"btn_delete_propietario_{bolso_id}", type="primary"):
                                    if confirmar_borrado_propietario:
                                        try:
                                            supabase.table("detalles_bolso").delete().eq("bolso_id", bolso_id).execute()
                                            supabase.table("compartidos").delete().eq("bolso_id", bolso_id).execute()
                                            supabase.table("bolsos").delete().eq("id", bolso_id).execute()
                                            st.success("¡Bolso eliminado con éxito!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al eliminar el bolso: {e}")
                                    else:
                                        st.error("Debes marcar la casilla de confirmación.")
                        
                        st.markdown("---")
                        st.markdown("### 🗓️ Cronograma, Participantes y Estados")
                        
                        resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", bolso_id).execute()
                        datos_existentes = resp_det.data if resp_det.data else []
                        
                        if not datos_existentes or len(set(r["nro_puesto"] for r in datos_existentes)) != total_puestos:
                            for i in range(1, total_puestos + 1):
                                for idx, fecha in enumerate(fechas_bolso):
                                    existe = any(d["nro_puesto"] == i and d["fecha"] == fecha for d in datos_existentes)
                                    if not existe:
                                        estado_inicial = "🟢 Recibe Pozo" if (idx + 1) == i else "⏳ Pendiente"
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
                            fecha = row["fecha"]
                            if puesto <= total_puestos and fecha in fechas_bolso:
                                if puesto not in matriz_dict:
                                    matriz_dict[puesto] = {
                                        "Nro. Puesto": puesto,
                                        "Participante": row["participante"]
                                    }
                                matriz_dict[puesto][fecha] = row["estado"]
                        
                        if matriz_dict:
                            lista_ordenada = [matriz_dict[p] for p in sorted(matriz_dict.keys()) if p in matriz_dict]
                            df_matriz = pd.DataFrame(lista_ordenada)
                            
                            columnas_fijas = ["Nro. Puesto", "Participante"] + fechas_bolso
                            for col in fechas_bolso:
                                if col not in df_matriz.columns:
                                    df_matriz[col] = "⏳ Pendiente"
                            df_matriz = df_matriz[[c for c in columnas_fijas if c in df_matriz.columns]]

                            opciones_base = ["⏳ Pendiente", "🟢 Recibe Pozo", f"✅ Pagado (por {email_corto})"]
                            
                            column_config_dict = {
                                "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                                "Participante": st.column_config.TextColumn("Participante", width="medium"),
                            }
                            
                            for fecha in fechas_bolso:
                                valores_existentes = df_matriz[fecha].dropna().unique().tolist() if fecha in df_matriz.columns else []
                                opciones_estado = list(dict.fromkeys(opciones_base + valores_existentes))
                                column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                    label=fecha, options=opciones_estado, required=True, width="medium"
                                )

                            df_editado = st.data_editor(df_matriz, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_{bolso_id}")
                            
                            if st.button("Guardar Cambios del Cronograma", key=f"btn_save_{bolso_id}", type="primary"):
                                try:
                                    for index, row in df_editado.iterrows():
                                        puesto = row["Nro. Puesto"]
                                        nombre_part = row["Participante"]
                                        for fecha in fechas_bolso:
                                            if fecha in row:
                                                check_f = supabase.table("detalles_bolso").select("id").eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                                if check_f.data:
                                                    supabase.table("detalles_bolso").update({
                                                        "participante": nombre_part,
                                                        "estado": row[fecha],
                                                        "actualizado_por": email_corto
                                                    }).eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                                else:
                                                    supabase.table("detalles_bolso").insert({
                                                        "bolso_id": bolso_id,
                                                        "nro_puesto": puesto,
                                                        "participante": nombre_part,
                                                        "fecha": fecha,
                                                        "estado": row[fecha],
                                                        "actualizado_por": email_corto
                                                    }).execute()
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
        
        nombre_bolso = st.text_input("Nombre del Bolso", key="new_nombre")
        monto_cuota = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=50.0, key="new_monto")
        
        tipo_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], key="new_moneda")
        
        tipo_tasa = "N/A"
        otra_tasa_detalle = ""
        
        if tipo_moneda == "Bolívares (Bs)":
            tipo_tasa = st.selectbox("¿A qué tasa?", ["BCV (Dólar)", "BCV (Euro)", "Otra"], key="new_tasa")
            if tipo_tasa == "Otra":
                otra_tasa_detalle = st.text_input("Especifique cuál tasa", key="new_otra_tasa")
        
        frecuencia = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"], key="new_freq")
        total_puestos = st.number_input("Número Total de Puestos", min_value=1, value=7, step=1, key="new_puestos")
        
        st.markdown("---")
        st.markdown("📅 **Selecciona la fecha correspondiente para cada Puesto:**")
        
        fechas_seleccionadas = []
        for i in range(1, int(total_puestos) + 1):
            f = st.date_input(f"Fecha para el Puesto {i}", key=f"fecha_puesto_{i}")
            fechas_seleccionadas.append(f.strftime("%d-%b"))
        
        if st.button("Guardar Bolso", type="primary", key="btn_guardar_nuevo_bolso"):
            if nombre_bolso:
                try:
                    fechas_str = ", ".join(fechas_seleccionadas)
                    supabase.table("bolsos").insert({
                        "nombre": nombre_bolso,
                        "monto_cuota": monto_cuota,
                        "tipo_moneda": tipo_moneda,
                        "tipo_tasa": tipo_tasa,
                        "otra_tasa_detalle": otra_tasa_detalle,
                        "frecuencia": frecuencia,
                        "total_puestos": int(total_puestos),
                        "creador_id": usuario_actual.id,
                        "fechas_cronograma": fechas_str
                    }).execute()
                    
                    st.success(f"¡Bolso '{nombre_bolso}' creado exitosamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en Supabase: {e}")
            else:
                st.warning("Por favor ingresa al menos el nombre del bolso.")

    # PESTAÑA 3: Bolsos compartidos conmigo
    with tab_compartidos:
        col_comp_1, col_comp_2 = st.columns([3, 1])
        with col_comp_1:
            st.subheader("🤝 Bolsos Compartidos Conmigo")
        with col_comp_2:
            if st.button("🔄 Actualizar Tabla", key="btn_refrescar_compartidos"):
                st.rerun()

        try:
            resp_comp = supabase.table("compartidos").select("bolso_id, nivel").eq("email_colaborador", email_usuario).execute()
            shared_records = resp_comp.data if resp_comp.data else []
            
            if shared_records:
                bolsos_vistos = set()
                
                for idx, rec in enumerate(shared_records):
                    b_id = rec["bolso_id"]
                    if b_id in bolsos_vistos:
                        continue
                    bolsos_vistos.add(b_id)
                    
                    nivel_acceso = rec["nivel"]
                    
                    b_info_resp = supabase.table("bolsos").select("*").eq("id", b_id).execute()
                    if b_info_resp.data:
                        bolso = b_info_resp.data[0]
                        total_puestos = int(bolso['total_puestos'])
                        monto_cuota = float(bolso['monto_cuota'])
                        pozo_total = monto_cuota * total_puestos
                        
                        tipo_moneda = bolso.get('tipo_moneda', 'Divisa')
                        tipo_tasa = bolso.get('tipo_tasa', 'N/A')
                        otra_tasa = bolso.get('otra_tasa_detalle', '')
                        
                        if tipo_moneda == "Divisa":
                            texto_modalidad = "Divisa"
                            simbolo = "$"
                        else:
                            simbolo = "Bs."
                            if tipo_tasa == "BCV (Dólar)":
                                texto_modalidad = "BS - DOLAR"
                            elif tipo_tasa == "BCV (Euro)":
                                texto_modalidad = "BS - EURO"
                            elif tipo_tasa == "Otra":
                                texto_modalidad = f"BS - OTRA: {otra_tasa.upper() if otra_tasa else 'OTRA'}"
                            else:
                                texto_modalidad = "BS"
                        
                        fechas_str = bolso.get('fechas_cronograma')
                        if not fechas_str:
                            fechas_str = "15-sept, 30-sept, 15-oct, 30-oct, 15-nov, 30-nov, 15-dic"
                        fechas_bolso = [f.strip() for f in fechas_str.split(",") if f.strip()]
                        
                        with st.expander(f"📦 {bolso['nombre']} (Compartido - {nivel_acceso}) — Cuota: {simbolo}{monto_cuota:,.2f} ({texto_modalidad})"):
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Cuota", f"{simbolo}{monto_cuota:,.2f}")
                            col2.metric("Puestos", total_puestos)
                            col3.metric("Pozo Total", f"{simbolo}{pozo_total:,.2f}")
                            col4.metric("Frecuencia", bolso['frecuencia'])
                            
                            st.markdown("---")
                            
                            if nivel_acceso == "Editor":
                                with st.popover("✏️ Editar configuración y fechas de este Bolso"):
                                    nuevo_nombre = st.text_input("Nombre del Bolso", value=bolso['nombre'], key=f"edit_shared_nom_{b_id}")
                                    nuevo_monto = st.number_input("Monto por Cuota", min_value=0.0, format="%.2f", value=monto_cuota, key=f"edit_shared_mont_{b_id}")
                                    
                                    idx_moneda = ["Divisa", "Bolívares (Bs)"].index(tipo_moneda) if tipo_moneda in ["Divisa", "Bolívares (Bs)"] else 0
                                    nueva_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], index=idx_moneda, key=f"edit_shared_moneda_{b_id}")
                                    
                                    nueva_tasa = "N/A"
                                    nuevo_detalle_tasa = ""
                                    
                                    if nueva_moneda == "Bolívares (Bs)":
                                        opciones_tasas = ["BCV (Dólar)", "BCV (Euro)", "Otra"]
                                        idx_tasa = opciones_tasas.index(tipo_tasa) if tipo_tasa in opciones_tasas else 0
                                        nueva_tasa = st.selectbox("¿A qué tasa?", opciones_tasas, index=idx_tasa, key=f"edit_shared_tasa_{b_id}")
                                        
                                        if nueva_tasa == "Otra":
                                            nuevo_detalle_tasa = st.text_input("Especifique cuál tasa", value=otra_tasa, key=f"edit_shared_otra_{b_id}")
                                    
                                    idx_freq = ["Quincenal", "Semanal", "Mensual"].index(bolso['frecuencia']) if bolso['frecuencia'] in ["Quincenal", "Semanal", "Mensual"] else 0
                                    nueva_freq = st.selectbox("Frecuencia", ["Quincenal", "Semanal", "Mensual"], index=idx_freq, key=f"edit_shared_freq_{b_id}")
                                    nuevo_puestos = st.number_input("Número Total de Puestos", min_value=1, value=total_puestos, step=1, key=f"edit_shared_puest_{b_id}")
                                    
                                    st.markdown("---")
                                    st.markdown("📅 **Selecciona la fecha para cada Puesto:**")
                                    
                                    fechas_editadas = []
                                    for p in range(1, int(nuevo_puestos) + 1):
                                        fecha_default = datetime.date.today()
                                        if p - 1 < len(fechas_bolso):
                                            try:
                                                partes = fechas_bolso[p-1].split("-")
                                                if len(partes) == 2:
                                                    meses = {"ene":1, "feb":2, "mar":3, "abr":4, "may":5, "jun":6, "jul":7, "ago":8, "sept":9, "oct":10, "nov":11, "dic":12}
                                                    m_num = meses.get(partes[1].lower(), 1)
                                                    fecha_default = datetime.date(datetime.date.today().year, m_num, int(partes[0]))
                                            except:
                                                pass
                                                
                                        f_sel = st.date_input(f"Fecha para Puesto {p}", value=fecha_default, key=f"edit_shared_date_{b_id}_{p}")
                                        fechas_editadas.append(f_sel.strftime("%d-%b"))
                                    
                                    if st.button("Guardar Cambios Generales", key=f"btn_edit_gen_shared_{b_id}", type="primary"):
                                        try:
                                            nuevas_fechas_str = ", ".join(fechas_editadas)
                                            supabase.table("bolsos").update({
                                                "nombre": nuevo_nombre,
                                                "monto_cuota": nuevo_monto,
                                                "tipo_moneda": nueva_moneda,
                                                "tipo_tasa": nueva_tasa,
                                                "otra_tasa_detalle": nuevo_detalle_tasa,
                                                "frecuencia": nueva_freq,
                                                "total_puestos": int(nuevo_puestos),
                                                "fechas_cronograma": nuevas_fechas_str
                                            }).eq("id", b_id).execute()
                                            st.success("¡Configuración actualizada con éxito!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al actualizar: {e}")

                            with st.popover("⚙️ Salir / Dejar de ver este Bolso"):
                                st.markdown("🗑️ **Remover de tus compartidos**")
                                st.write("Si ya no deseas participar o ver este bolso compartido, puedes removerlo de tu lista.")
                                chk_salir = st.checkbox("Confirmo que deseo salir de este bolso compartido", key=f"chk_salir_{b_id}")
                                if st.button("Remover de mis compartidos", key=f"btn_salir_{b_id}", type="primary"):
                                    if chk_salir:
                                        try:
                                            supabase.table("compartidos").delete().eq("bolso_id", b_id).eq("email_colaborador", email_usuario).execute()
                                            st.success("Te has removido de este bolso exitosamente.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al salir del bolso: {e}")
                                    else:
                                        st.error("Debes marcar la casilla de confirmación.")

                            st.markdown("---")
                            resp_det = supabase.table("detalles_bolso").select("*").eq("bolso_id", b_id).execute()
                            datos_existentes = resp_det.data if resp_det.data else []
                            
                            matriz_dict = {}
                            for row in datos_existentes:
                                puesto = row["nro_puesto"]
                                fecha = row["fecha"]
                                if puesto <= total_puestos and fecha in fechas_bolso:
                                    if puesto not in matriz_dict:
                                        matriz_dict[puesto] = {
                                            "Nro. Puesto": puesto,
                                            "Participante": row["participante"]
                                        }
                                    matriz_dict[puesto][fecha] = row["estado"]
                            
                            if matriz_dict:
                                lista_ordenada = [matriz_dict[p] for p in sorted(matriz_dict.keys()) if p in matriz_dict]
                                df_matriz = pd.DataFrame(lista_ordenada)
                                
                                columnas_fijas = ["Nro. Puesto", "Participante"] + fechas_bolso
                                for col in fechas_bolso:
                                    if col not in df_matriz.columns:
                                        df_matriz[col] = "⏳ Pendiente"
                                df_matriz = df_matriz[[c for c in columnas_fijas if c in df_matriz.columns]]

                                es_solo_lectura = (nivel_acceso == "Lectura")
                                
                                opciones_base = ["⏳ Pendiente", "🟢 Recibe Pozo", f"✅ Pagado (por {email_corto})"]
                                
                                column_config_dict = {
                                    "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                                    "Participante": st.column_config.TextColumn("Participante", disabled=es_solo_lectura, width="medium"),
                                }
                                
                                for fecha in fechas_bolso:
                                    valores_existentes = df_matriz[fecha].dropna().unique().tolist() if fecha in df_matriz.columns else []
                                    opciones_estado = list(dict.fromkeys(opciones_base + valores_existentes))
                                    column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                        label=fecha, options=opciones_estado, required=True, width="medium", disabled=es_solo_lectura
                                    )

                                df_editado = st.data_editor(df_matriz, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_shared_{b_id}_{idx}")
                                
                                if nivel_acceso == "Editor":
                                    if st.button("Guardar Cambios Compartidos", key=f"btn_save_shared_{b_id}_{idx}", type="primary"):
                                        try:
                                            for index, row in df_editado.iterrows():
                                                puesto = row["Nro. Puesto"]
                                                for fecha in fechas_bolso:
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
                        resp_check = supabase.table("compartidos").select("*").eq("bolso_id", bolso_id_seleccionado).eq("email_colaborador", correo_limpio).execute()
                        
                        if resp_check.data and len(resp_check.data) > 0:
                            st.warning(f"⚠️ El usuario **{correo_limpio}** ya tiene acceso a este bolso.")
                        else:
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
