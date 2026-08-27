import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Punto de Venta - Carnicería", page_icon="🥩", layout="wide")

# CONEXIÓN AL MOTOR EN LA NUBE (Render)
API_URL = "https://api-carniceria-bdoz.onrender.com"

# --- DATOS PARA EL QR ---
DATOS_TRANSFERENCIA = "CLABE: 012345678901234567 | Banco: BBVA | Beneficiario: Carniceria"

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "rol" not in st.session_state:
    st.session_state.rol = ""

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

else:
    with st.sidebar:
        st.title("🥩 Panel de Control")
        st.write(f"👤 **Usuario:** {st.session_state.usuario}")
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.usuario = ""
            st.session_state.rol = ""
            st.rerun()

    st.title("🥩 Sistema de Gestión - Carnicería")
    st.divider()

    try:
        productos = requests.get(f"{API_URL}/productos/").json()
    except Exception as e:
        productos = []

    # PESTAÑAS DEL SISTEMA
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🛒 Venta", "📒 Clientes", "🥩 Inventario", "📦 Compras", "🗑️ Mermas", "💸 Gastos", "🧮 Caja y Reportes"])

    # --- 1. VENTAS (CON ESCÁNER) ---
    with tab1:
        st.header("🛒 Registrar Venta")
        
        if productos and isinstance(productos, list):
            st.info("💡 **Tip:** Haz clic en la caja de abajo y usa tu pistola lectora para buscar rápido.")
            codigo_escaneado = st.text_input("🔍 Escáner de Código de Barras (Opcional):", value="", key="scanner_venta")
            
            indice_producto = 0
            
            if codigo_escaneado != "":
                encontrado = False
                for i, p in enumerate(productos):
                    if str(p.get("codigo_barras")) == str(codigo_escaneado):
                        indice_producto = i
                        encontrado = True
                        st.success(f"✅ Producto detectado: **{p['nombre']}**")
                        break
                if not encontrado:
                    st.warning("⚠️ Código no reconocido en el inventario.")
            
            st.divider()
            
            opciones_prod = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']:.3f} KG)": p for p in productos}
            
            prod_seleccionado = st.selectbox("🥩 Selecciona el producto manualmente (o usa el escáner):", list(opciones_prod.keys()), index=indice_producto)
            
            col1, col2 = st.columns(2)
            with col1:
                cantidad = st.number_input("Cantidad (KG / Piezas):", min_value=0.001, value=1.000, step=0.001, format="%.3f")
            
            precio_venta = opciones_prod[prod_seleccionado]["precio_venta"]
            id_prod = opciones_prod[prod_seleccionado]["id"]
            
            st.divider()
            metodo_pago = st.radio("💳 Método de pago:", ["Efectivo", "Tarjeta", "Transferencia", "Fiado"], horizontal=True)
            
            id_cliente_sel = None
            cli_escogido = ""
            
            if metodo_pago == "Transferencia":
                with st.expander("📲 MOSTRAR CÓDIGO QR AL CLIENTE"):
                    try:
                        st.image("mi_qr.png", width=300)
                        st.info("Escanea el QR con la app de tu banco o Mercado Pago.")
                    except Exception as e:
                        st.warning("⚠️ Falta subir la imagen 'mi_qr.png' a GitHub.")
            
            elif metodo_pago == "Fiado":
                try:
                    res_cli = requests.get(f"{API_URL}/clientes/").json()
                    if res_cli and isinstance(res_cli, list) and len(res_cli) > 0:
                        opc_cli = {f"#{c['id']} - {c['nombre']}": c['id'] for c in res_cli}
                        cli_escogido = st.selectbox("👤 ¿A qué cliente le vas a fiar?", list(opc_cli.keys()))
                        id_cliente_sel = opc_cli[cli_escogido]
                    else:
                        st.error("⚠️ No hay clientes. Ve a la pestaña 'Clientes' para agregarlos primero.")
                except Exception as e:
                    st.error("Error al cargar clientes.")
            
            st.info(f"**Total a cobrar:** ${(cantidad * precio_venta):,.2f} MXN")
            
            if st.button("💰 Cobrar Venta", type="primary"):
                if cantidad > opciones_prod[prod_seleccionado]["stock_actual"]:
                    st.error("⚠️ No tienes suficiente stock para esta venta.")
                elif metodo_pago == "Fiado" and id_cliente_sel is None:
                    st.error("⚠️ Debes seleccionar un cliente para fiarle.")
                else:
                    payload = {
                        "detalles": [{"id_producto": id_prod, "cantidad": cantidad, "precio_unitario": precio_venta}],
                        "metodo_pago": metodo_pago,
                        "id_cliente": id_cliente_sel
                    }
                    try:
                        res = requests.post(f"{API_URL}/ventas/", json=payload)
                        if res.status_code == 200:
                            id_venta = res.json().get("id_venta")
                            st.success(f"¡Venta exitosa ({metodo_pago})!")
                            
                            res_ticket = requests.get(f"{API_URL}/tickets/{id_venta}").json()
                            if "Error" not in res_ticket:
                                st.markdown("---")
                                st.markdown("<h2 style='text-align: center;'>🧾 TICKET DE VENTA</h2>", unsafe_allow_html=True)
                                st.write(f"**Folio:** #{res_ticket['id_venta']} | **Fecha:** {res_ticket['fecha'][:16]}")
                                st.write(f"**Pagado mediante:** {metodo_pago}")
                                if metodo_pago == "Fiado":
                                    st.write(f"**Cargado a la cuenta de:** {cli_escogido}")
                                st.divider()
                                for d in res_ticket['detalles']:
                                    nombre_limpio = str(d['producto']).strip() 
                                    st.write(f"🥩 **{nombre_limpio}**")
                                    st.write(f"{d['cantidad']} KG/PZ x ${d['precio_unitario']:,.2f} = **${d['subtotal']:,.2f} MXN**")
                                st.divider()
                                st.markdown(f"<h3 style='text-align: right;'>TOTAL: ${res_ticket['total']:,.2f} MXN</h3>", unsafe_allow_html=True)
                                st.markdown("---")
                                
                                if st.button("🔄 Iniciar Nueva Venta"):
                                    st.rerun()
                            else:
                                time.sleep(1.5)
                                st.rerun()
                        else:
                            st.error("Error al registrar la venta en la base de datos.")
                    except Exception as e:
                        st.error("Error de conexión con el servidor al cobrar.")
        else:
            st.warning("No hay productos registrados en el inventario.")

    # --- 2. LIBRETA DE CLIENTES Y FIADOS ---
    with tab2:
        st.header("📒 Libreta de Clientes y Deudores")
        
        with st.expander("➕ Registrar Nuevo Cliente"):
            with st.form("form_cliente"):
                nom_c = st.text_input("Nombre del Cliente o Negocio:")
                tel_c = st.text_input("Teléfono / WhatsApp (Opcional):")
                if st.form_submit_button("Guardar Cliente"):
                    try:
                        res_c = requests.post(f"{API_URL}/clientes/", json={"nombre": nom_c, "telefono": tel_c})
                        if "Error" not in res_c.json():
                            st.success("¡Cliente guardado exitosamente!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error("Error al conectar con el servidor.")
        
        try:
            clientes_data = requests.get(f"{API_URL}/clientes/").json()
        except Exception as e:
            clientes_data = []

        st.subheader("👥 Lista de Clientes")
        if clientes_data and isinstance(clientes_data, list):
            df_c = pd.DataFrame(clientes_data)
            st.dataframe(df_c[["id", "nombre", "telefono", "deuda_total"]].rename(columns={"deuda_total": "Debe ($)"}), width=800)
            
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("💰 Registrar un Abono")
                opciones_abono = {f"#{c['id']} - {c['nombre']} (Debe: ${c['deuda_total']:,.2f})": c for c in clientes_data if c['deuda_total'] > 0}
                if opciones_abono:
                    cliente_abono = st.selectbox("Selecciona quién va a abonar:", list(opciones_abono.keys()))
                    deuda_act = float(opciones_abono[cliente_abono]['deuda_total'])
                    monto_abono = st.number_input("Monto a abonar ($):", min_value=1.0, max_value=deuda_act, step=50.0)
                    metodo_abono = st.selectbox("¿Cómo pagó el abono?", ["Efectivo", "Tarjeta", "Transferencia"])
                    
                    if st.button("📥 Recibir Abono", type="primary"):
                        try:
                            res_ab = requests.post(f"{API_URL}/clientes/{opciones_abono[cliente_abono]['id']}/abono", 
                                                   json={"monto": monto_abono, "metodo_pago": metodo_abono})
                            if "Error" not in res_ab.json():
                                st.success("¡Abono registrado! El dinero se sumó a tu Caja.")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(res_ab.json()["Error"])
                        except Exception as e:
                            st.error("Error al conectar.")
                else:
                    st.info("🏆 ¡Nadie te debe dinero actualmente!")
            
            with c2:
                st.subheader("🗑️ Eliminar Cliente")
                opciones_del_cli = {f"#{c['id']} - {c['nombre']}": c['id'] for c in clientes_data}
                cliente_elim = st.selectbox("Cliente a borrar:", list(opciones_del_cli.keys()))
                if st.button("Eliminar permanentemente"):
                    try:
                        res_del = requests.delete(f"{API_URL}/clientes/{opciones_del_cli[cliente_elim]}")
                        if "Error" in res_del.json():
                            st.error(res_del.json()["Error"]) 
                        else:
                            st.success("Cliente eliminado.")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error("Error al conectar.")
        else:
            st.info("No hay clientes en tu libreta. Agrega uno arriba.")

    # --- 3. INVENTARIO (CON ALERTAS Y CÓDIGO DE BARRAS) ---
    with tab3:
        st.header("Catálogo y Existencias")

        with st.expander("🖨️ Generador de Etiquetas (Códigos de Barras)"):
            st.write("Crea códigos para imprimir y pegar en productos sin etiqueta (ej. bolsas de carbón o manteca).")
            codigo_a_generar = st.text_input("Escribe un código inventado (Ej. 101 o 800123):")
            if codigo_a_generar:
                url_barcode = f"https://barcode.tec-it.com/barcode.ashx?data={codigo_a_generar}&code=Code128&translate-esc=true"
                st.image(url_barcode, width=250)
                st.info("Haz clic derecho en la imagen, selecciona 'Guardar imagen como...', imprímela y pégala en tu bolsa.")
        
        with st.expander("➕ Agregar Nuevo Producto (Con Lector)"):
            with st.form("form_nuevo_producto"):
                nombre = st.text_input("Nombre del Producto:")
                categoria = st.selectbox("Categoría:", [("Res", 1), ("Cerdo", 2), ("Pollo", 3), ("Procesados/Abarrotes", 4)], format_func=lambda x: x[0])
                codigo_barras = st.text_input("Código de Barras (opcional - usa el escáner aquí):")
                
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1: precio_c = st.number_input("Costo Proveedor por KG/PZ ($):", min_value=0.0, step=1.0)
                with col_c2: precio_v = st.number_input("Precio al Público por KG/PZ ($):", min_value=0.0, step=1.0)
                with col_c3: stock_ini = st.number_input("Stock inicial (KG/PZ):", min_value=0.0, step=0.001, format="%.3f")
                    
                if st.form_submit_button("Guardar Producto"):
                    payload_prod = {
                        "nombre": nombre, "id_categoria": categoria[1], 
                        "precio_compra": precio_c, "precio_venta": precio_v, 
                        "stock_actual": stock_ini, "unidad_medida": "KG",
                        "codigo_barras": codigo_barras
                    }
                    try:
                        res_post = requests.post(f"{API_URL}/productos/", json=payload_prod)
                        if "Error" in res_post.json(): 
                            st.error(f"Error: {res_post.json()['Detalle']}")
                        else:
                            st.success("¡Producto guardado!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e: 
                        st.error("Error de servidor.")
        
        with st.expander("✏️ Editar Precios de un Producto"):
            if productos and isinstance(productos, list):
                opciones_edit = {f"#{p['id']} - {p['nombre']}": p for p in productos}
                prod_edit_nombre = st.selectbox("Selecciona el producto a modificar:", list(opciones_edit.keys()), key="edit_box")
                prod_data = opciones_edit[prod_edit_nombre]
                
                val_compra = float(prod_data.get('precio_compra') or 0.0)
                val_venta = float(prod_data.get('precio_venta') or 0.0)
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    nuevo_precio_c = st.number_input("Costo Proveedor Actualizado ($):", min_value=0.0, value=val_compra, step=1.0)
                with col_e2:
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
                    except Exception as e:
                        st.error("Error de conexión al servidor.")
            else:
                st.info("Agrega productos primero para poder editarlos.")

        # ¡NUEVO: ALERTAS DE STOCK BAJO!
        st.divider()
        st.subheader("🚨 Alertas de Inventario")
        if productos and isinstance(productos, list):
            productos_bajos = [p for p in productos if p['stock_actual'] <= 3.0]
            if productos_bajos:
                for pb in productos_bajos:
                    st.error(f"⚠️ **STOCK BAJO:** Te quedan solo {pb['stock_actual']} KG/PZ de **{pb['nombre']}**.")
            else:
                st.success("✅ Todo el inventario tiene buen nivel de stock (Más de 3 KG/PZ).")

        st.subheader("Existencias Actuales")
        if productos and isinstance(productos, list):
            df = pd.DataFrame(productos)
            try:
                df = df.rename(columns={"nombre": "Producto", "categoria": "Categoría", "precio_venta": "Precio ($)", "stock_actual": "Stock", "codigo_barras": "Cód. Barras"})
                st.dataframe(df[["id", "Producto", "Cód. Barras", "Categoría", "Precio ($)", "Stock"]])
            except Exception as e: 
                st.dataframe(df)
            
        st.divider()
        st.subheader("⚠️ Eliminar Producto")
        if productos and isinstance(productos, list):
            opciones_del = {f"#{p['id']} - {p['nombre']}": p["id"] for p in productos}
            prod_del = st.selectbox("Producto a eliminar:", list(opciones_del.keys()), key="del_box_2")
            
            if st.button("🗑️ Borrar del Inventario"):
                try:
                    res_del = requests.delete(f"{API_URL}/productos/{opciones_del[prod_del]}")
                    datos_res = res_del.json()
                    if "Error" in datos_res:
                        st.error(f"No se puede borrar el producto porque ya tiene ventas asociadas.")
                    elif res_del.status_code == 200:
                        st.success("¡Producto eliminado correctamente!")
                        time.sleep(1)
                        st.rerun()
                except Exception as e: 
                    st.error("Error de conexión con el servidor.")

    # --- 4. COMPRAS ---
    with tab4:
        st.header("📦 Ingresar Nueva Mercancía (Resurtir)")
        if productos and isinstance(productos, list):
            opciones_compra = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']} KG/PZ)": p["id"] for p in productos}
            prod_compra = st.selectbox("¿Qué producto estás resurtiendo?", list(opciones_compra.keys()), key="compra_box")
            
            col_comp1, col_comp2 = st.columns(2)
            with col_comp1: kilos_comprados = st.number_input("Cantidad (KG/PZ):", min_value=0.001, value=10.000, step=0.500, format="%.3f")
            with col_comp2: costo_total = st.number_input("Costo Total pagado ($):", min_value=0.0, step=100.0)
            
            desc_compra = st.text_input("Nota / Proveedor:", value="Compra a proveedor local")
            if st.button("🚚 Registrar Entrada de Mercancía", type="primary"):
                payload_compra = {
                    "id_producto": opciones_compra[prod_compra],
                    "cantidad": kilos_comprados,
                    "costo_total": costo_total,
                    "descripcion": f"Resurtido: {desc_compra}"
                }
                try:
                    res_c = requests.post(f"{API_URL}/compras/", json=payload_compra)
                    if res_c.status_code == 200:
                        st.success("¡Mercancía sumada al inventario y registrada en gastos!")
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e: 
                    st.error("Error al conectar con el servidor.")
        else:
            st.warning("Primero debes agregar productos en la pestaña de Inventario.")

    # --- 5. MERMAS ---
    with tab5:
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
                        time.sleep(1)
                        st.rerun()
                except Exception as e: 
                    st.error("Error de servidor.")

    # --- 6. GASTOS ---
    with tab6:
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
                        time.sleep(1)
                        st.rerun()
                except Exception as e: 
                    st.error("Error de servidor.")
                    
        st.divider()
        st.subheader("📋 Historial de Gastos")
        try:
            gastos_data = requests.get(f"{API_URL}/gastos/").json()
            if gastos_data and isinstance(gastos_data, list):
                st.dataframe(pd.DataFrame(gastos_data), width="stretch")
        except Exception as e: 
            pass

    # --- 7. CAJA Y REPORTES (CON RANKING) ---
    with tab7:
        st.header("🧮 Control de Caja y Tablero Financiero")
        
        st.subheader("💵 Turno Actual (Corte de Caja)")
        fondo_inicial = st.number_input("Fondo de caja inicial (Morralla) $:", min_value=0.0, step=50.0, value=500.0)
        
        if st.button("⚖️ Hacer Corte de Caja de HOY", type="primary"):
            try:
                res_rep = requests.get(f"{API_URL}/reportes/?periodo=Hoy").json()
                if "Error" not in res_rep:
                    ventas_efectivo = res_rep.get('ventas_efectivo', 0.0)
                    ventas_banco = res_rep.get('ventas_banco', 0.0)
                    gastos_hoy = res_rep.get('gastos', 0.0)
                    
                    efectivo_esperado = fondo_inicial + ventas_efectivo - gastos_hoy
                    
                    st.info("### 💰 Resultado del Corte de Caja (Físico)")
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    col_r1.metric("1. Fondo Inicial", f"${fondo_inicial:,.2f}")
                    col_r2.metric("2. Entradas (EFECTIVO)", f"+ ${ventas_efectivo:,.2f}")
                    col_r3.metric("3. Salidas (Gastos)", f"- ${gastos_hoy:,.2f}")
                    col_r4.metric("EFECTIVO EN CAJÓN", f"${efectivo_esperado:,.2f}")
                    
                    st.warning(f"**Instrucción:** Abre el cajón. Debes tener exactamente **${efectivo_esperado:,.2f} MXN** en billetes y monedas.")
                    st.success(f"💳 **Dinero extra seguro en Banco (Tarjetas/Transferencias):** ${ventas_banco:,.2f} MXN")
                else: 
                    st.error(f"Error del motor: {res_rep['Error']}")
            except Exception as e: 
                st.error("Error al generar el corte de caja.")
        
        st.divider()
        st.subheader("📊 Reportes Financieros Generales")
        periodo_sel = st.selectbox("📅 Selecciona el periodo histórico:", ["Semana", "Mes", "General"])
        
        if st.button("🔄 Ver Historial Financiero"):
            try:
                res_rep = requests.get(f"{API_URL}/reportes/?periodo={periodo_sel}").json()
                if "Error" not in res_rep:
                    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                    col_h1.metric("Ingresos Totales", f"${res_rep.get('ventas_totales', 0):,.2f}")
                    col_h2.metric("Salidas (Gastos)", f"${res_rep.get('gastos', 0):,.2f}")
                    col_h3.metric("Pérdida (Mermas)", f"${res_rep.get('mermas', 0):,.2f}")
                    col_h4.metric("GANANCIA NETA", f"${res_rep.get('ganancia_neta', 0):,.2f}")
                    
                    st.divider()
                    st.subheader(f"📈 ¿En qué se va el dinero? (Periodo: {periodo_sel})")
                    if res_rep.get("detalle_gastos"):
                        df_g = pd.DataFrame(res_rep["detalle_gastos"]).groupby("categoria").sum().reset_index()
                        st.bar_chart(df_g, x="categoria", y="monto")
                    else: 
                        st.info(f"No hay gastos registrados para el periodo: {periodo_sel}.")
                else: 
                    st.error(f"Error del motor: {res_rep['Error']}")
            except Exception as e: 
                st.error("Error al generar el reporte histórico.")
                
        # ¡NUEVO: RANKING DE PRODUCTOS!
        st.divider()
        st.subheader("🏆 Ranking de Productos Más Vendidos")
        try:
            res_top = requests.get(f"{API_URL}/reportes/top-productos").json()
            if res_top and isinstance(res_top, list) and len(res_top) > 0 and "Error" not in res_top[0]:
                df_top = pd.DataFrame(res_top)
                st.bar_chart(df_top, x="producto", y="total_vendido", color="#FF4B4B")
            else:
                st.info("Aún no hay suficientes ventas registradas para generar el ranking.")
        except Exception as e:
            pass