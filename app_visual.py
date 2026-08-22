import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Punto de Venta - Carnicería", page_icon="🥩", layout="wide")

# CONEXIÓN AL MOTOR EN LA NUBE (Render)
API_URL = "https://api-carniceria-bdoz.onrender.com"

# --- MEMORIA DE SESIÓN (LOGIN) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "rol" not in st.session_state:
    st.session_state.rol = ""

# --- PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
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

# --- SISTEMA PRINCIPAL ---
else:
    with st.sidebar:
        st.title("🥩 Panel de Control")
        st.write(f"👤 **Usuario:** {st.session_state.usuario}")
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

    st.title("🥩 Sistema de Gestión - Carnicería")
    st.divider()

    try:
        res_prod = requests.get(f"{API_URL}/productos/")
        productos = res_prod.json()
    except:
        productos = []

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🛒 Venta", "🥩 Inventario", "📦 Compras (Resurtir)", "🗑️ Mermas", "💸 Gastos", "📊 Reportes"])

    # --- PESTAÑA 1: VENTAS ---
    with tab1:
        st.header("Registrar Venta")
        if productos and isinstance(productos, list):
            opciones_prod = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']:.3f} KG)": p for p in productos}
            prod_seleccionado = st.selectbox("Selecciona el corte de carne:", list(opciones_prod.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                cantidad = st.number_input("Cantidad (KG):", min_value=0.001, value=1.000, step=0.001, format="%.3f")
            
            precio_venta = opciones_prod[prod_seleccionado]["precio_venta"]
            id_prod = opciones_prod[prod_seleccionado]["id"]
            
            st.info(f"**Total a cobrar:** ${(cantidad * precio_venta):,.2f} MXN")
            
            if st.button("💰 Cobrar Venta", type="primary"):
                if cantidad > opciones_prod[prod_seleccionado]["stock_actual"]:
                    st.error("⚠️ No tienes suficiente stock para esta venta.")
                else:
                    payload = {"detalles": [{"id_producto": id_prod, "cantidad": cantidad, "precio_unitario": precio_venta}]}
                    res = requests.post(f"{API_URL}/ventas/", json=payload)
                    if res.status_code == 200:
                        st.success("¡Venta registrada y descontada del inventario con éxito!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Error al registrar la venta.")
        else:
            st.warning("No hay productos registrados.")

    # --- PESTAÑA 2: INVENTARIO (CORREGIDA AL 100%) ---
    with tab2:
        st.header("Catálogo y Existencias")
        
        # ACORDEÓN 1: NUEVO PRODUCTO
        with st.expander("➕ Agregar Nuevo Producto"):
            with st.form("form_nuevo_producto"):
                nombre = st.text_input("Nombre del Producto:")
                categoria = st.selectbox("Categoría:", [("Res", 1), ("Cerdo", 2), ("Pollo", 3), ("Procesados", 4)], format_func=lambda x: x[0])
                c1, c2, c3 = st.columns(3)
                with c1: precio_c = st.number_input("Costo Proveedor por KG ($):", min_value=0.0, step=1.0)
                with c2: precio_v = st.number_input("Precio al Público por KG ($):", min_value=0.0, step=1.0)
                with c3: stock_ini = st.number_input("Kilos iniciales (KG):", min_value=0.0, step=0.001, format="%.3f")
                    
                if st.form_submit_button("Guardar Producto"):
                    payload_prod = {"nombre": nombre, "id_categoria": categoria[1], "precio_compra": precio_c, "precio_venta": precio_v, "stock_actual": stock_ini, "unidad_medida": "KG"}
                    try:
                        res_post = requests.post(f"{API_URL}/productos/", json=payload_prod)
                        if "Error" in res_post.json(): st.error(f"Error: {res_post.json()['Detalle']}")
                        else:
                            st.success("¡Producto guardado!")
                            time.sleep(1)
                            st.rerun()
                    except: st.error("Error de servidor.")
        
        # ACORDEÓN 2: EDITAR PRECIOS 
        with st.expander("✏️ Editar Precios de un Producto"):
            if productos and isinstance(productos, list):
                opciones_edit = {f"#{p['id']} - {p['nombre']}": p for p in productos}
                prod_edit_nombre = st.selectbox("Selecciona el producto a modificar:", list(opciones_edit.keys()), key="edit_box")
                prod_data = opciones_edit[prod_edit_nombre]
                
                # LA MAGIA ANTI-ERRORES ESTÁ AQUÍ
                val_compra = float(prod_data.get('precio_compra') or 0.0)
                val_venta = float(prod_data.get('precio_venta') or 0.0)
                
                c1, c2 = st.columns(2)
                with c1:
                    nuevo_precio_c = st.number_input("Costo Proveedor Actualizado ($):", min_value=0.0, value=val_compra, step=1.0)
                with c2:
                    nuevo_precio_v = st.number_input("Precio al Público Actualizado ($):", min_value=0.0, value=val_venta, step=1.0)
                    
                if st.button("💾 Guardar Nuevos Precios"):
                    payload_edit = {"precio_compra": nuevo_precio_c, "precio_venta": nuevo_precio_v}
                    try:
                        res_edit = requests.put(f"{API_URL}/productos/{prod_data['id']}", json=payload_edit)
                        if res_edit.status_code == 200:
                            st.success("¡Precios actualizados con éxito!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error al actualizar.")
                    except:
                        st.error("Error de conexión al servidor.")
            else:
                st.info("Agrega productos primero para poder editarlos.")

        st.subheader("Existencias Actuales")
        if productos and isinstance(productos, list):
            df = pd.DataFrame(productos)
            try:
                df = df.rename(columns={"nombre": "Producto", "categoria": "Categoría", "precio_venta": "Precio Público ($)", "stock_actual": "Stock (KG)"})
                st.dataframe(df[["id", "Producto", "Categoría", "Precio Público ($)", "Stock (KG)"]])
            except: st.dataframe(df)
            
        st.divider()
        st.subheader("⚠️ Eliminar Producto")
        if productos and isinstance(productos, list):
            opciones_del = {f"#{p['id']} - {p['nombre']}": p["id"] for p in productos}
            prod_del = st.selectbox("Producto a eliminar:", list(opciones_del.keys()), key="del_box_2")
            
            if st.button("🗑️ Borrar del Inventario"):
                try:
                    res_del = requests.delete(f"{API_URL}/productos/{opciones_del[prod_del]}")
                    datos_res = res_del.json()
                    
                    # 1. Revisamos si el Cerebro nos mandó un mensaje de Error (ej. producto en uso)
                    if "Error" in datos_res:
                        st.error(f"No se puede borrar el producto porque ya tiene ventas o movimientos registrados. (Protección contable).")
                    
                    # 2. Si todo salió bien, mostramos éxito y recargamos
                    elif res_del.status_code == 200:
                        st.success("¡Producto eliminado correctamente!")
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        st.error("Ocurrió un problema desconocido al eliminar.")
                        
                except Exception as e: # Al poner 'Exception as e', ya no choca con el st.rerun()
                    st.error("Error de conexión con el servidor.")

    # --- PESTAÑA 3: COMPRAS (Resurtir) ---
    with tab3:
        st.header("📦 Ingresar Nueva Mercancía (Resurtir)")
        st.write("¿Llegaste de la Central de Abastos? Registra aquí los kilos que compraste para sumarlos a tu inventario.")
        
        if productos and isinstance(productos, list):
            opciones_compra = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']} KG)": p["id"] for p in productos}
            prod_compra = st.selectbox("¿Qué producto estás resurtiendo?", list(opciones_compra.keys()), key="compra_box")
            
            c1, c2 = st.columns(2)
            with c1:
                kilos_comprados = st.number_input("Kilos que compraste (KG):", min_value=0.001, value=10.000, step=0.500, format="%.3f")
            with c2:
                costo_total = st.number_input("¿Cuánto pagaste en total por estos kilos? ($):", min_value=0.0, step=100.0)
                
            desc_compra = st.text_input("Nota / Proveedor:", value="Compra a proveedor local")
            
            if st.button("🚚 Registrar Entrada de Mercancía", type="primary"):
                id_pc = opciones_compra[prod_compra]
                payload_compra = {
                    "id_producto": id_pc,
                    "cantidad": kilos_comprados,
                    "costo_total": costo_total,
                    "descripcion": f"Resurtido: {desc_compra}"
                }
                try:
                    res_c = requests.post(f"{API_URL}/compras/", json=payload_compra)
                    if res_c.status_code == 200:
                        st.success("¡Mercancía sumada al inventario y dinero registrado en gastos exitosamente!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Problema al registrar la compra.")
                except: st.error("Error al conectar con el servidor.")
        else:
            st.warning("Primero debes agregar productos en la pestaña de Inventario.")

    # --- PESTAÑA 4: MERMAS ---
    with tab4:
        st.header("Registro de Mermas (Hueso/Grasa)")
        if productos and isinstance(productos, list):
            opciones_merma = {f"#{p['id']} - {p['nombre']}": p["id"] for p in productos}
            prod_merma = st.selectbox("¿De qué corte salió la merma?", list(opciones_merma.keys()), key="merma_box")
            peso_merma = st.number_input("Peso de la merma (KG):", min_value=0.0, value=0.500, step=0.001, format="%.3f")
            desc_merma = st.text_input("Descripción:", value="Recorte de grasa y hueso")
            
            if st.button("🗑️ Registrar Merma", type="primary"):
                payload_merma = {"id_producto": opciones_merma[prod_merma], "peso_merma": peso_merma, "descripcion": desc_merma}
                try:
                    res_m = requests.post(f"{API_URL}/mermas/", json=payload_merma)
                    if res_m.status_code == 200:
                        st.success("¡Merma registrada!")
                        time.sleep(1); st.rerun()
                except: st.error("Error de servidor.")

    # --- PESTAÑA 5: GASTOS ---
    with tab5:
        st.header("Registro de Gastos y Salidas de Dinero")
        with st.form("form_gastos"):
            cat_gasto = st.selectbox("Categoría del Gasto:", ["Servicios (Luz, Agua, Internet)", "Flete / Viaje a Central de Abastos", "Mantenimiento de Vehículo", "Empaques, Bolsas y Limpieza", "Sueldos y Viáticos", "Otros"])
            monto_gasto = st.number_input("Monto total gastado ($):", min_value=0.0, step=50.0)
            desc_gasto = st.text_input("Descripción:")
            
            if st.form_submit_button("💸 Registrar Gasto", type="primary"):
                payload_gasto = {"categoria": cat_gasto, "monto": monto_gasto, "descripcion": desc_gasto}
                try:
                    res_g = requests.post(f"{API_URL}/gastos/", json=payload_gasto)
                    if res_g.status_code == 200:
                        st.success("¡Gasto registrado exitosamente!")
                        time.sleep(1); st.rerun()
                except: st.error("Error de servidor.")
                    
        st.divider()
        st.subheader("📋 Historial de Gastos")
        try:
            gastos_data = requests.get(f"{API_URL}/gastos/").json()
            if gastos_data and isinstance(gastos_data, list):
                st.dataframe(pd.DataFrame(gastos_data), width="stretch")
        except: pass

    # --- PESTAÑA 6: REPORTES ---
    with tab6:
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
                    else: st.info(f"No hay gastos registrados para el periodo: {periodo_sel}.")
                else: st.error(f"Error del motor: {res_rep['Error']}")
            except: st.error("Error al generar el reporte.")