import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
# ESTO DEBE SER LA PRIMERA INSTRUCCIÓN DE STREAMLIT SIEMPRE
st.set_page_config(page_title="Punto de Venta - Carnicería", page_icon="🥩", layout="wide")

# 1. CONEXIÓN AL MOTOR LOCAL (o en la nube si ya lo cambiaste)
API_URL = "https://api-carniceria-bdoz.onrender.com"

# --- 2. MEMORIA DE SESIÓN (LOGIN) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "rol" not in st.session_state:
    st.session_state.rol = ""

# --- 3. PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
    # Diseño centrado con columnas
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True) 
        st.markdown("<h1 style='text-align: center;'>🥩 Sistema de Gestión</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>🔒 Control de Acceso</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("👤 Nombre de Usuario:")
            password = st.text_input("🔑 PIN de Seguridad:", type="password")
            submit = st.form_submit_button("🚀 Iniciar Sesión", use_container_width=True)
            
            if submit:
                # Cuentas maestras de prueba
                if usuario == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.session_state.usuario = "admin"
                    st.session_state.rol = "Administrador / Dueño"
                    st.rerun()
                elif usuario == "cajero" and password == "0000":
                    st.session_state.logged_in = True
                    st.session_state.usuario = "cajero"
                    st.session_state.rol = "Cajero"
                    st.rerun()
                else:
                    st.error("❌ Usuario o PIN incorrectos")

# --- 4. SISTEMA PRINCIPAL (Solo se ve si el login es correcto) ---
else:
    # PANEL LATERAL (Sidebar)
    with st.sidebar:
        st.title("🥩 Panel de Control")
        st.write(f"👤 **Usuario:** {st.session_state.usuario}")
        
        # Le damos color diferente dependiendo del rol
        if st.session_state.rol == "Administrador / Dueño":
            st.success(f"👑 **Rol:** {st.session_state.rol}")
        else:
            st.info(f"💼 **Rol:** {st.session_state.rol}")
        
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.usuario = ""
            st.session_state.rol = ""
            st.rerun()

    # TÍTULO PRINCIPAL DEL SISTEMA
    st.title("🥩 Sistema de Gestión - Carnicería")
    st.divider()

    # Consultamos los productos globales al inicio para usarlos en varias pestañas
    try:
        res_prod = requests.get(f"{API_URL}/productos/")
        productos = res_prod.json()
    except:
        productos = []

    # Creamos las pestañas de navegación
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛒 Venta", "🥩 Inventario", "🗑️ Mermas", "💸 Gastos", "📊 Reportes"])

    # --- PESTAÑA 1: VENTAS ---
    with tab1:
        st.header("Registrar Venta")
        
        if productos and isinstance(productos, list):
            # Le agregamos el ID al inicio para que nunca haya nombres duplicados
            opciones_prod = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']:.3f} KG)": p for p in productos}
            
            prod_seleccionado = st.selectbox("Selecciona el corte de carne:", list(opciones_prod.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                # step=0.001 permite vender desde 1 gramo hasta kilos enteros
                cantidad = st.number_input("Cantidad (KG):", min_value=0.001, value=1.000, step=0.001, format="%.3f")
            
            precio_venta = opciones_prod[prod_seleccionado]["precio_venta"]
            id_prod = opciones_prod[prod_seleccionado]["id"]
            
            st.info(f"**Total a cobrar:** ${(cantidad * precio_venta):,.2f} MXN")
            
            if st.button("💰 Cobrar Venta", type="primary"):
                # Validar que haya stock suficiente (Opcional pero recomendado)
                if cantidad > opciones_prod[prod_seleccionado]["stock_actual"]:
                    st.error("⚠️ No tienes suficiente stock para esta venta.")
                else:
                    payload = {
                        "detalles": [
                            {
                                "id_producto": id_prod,
                                "cantidad": cantidad,
                                "precio_unitario": precio_venta
                            }
                        ]
                    }
                    res = requests.post(f"{API_URL}/ventas/", json=payload)
                    if res.status_code == 200:
                        st.success("¡Venta registrada y descontada del inventario con éxito!")
                        time.sleep(1) # Pausa de 1 segundo para que leas el mensaje
                        st.rerun()    # ¡MAGIA! Recarga la página automáticamente
                    else:
                        st.error("Error al registrar la venta.")
        else:
            st.warning("No hay productos registrados. Ve a la pestaña de Inventario para dar de alta tus cortes.")

    # --- PESTAÑA 2: INVENTARIO ---
    with tab2:
        st.header("Catálogo y Existencias")
        
        with st.expander("➕ Agregar Nuevo Producto"):
            with st.form("form_nuevo_producto"):
                nombre = st.text_input("Nombre del Producto:")
                categoria = st.selectbox("Categoría:", [("Res", 1), ("Cerdo", 2), ("Pollo", 3), ("Procesados", 4)], format_func=lambda x: x[0])
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    precio_c = st.number_input("Costo Proveedor por KG ($):", min_value=0.0, step=1.0)
                with c2:
                    precio_v = st.number_input("Precio al Público por KG ($):", min_value=0.0, step=1.0)
                with c3:
                    stock_ini = st.number_input("Kilos que entraron (KG):", min_value=0.0, step=0.001, format="%.3f")
                    
                if st.form_submit_button("Guardar Producto"):
                    payload_prod = {
                        "nombre": nombre,
                        "id_categoria": categoria[1],
                        "precio_compra": precio_c,
                        "precio_venta": precio_v,
                        "stock_actual": stock_ini,
                        "unidad_medida": "KG"
                    }
                    try:
                        res_post = requests.post(f"{API_URL}/productos/", json=payload_prod)
                        respuesta = res_post.json()
                        
                        if "Error" in respuesta:
                            st.error(f"El motor rechazó el producto: {respuesta['Detalle']}")
                        else:
                            st.success("¡Producto guardado con éxito!")
                            time.sleep(1)
                            st.rerun() # Ahora sí recargará la página sin atorarse
                    except Exception as e: # ¡EL TRUCO ESTÁ AQUÍ!
                        st.error(f"Error de servidor: Verifica que FastAPI esté encendido.")
                    
        st.subheader("Existencias Actuales")
        if productos and isinstance(productos, list):
            df = pd.DataFrame(productos)
            try:
                df = df.rename(columns={"nombre": "Producto", "categoria": "Categoría", "precio_venta": "Precio Público ($)", "stock_actual": "Stock (KG)"})
                # Tabla limpia, sin el comando que causaba advertencias en la terminal
                st.dataframe(df[["id", "Producto", "Categoría", "Precio Público ($)", "Stock (KG)"]])
            except:
                st.dataframe(df)
                
        st.divider()
        st.subheader("⚠️ Eliminar Producto")
        if productos and isinstance(productos, list):
            opciones_del = {f"#{p['id']} - {p['nombre']}": p["id"] for p in productos}
            prod_del = st.selectbox("Producto a eliminar:", list(opciones_del.keys()), key="del_box")
            if st.button("🗑️ Borrar del Inventario"):
                id_del = opciones_del[prod_del]
                try:
                    res_del = requests.delete(f"{API_URL}/productos/{id_del}").json()
                    if "Error" in res_del:
                        st.error(res_del["Error"])
                    else:
                        st.success(res_del["mensaje"])
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error("Error al conectar con el servidor.")

    # --- PESTAÑA 3: MERMAS ---
    with tab3:
        st.header("Registro de Mermas (Hueso/Grasa)")
        st.write("Registra aquí los recortes para que se descuenten de tu inventario y el dinero cuadre.")
        
        if productos and isinstance(productos, list):
            # 1. Agregamos el ID (#) al inicio para evitar bugs con nombres duplicados
            opciones_merma = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']} KG)": p["id"] for p in productos}
            
            prod_merma = st.selectbox("¿De qué corte salió la merma?", list(opciones_merma.keys()), key="merma_box")
            
            # 2. Quitamos el format="%.3f" y simplificamos el step para escribir libremente (ej. 1, 1.5, 0.2)
            peso_merma = st.number_input("Peso de la merma (KG):", min_value=0.0, value=0.500, step=0.001, format="%.3f")
            
            desc_merma = st.text_input("Descripción:", value="Recorte de grasa y hueso")
            
            if st.button("🗑️ Registrar Merma", type="primary"):
                id_pm = opciones_merma[prod_merma]
                payload_merma = {
                    "id_producto": id_pm,
                    "peso_merma": peso_merma,
                    "descripcion": desc_merma
                }
                # 3. Ponemos el try... except Exception as e para que no choque con st.rerun()
                try:
                    res_m = requests.post(f"{API_URL}/mermas/", json=payload_merma)
                    if res_m.status_code == 200:
                        st.success("¡Merma registrada y descontada del inventario!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Problema al registrar la merma.")
                except Exception as e:
                    st.error("Error de servidor: Verifica que FastAPI esté encendido.")

    # --- PESTAÑA 4: GASTOS ---
    with tab4:
        st.header("Registro de Gastos y Salidas de Dinero")
        
        with st.form("form_gastos"):
            categorias_gastos = ["Servicios (Luz, Agua, Internet)", "Flete / Viaje a Central de Abastos", "Mantenimiento de Vehículo", "Empaques, Bolsas y Limpieza", "Sueldos y Viáticos", "Otros"]
            cat_gasto = st.selectbox("Categoría del Gasto:", categorias_gastos)
            monto_gasto = st.number_input("Monto total gastado ($):", min_value=0.0, step=50.0)
            desc_gasto = st.text_input("Descripción:")
            
            if st.form_submit_button("💸 Registrar Gasto", type="primary"):
                payload_gasto = {"categoria": cat_gasto, "monto": monto_gasto, "descripcion": desc_gasto}
                try:
                    res_g = requests.post(f"{API_URL}/gastos/", json=payload_gasto)
                    if res_g.status_code == 200:
                        st.success("¡Gasto registrado exitosamente!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Problema al registrar el gasto.")
                except Exception as e:
                    st.error("Error de servidor: Verifica que FastAPI esté encendido.")
                    
        st.divider()
        st.subheader("📋 Historial de Gastos")
        try:
            gastos_data = requests.get(f"{API_URL}/gastos/").json()
            if gastos_data and isinstance(gastos_data, list):
                # SILENCIAMOS LA TERMINAL: cambiamos a width="stretch"
                st.dataframe(pd.DataFrame(gastos_data), width="stretch")
        except:
            pass

    # --- PESTAÑA 5: DASHBOARD Y FINANZAS ---
    with tab5:
        st.header("📊 Tablero Financiero")
        
        periodo_sel = st.selectbox("📅 Selecciona el periodo del reporte:", ["Hoy", "Semana", "Mes", "General"])
        
        if st.button("🔄 Generar Corte de Caja", type="primary"):
            try:
                res_rep = requests.get(f"{API_URL}/reportes/?periodo={periodo_sel}").json()
                if "Error" not in res_rep:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Ingresos (Ventas)", f"${res_rep['ventas']:,.2f}")
                    col2.metric("Salidas (Gastos)", f"${res_rep['gastos']:,.2f}")
                    col3.metric("Pérdida (Mermas)", f"${res_rep['mermas']:,.2f}")
                    col4.metric("GANANCIA NETA", f"${res_rep['ganancia_neta']:,.2f}")
                    
                    st.divider()
                    st.subheader(f"📈 ¿En qué se va el dinero? (Periodo: {periodo_sel})")
                    if res_rep["detalle_gastos"]:
                        df_g = pd.DataFrame(res_rep["detalle_gastos"]).groupby("categoria").sum().reset_index()
                        st.bar_chart(df_g, x="categoria", y="monto")
                    else:
                        st.info(f"No hay gastos registrados para el periodo: {periodo_sel}.")
                else:
                    st.error(f"Error del motor: {res_rep['Error']}")
            except Exception as e:
                st.error("Error al generar el reporte. Verifica que el servidor FastAPI esté encendido.")