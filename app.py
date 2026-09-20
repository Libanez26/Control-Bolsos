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

# --- INICIALIZAR TASAS INTERACTIVAS EN SESIÓN ---
if "tasa_bcv_dolar_val" not in st.session_state:
    st.session_state["tasa_bcv_dolar_val"] = 36.50
if "tasa_bcv_euro_val" not in st.session_state:
    st.session_state["tasa_bcv_euro_val"] = 40.00
if "tasa_otra_val" not in st.session_state:
    st.session_state["tasa_otra_val"] = 38.00

# --- RECUPERAR Y VALIDAR SESIÓN POR DISPOSITIVO ---
if st.session_state["usuario"] is None and device_token_cookie:
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
        else:
            cookie_manager.delete("dispositivo_confiable_token_bolsos")
            st.session_state["usuario"] = None
    except Exception:
        st.session_state["usuario"] = None

# --- PANTALLA DE LOGIN / REGISTRO ---
if st.session_state["usuario"] is None:
    st.title("💰 Gestión de Bolsos (Sanes)")
    st.markdown("Por favor, inicia sesión o regístrate para continuar.")
    
    modo = st.radio("Acción", ["Iniciar Sesión", "Registrarse"], horizontal=True, key="main_modo_auth")
    email = st.text_input("Correo electrónico", key="main_email_auth")
    password = st.text_input("Contraseña", type="password", key="main_pass_auth")
    
    recordar_dispositivo = st.checkbox(
        "Confiar en este dispositivo (Mantener sesión abierta solo aquí)",
        value=True,
        key="main_chk_dispositivo"
    )
    
    if modo == "Iniciar Sesión":
        if st.button("Ingresar", type="primary", key="btn_ingresar_auth"):
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
        if st.button("Crear Cuenta", type="primary", key="btn_crear_auth"):
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
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💱 Tasas Globales de Referencia")
    st.sidebar.markdown("Valores orientativos rápidos:")
    st.session_state["tasa_bcv_dolar_val"] = st.sidebar.number_input("Tasa BCV Dólar (Bs/USD)", min_value=0.0, format="%.2f", value=st.session_state["tasa_bcv_dolar_val"])
    st.session_state["tasa_bcv_euro_val"] = st.sidebar.number_input("Tasa BCV Euro (Bs/EUR)", min_value=0.0, format="%.2f", value=st.session_state["tasa_bcv_euro_val"])
    st.session_state["tasa_otra_val"] = st.sidebar.number_input("Tasa Personalizada/Otra (Bs)", min_value=0.0, format="%.2f", value=st.session_state["tasa_otra_val"])

    st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar Sesión en este equipo", key="btn_sidebar_cerrar"):
        if device_token_cookie:
            try:
                supabase.table("dispositivos_confiados").delete().eq(
                    "device_token", device_token_cookie
                ).execute()
            except Exception:
                pass
            cookie_manager.delete("dispositivo_confiable_token_bolsos")
            
        st.session_state["usuario"] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Zona de Peligro")
    with st.sidebar.popover("🗑️ Eliminar mi cuenta"):
        st.warning("⚠️ **Atención:** Esta acción es totalmente irreversible. Borrará tu cuenta de forma definitiva y todos tus bolsos y datos asociados desaparecerán para siempre.")
        confirmar_eliminacion = st.checkbox("Confirmo que deseo eliminar mi cuenta para siempre", key="chk_confirma_eliminar_cuenta")
        
        if st.button("Eliminar Permanentemente", type="primary", key="btn_ejecutar_eliminar_cuenta"):
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

    # DEFINICIÓN DE PESTAÑAS PRINCIPALES
    tab_mis_bolsos, tab_crear, tab_compartidos, tab_permisos, tab_divisas = st.tabs([
        "📦 Mis Bolsos", 
        "➕ Crear Bolso", 
        "🤝 Compartidos", 
        "⚙️ Permisos", 
        "💱 Divisas"
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
                    
                    tipo_moneda = bolso.get('tipo_moneda', 'Divisa')
                    tipo_tasa = bolso.get('tipo_tasa', 'N/A')
                    otra_tasa = bolso.get('otra_tasa_detalle', '')
                    tasa_guardada = bolso.get('tasa_valor')
                    
                    if tasa_guardada is not None:
                        tasa_aplicada = float(tasa_guardada)
                    else:
                        if tipo_tasa == "BCV (Dólar)":
                            tasa_aplicada = st.session_state["tasa_bcv_dolar_val"]
                        elif tipo_tasa == "BCV (Euro)":
                            tasa_aplicada = st.session_state["tasa_bcv_euro_val"]
                        elif tipo_tasa == "Otra":
                            tasa_aplicada = st.session_state["tasa_otra_val"]
                        else:
                            tasa_aplicada = 1.0

                    if tipo_moneda == "Divisa":
                        simbolo = "$"
                        monto_cobro_efectivo = monto_cuota
                        pozo_total = monto_cuota * total_puestos
                        texto_modalidad = "Divisa ($)"
                    else:
                        simbolo = "Bs."
                        monto_cobro_efectivo = monto_cuota * tasa_aplicada
                        pozo_total = monto_cobro_efectivo * total_puestos
                        if tipo_tasa == "BCV (Dólar)":
                            texto_modalidad = f"BS (Tasa BCV Dólar: {tasa_aplicada:,.2f})"
                        elif tipo_tasa == "BCV (Euro)":
                            texto_modalidad = f"BS (Tasa BCV Euro: {tasa_aplicada:,.2f})"
                        elif tipo_tasa == "Otra":
                            texto_modalidad = f"BS ({otra_tasa.upper() if otra_tasa else 'OTRA'}: {tasa_aplicada:,.2f})"
                        else:
                            texto_modalidad = "BS"
                    
                    fechas_str = bolso.get('fechas_cronograma')
                    if not fechas_str:
                        fechas_str = "15-sept, 30-sept, 15-oct, 30-oct, 15-nov, 30-nov, 15-dic"
                    fechas_bolso = [f.strip() for f in fechas_str.split(",") if f.strip()]
                    
                    titulo_expander = f"📦 {bolso['nombre']} — Base: ${monto_cuota:,.2f} USD | Cobro: {simbolo}{monto_cobro_efectivo:,.2f} ({texto_modalidad})"
                    with st.expander(titulo_expander):
                        col1, col2, col3, col4 = st.columns(4)
                        if tipo_moneda == "Bolívares (Bs)":
                            col1.metric("Cuota Base (USD)", f"${monto_cuota:,.2f}", f"Equiv. Bs: {monto_cobro_efectivo:,.2f}")
                        else:
                            col1.metric("Cuota por Persona", f"${monto_cuota:,.2f}")
                        col2.metric("Total Puestos", total_puestos)
                        col3.metric("Pozo a Recibir", f"{simbolo}{pozo_total:,.2f}")
                        col4.metric("Frecuencia", bolso['frecuencia'])
                        
                        st.markdown("---")
                        
                        col_accion_1, col_accion_2 = st.columns([1, 1])
                        
                        with col_accion_1:
                            with st.popover("✏️ Editar configuración y fechas de este Bolso"):
                                nuevo_nombre = st.text_input("Nombre del Bolso", value=bolso['nombre'], key=f"edit_nom_{bolso_id}")
                                nuevo_monto = st.number_input("Monto Base por Cuota (en Dólares $)", min_value=0.0, format="%.2f", value=monto_cuota, key=f"edit_mont_{bolso_id}")
                                
                                idx_moneda = ["Divisa", "Bolívares (Bs)"].index(tipo_moneda) if tipo_moneda in ["Divisa", "Bolívares (Bs)"] else 0
                                nueva_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], index=idx_moneda, key=f"edit_moneda_{bolso_id}")
                                
                                nueva_tasa = "N/A"
                                nuevo_detalle_tasa = ""
                                nuevo_tasa_valor = 1.0
                                
                                if nueva_moneda == "Bolívares (Bs)":
                                    opciones_tasas = ["BCV (Dólar)", "BCV (Euro)", "Otra"]
                                    idx_tasa = opciones_tasas.index(tipo_tasa) if tipo_tasa in opciones_tasas else 0
                                    nueva_tasa = st.selectbox("¿A qué tasa?", opciones_tasas, index=idx_tasa, key=f"edit_tasa_{bolso_id}")
                                    
                                    if nueva_tasa == "Otra":
                                        nuevo_detalle_tasa = st.text_input("Especifique cuál tasa", value=otra_tasa, key=f"edit_otra_{bolso_id}")
                                    
                                    val_tasa_default = float(tasa_guardada) if tasa_guardada is not None else tasa_aplicada
                                    nuevo_tasa_valor = st.number_input("Valor actual de la Tasa (Bs)", min_value=0.0, format="%.2f", value=val_tasa_default, key=f"edit_tasa_val_{bolso_id}")
                                
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
                                            "tasa_valor": nuevo_tasa_valor,
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
                        st.markdown("### 🗓️ Cronograma, Participantes y Estados con Notas")
                        
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
                                            "nota": "",
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
                                matriz_dict[puesto][f"Nota | {fecha}"] = row.get("nota", "")
                        
                        if matriz_dict:
                            lista_ordenada = [matriz_dict[p] for p in sorted(matriz_dict.keys()) if p in matriz_dict]
                            df_matriz = pd.DataFrame(lista_ordenada)
                            
                            # Construir columnas fijas asegurando las de estado y nota
                            columnas_fijas = ["Nro. Puesto", "Participante"]
                            for fecha in fechas_bolso:
                                columnas_fijas.append(fecha)
                                columnas_fijas.append(f"Nota | {fecha}")

                            for col in fechas_bolso:
                                if col not in df_matriz.columns:
                                    df_matriz[col] = "⏳ Pendiente"
                            for fecha in fechas_bolso:
                                nota_col = f"Nota | {fecha}"
                                if nota_col not in df_matriz.columns:
                                    df_matriz[nota_col] = ""

                            df_matriz = df_matriz[[c for c in columnas_fijas if c in df_matriz.columns]]

                            # --- SELECTOR DE VISIBILIDAD DE COLUMNAS (OJITO) ---
                            with st.popover("👁️ Ocultar / Mostrar Fechas y Notas"):
                                st.markdown("**Selecciona las fechas visibles:**")
                                vis_cols = {}
                                for col in fechas_bolso:
                                    vis_cols[col] = st.checkbox(f"📅 {col}", value=True, key=f"chk_col_{bolso_id}_{col}")
                            
                            fechas_visibles = [col for col in fechas_bolso if vis_cols.get(col, True)]
                            
                            # Armar dinámicamente qué mostrar
                            columnas_a_mostrar = ["Nro. Puesto", "Participante"]
                            for fecha in fechas_visibles:
                                columnas_a_mostrar.append(fecha)
                                columnas_a_mostrar.append(f"Nota | {fecha}")

                            df_matriz_filtrado = df_matriz[[c for c in columnas_a_mostrar if c in df_matriz.columns]]

                            opciones_base = ["⏳ Pendiente", "🟢 Recibe Pozo", f"✅ Cobrado (por {email_corto})"]
                            
                            column_config_dict = {
                                "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                                "Participante": st.column_config.TextColumn("Participante", width="medium"),
                            }
                            
                            for fecha in fechas_visibles:
                                if fecha in df_matriz_filtrado.columns:
                                    serie_fecha = df_matriz_filtrado[fecha]
                                    if isinstance(serie_fecha, pd.DataFrame):
                                        serie_fecha = serie_fecha.iloc[:, 0]
                                    valores_existentes = serie_fecha.dropna().unique().tolist()
                                else:
                                    valores_existentes = []
                                    
                                opciones_estado = list(dict.fromkeys(opciones_base + valores_existentes))
                                column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                    label=f"Estado {fecha}", options=opciones_estado, required=True, width="medium"
                                )
                                
                                # Configurar la columna de notas como un campo de texto
                                nota_col_key = f"Nota | {fecha}"
                                column_config_dict[nota_col_key] = st.column_config.TextColumn(
                                    label=f"Nota {fecha}", width="medium"
                                )

                            df_editado = st.data_editor(df_matriz_filtrado, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_{bolso_id}")
                            
                            if st.button("Guardar Cambios del Cronograma", key=f"btn_save_{bolso_id}", type="primary"):
                                try:
                                    for index, row in df_editado.iterrows():
                                        puesto = row["Nro. Puesto"]
                                        nombre_part = row["Participante"]
                                        for fecha in fechas_visibles:
                                            estado_val = row.get(fecha, "⏳ Pendiente")
                                            nota_val = row.get(f"Nota | {fecha}", "")
                                            
                                            check_f = supabase.table("detalles_bolso").select("id").eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                            if check_f.data:
                                                supabase.table("detalles_bolso").update({
                                                    "participante": nombre_part,
                                                    "estado": estado_val,
                                                    "nota": nota_val,
                                                    "actualizado_por": email_corto
                                                }).eq("bolso_id", bolso_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                            else:
                                                supabase.table("detalles_bolso").insert({
                                                    "bolso_id": bolso_id,
                                                    "nro_puesto": puesto,
                                                    "participante": nombre_part,
                                                    "fecha": fecha,
                                                    "estado": estado_val,
                                                    "nota": nota_val,
                                                    "actualizado_por": email_corto
                                                }).execute()
                                    st.success("¡Cambios y notas guardados exitosamente!")
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
        
        tipo_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], key="new_moneda")
        
        tipo_tasa = "N/A"
        otra_tasa_detalle = ""
        tasa_valor = 1.0
        
        if tipo_moneda == "Bolívares (Bs)":
            st.info("💡 **Nota:** El valor base del bolso se define en **Dólares ($)**, pero se calculará y cobrará en **Bolívares (Bs)** según la tasa diaria que indiques.")
            monto_cuota = st.number_input("Monto Base por Cuota (en Dólares $)", min_value=0.0, format="%.2f", value=50.0, key="new_monto")
            tipo_tasa = st.selectbox("¿A qué tasa se cobrará?", ["BCV (Dólar)", "BCV (Euro)", "Otra"], key="new_tasa")
            if tipo_tasa == "Otra":
                otra_tasa_detalle = st.text_input("Especifique cuál tasa", key="new_otra_tasa")
            
            tasa_def = st.session_state["tasa_bcv_euro_val"] if tipo_tasa == "BCV (Euro)" else st.session_state["tasa_bcv_dolar_val"]
            tasa_valor = st.number_input("Valor de la Tasa del Día (Bs)", min_value=0.0, format="%.2f", value=tasa_def, key="new_tasa_valor")
        else:
            monto_cuota = st.number_input("Monto por Cuota ($)", min_value=0.0, format="%.2f", value=50.0, key="new_monto")
        
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
                        "tasa_valor": tasa_valor,
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
                        
                        tipo_moneda = bolso.get('tipo_moneda', 'Divisa')
                        tipo_tasa = bolso.get('tipo_tasa', 'N/A')
                        otra_tasa = bolso.get('otra_tasa_detalle', '')
                        tasa_guardada = bolso.get('tasa_valor')
                        
                        if tasa_guardada is not None:
                            tasa_aplicada = float(tasa_guardada)
                        else:
                            if tipo_tasa == "BCV (Dólar)":
                                tasa_aplicada = st.session_state["tasa_bcv_dolar_val"]
                            elif tipo_tasa == "BCV (Euro)":
                                tasa_aplicada = st.session_state["tasa_bcv_euro_val"]
                            elif tipo_tasa == "Otra":
                                tasa_aplicada = st.session_state["tasa_otra_val"]
                            else:
                                tasa_aplicada = 1.0

                        if tipo_moneda == "Divisa":
                            simbolo = "$"
                            monto_cobro_efectivo = monto_cuota
                            pozo_total = monto_cuota * total_puestos
                            texto_modalidad = "Divisa ($)"
                        else:
                            simbolo = "Bs."
                            monto_cobro_efectivo = monto_cuota * tasa_aplicada
                            pozo_total = monto_cobro_efectivo * total_puestos
                            if tipo_tasa == "BCV (Dólar)":
                                texto_modalidad = f"BS (Tasa BCV Dólar: {tasa_aplicada:,.2f})"
                            elif tipo_tasa == "BCV (Euro)":
                                texto_modalidad = f"BS (Tasa BCV Euro: {tasa_aplicada:,.2f})"
                            elif tipo_tasa == "Otra":
                                texto_modalidad = f"BS ({otra_tasa.upper() if otra_tasa else 'OTRA'}: {tasa_aplicada:,.2f})"
                            else:
                                texto_modalidad = "BS"
                        
                        fechas_str = bolso.get('fechas_cronograma')
                        if not fechas_str:
                            fechas_str = "15-sept, 30-sept, 15-oct, 30-oct, 15-nov, 30-nov, 15-dic"
                        fechas_bolso = [f.strip() for f in fechas_str.split(",") if f.strip()]
                        
                        titulo_exp_shared = f"📦 {bolso['nombre']} (Compartido - {nivel_acceso}) — Base: ${monto_cuota:,.2f} USD | Cobro: {simbolo}{monto_cobro_efectivo:,.2f} ({texto_modalidad})"
                        with st.expander(titulo_exp_shared):
                            col1, col2, col3, col4 = st.columns(4)
                            if tipo_moneda == "Bolívares (Bs)":
                                col1.metric("Cuota Base (USD)", f"${monto_cuota:,.2f}", f"Equiv. Bs: {monto_cobro_efectivo:,.2f}")
                            else:
                                col1.metric("Cuota", f"${monto_cuota:,.2f}")
                            col2.metric("Puestos", total_puestos)
                            col3.metric("Pozo Total", f"{simbolo}{pozo_total:,.2f}")
                            col4.metric("Frecuencia", bolso['frecuencia'])
                            
                            st.markdown("---")
                            
                            if nivel_acceso == "Editor":
                                with st.popover("✏️ Editar configuración y fechas de este Bolso"):
                                    nuevo_nombre = st.text_input("Nombre del Bolso", value=bolso['nombre'], key=f"edit_shared_nom_{b_id}")
                                    nuevo_monto = st.number_input("Monto Base por Cuota (en Dólares $)", min_value=0.0, format="%.2f", value=monto_cuota, key=f"edit_shared_mont_{b_id}")
                                    
                                    idx_moneda = ["Divisa", "Bolívares (Bs)"].index(tipo_moneda) if tipo_moneda in ["Divisa", "Bolívares (Bs)"] else 0
                                    nueva_moneda = st.selectbox("Tipo de Moneda", ["Divisa", "Bolívares (Bs)"], index=idx_moneda, key=f"edit_shared_moneda_{b_id}")
                                    
                                    nueva_tasa = "N/A"
                                    nuevo_detalle_tasa = ""
                                    nuevo_tasa_valor = 1.0
                                    
                                    if nueva_moneda == "Bolívares (Bs)":
                                        opciones_tasas = ["BCV (Dólar)", "BCV (Euro)", "Otra"]
                                        idx_tasa = opciones_tasas.index(tipo_tasa) if tipo_tasa in opciones_tasas else 0
                                        nueva_tasa = st.selectbox("¿A qué tasa?", opciones_tasas, index=idx_tasa, key=f"edit_shared_tasa_{b_id}")
                                        
                                        if nueva_tasa == "Otra":
                                            nuevo_detalle_tasa = st.text_input("Especifique cuál tasa", value=otra_tasa, key=f"edit_shared_otra_{b_id}")
                                        
                                        val_tasa_default = float(tasa_guardada) if tasa_guardada is not None else tasa_aplicada
                                        nuevo_tasa_valor = st.number_input("Valor actual de la Tasa (Bs)", min_value=0.0, format="%.2f", value=val_tasa_default, key=f"edit_shared_tasa_val_{b_id}")
                                    
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
                                                "tasa_valor": nuevo_tasa_valor,
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
                                    matriz_dict[puesto][f"Nota | {fecha}"] = row.get("nota", "")
                            
                            if matriz_dict:
                                lista_ordenada = [matriz_dict[p] for p in sorted(matriz_dict.keys()) if p in matriz_dict]
                                df_matriz = pd.DataFrame(lista_ordenada)
                                
                                columnas_fijas = ["Nro. Puesto", "Participante"]
                                for fecha in fechas_bolso:
                                    columnas_fijas.append(fecha)
                                    columnas_fijas.append(f"Nota | {fecha}")

                                for col in fechas_bolso:
                                    if col not in df_matriz.columns:
                                        df_matriz[col] = "⏳ Pendiente"
                                for fecha in fechas_bolso:
                                    nota_col = f"Nota | {fecha}"
                                    if nota_col not in df_matriz.columns:
                                        df_matriz[nota_col] = ""

                                df_matriz = df_matriz[[c for c in columnas_fijas if c in df_matriz.columns]]

                                # --- SELECTOR DE VISIBILIDAD DE COLUMNAS (OJITO) EN COMPARTIDOS ---
                                with st.popover("👁️ Ocultar / Mostrar Fechas y Notas"):
                                    st.markdown("**Selecciona las fechas visibles:**")
                                    vis_cols_shared = {}
                                    for col in fechas_bolso:
                                        vis_cols_shared[col] = st.checkbox(f"📅 {col}", value=True, key=f"chk_col_shared_{b_id}_{col}")
                                
                                fechas_visibles_shared = [col for col in fechas_bolso if vis_cols_shared.get(col, True)]
                                
                                columnas_a_mostrar_shared = ["Nro. Puesto", "Participante"]
                                for fecha in fechas_visibles_shared:
                                    columnas_a_mostrar_shared.append(fecha)
                                    columnas_a_mostrar_shared.append(f"Nota | {fecha}")

                                df_matriz_filtrado_shared = df_matriz[[c for c in columnas_a_mostrar_shared if c in df_matriz.columns]]

                                es_solo_lectura = (nivel_acceso == "Lectura")
                                opciones_base = ["⏳ Pendiente", "🟢 Recibe Pozo", f"✅ Cobrado (por {email_corto})"]
                                
                                column_config_dict = {
                                    "Nro. Puesto": st.column_config.NumberColumn("Nro.", disabled=True, width="small"),
                                    "Participante": st.column_config.TextColumn("Participante", disabled=es_solo_lectura, width="medium"),
                                }
                                
                                for fecha in fechas_visibles_shared:
                                    if fecha in df_matriz_filtrado_shared.columns:
                                        serie_fecha = df_matriz_filtrado_shared[fecha]
                                        if isinstance(serie_fecha, pd.DataFrame):
                                            serie_fecha = serie_fecha.iloc[:, 0]
                                        valores_existentes = serie_fecha.dropna().unique().tolist()
                                    else:
                                        valores_existentes = []
                                        
                                    opciones_estado = list(dict.fromkeys(opciones_base + valores_existentes))
                                    column_config_dict[fecha] = st.column_config.SelectboxColumn(
                                        label=f"Estado {fecha}", options=opciones_estado, required=True, width="medium", disabled=es_solo_lectura
                                    )
                                    
                                    nota_col_key = f"Nota | {fecha}"
                                    column_config_dict[nota_col_key] = st.column_config.TextColumn(
                                        label=f"Nota {fecha}", width="medium", disabled=es_solo_lectura
                                    )

                                df_editado = st.data_editor(df_matriz_filtrado_shared, column_config=column_config_dict, use_container_width=True, hide_index=True, key=f"editor_shared_{b_id}_{idx}")
                                
                                if nivel_acceso == "Editor":
                                    if st.button("Guardar Cambios Compartidos", key=f"btn_save_shared_{b_id}_{idx}", type="primary"):
                                        try:
                                            for index, row in df_editado.iterrows():
                                                puesto = row["Nro. Puesto"]
                                                nombre_part = row["Participante"]
                                                for fecha in fechas_visibles_shared:
                                                    estado_val = row.get(fecha, "⏳ Pendiente")
                                                    nota_val = row.get(f"Nota | {fecha}", "")
                                                    
                                                    supabase.table("detalles_bolso").update({
                                                        "participante": nombre_part,
                                                        "estado": estado_val,
                                                        "nota": nota_val,
                                                        "actualizado_por": email_corto
                                                    }).eq("bolso_id", b_id).eq("nro_puesto", puesto).eq("fecha", fecha).execute()
                                            st.success("¡Cambios y notas guardados con éxito!")
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

    # PESTAÑA 5: Compra/Venta Dólares (Migrada a Supabase)
    with tab_divisas:
        st.subheader("💱 Control de Compra y Venta de Dólares")
        st.write("Registra las operaciones indicando quién vende, quién compra, los montos y los estados de entrega.")
        
        with st.form("form_nueva_divisa", clear_on_submit=True):
            st.markdown("### ➕ Registrar Nueva Operación")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                tipo_operacion = st.selectbox("Tipo de Operación", ["VENDIDO", "COMPRADO"], key="nuevo_tipo_op")
            with col_f2:
                monto_divisa = st.number_input("Monto en Dólares ($)", min_value=0.0, format="%.2f", value=20.0, key="nuevo_monto_op")
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                nombre_vendedor = st.text_input("Nombre del Vendedor", placeholder="Ej. Name", key="nuevo_vendedor_op")
            with col_n2:
                nombre_comprador = st.text_input("Nombre del Comprador", placeholder="Ej. Name", key="nuevo_comprador_op")
            
            st.markdown("---")
            st.markdown("📦 **Estado de Entrega inicial:**")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                chk_me_entregaron = st.checkbox("¿Me entregaron el dinero?", key="nuevo_chk_entregaron")
            with col_c2:
                chk_entregue = st.checkbox("¿Ya entregué el dinero?", key="nuevo_chk_entregue")
                
            btn_guardar_divisa = st.form_submit_button("Guardar Operación", type="primary")
            
            if btn_guardar_divisa:
                if nombre_vendedor.strip() and nombre_comprador.strip():
                    try:
                        supabase.table("divisas").insert({
                            "user_id": usuario_actual.id,
                            "operacion": tipo_operacion,
                            "monto": monto_divisa,
                            "vendedor": nombre_vendedor.strip(),
                            "comprador": nombre_comprador.strip(),
                            "me_entregaron": chk_me_entregaron,
                            "entregue": chk_entregue
                        }).execute()
                        st.success("¡Operación registrada con éxito en Supabase!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar la operación: {e}")
                else:
                    st.warning("Por favor ingresa tanto el nombre del vendedor como el del comprador.")

        st.markdown("---")
        st.subheader("📋 Listado y Control de Operaciones")
        st.write("Puedes editar directamente los campos o marcar las casillas de verificación para actualizar el estado al instante.")

        try:
            resp_divisas = supabase.table("divisas").select("*").eq("user_id", usuario_actual.id).order("created_at", desc=False).execute()
            registros_db = resp_divisas.data if resp_divisas.data else []

            if registros_db:
                lista_para_df = []
                for r in registros_db:
                    lista_para_df.append({
                        "id": r["id"],
                        "Operación": r["operacion"],
                        "Monto ($)": float(r["monto"]),
                        "Vendedor": r["vendedor"],
                        "Comprador": r["comprador"],
                        "Me Entregaron": r["me_entregaron"],
                        "Entregué": r["entregue"]
                    })

                df_divisas = pd.DataFrame(lista_para_df)
                df_mostrar = df_divisas.drop(columns=["id"])

                columnas_config_divisas = {
                    "Operación": st.column_config.SelectboxColumn(
                        "Operación",
                        options=["VENDIDO", "COMPRADO"],
                        required=True,
                        width="small"
                    ),
                    "Monto ($)": st.column_config.NumberColumn(
                        "Monto ($)",
                        format="$%.2f",
                        min_value=0.0,
                        required=True,
                        width="small"
                    ),
                    "Vendedor": st.column_config.TextColumn(
                        "Vendedor",
                        required=True,
                        width="medium"
                    ),
                    "Comprador": st.column_config.TextColumn(
                        "Comprador",
                        required=True,
                        width="medium"
                    ),
                    "Me Entregaron": st.column_config.CheckboxColumn(
                        "Me Entregaron",
                        required=True,
                        width="small"
                    ),
                    "Entregué": st.column_config.CheckboxColumn(
                        "Entregué",
                        required=True,
                        width="small"
                    ),
                }

                df_divisas_editado = st.data_editor(
                    df_mostrar,
                    column_config=columnas_config_divisas,
                    use_container_width=True,
                    hide_index=True,
                    key="editor_tabla_divisas"
                )

                col_bt_1, col_bt_2 = st.columns([1, 4])
                
                with col_bt_1:
                    if st.button("💾 Guardar Cambios", type="primary", key="btn_guardar_cambios_divisas"):
                        try:
                            for idx, row in df_editado.iterrows():
                                reg_id = df_divisas.iloc[idx]["id"]
                                supabase.table("divisas").update({
                                    "operacion": row["Operación"],
                                    "monto": row["Monto ($)"],
                                    "vendedor": row["Vendedor"],
                                    "comprador": row["Comprador"],
                                    "me_entregaron": row["Me Entregaron"],
                                    "entregue": row["Entregué"]
                                }).eq("id", reg_id).execute()

                            st.success("¡Cambios actualizados correctamente en Supabase!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar los cambios: {e}")
                        
                with col_bt_2:
                    if st.button("🗑️ Limpiar Todo el Historial", key="btn_limpiar_divisas"):
                        try:
                            supabase.table("divisas").delete().eq("user_id", usuario_actual.id).execute()
                            st.success("¡Historial borrado por completo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al limpiar el historial: {e}")
            else:
                st.info("No hay operaciones de compra/venta registradas todavía.")
        except Exception as e:
            st.error(f"Error al cargar las operaciones de divisas: {e}")
