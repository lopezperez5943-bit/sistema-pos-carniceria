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
                    st.session_state.logged_in = True; st.session_state.usuario = "admin"; st.session_state.rol = "Administrador / Dueño"
                    st.rerun()
                elif usuario == "cajero" and password == "0000":
                    st.session_state.logged_in = True; st.session_state.usuario = "cajero"; st.session_state.rol = "Cajero"
                    st.rerun()
                else:
                    st.error("❌ Usuario o PIN incorrectos")

else:
    with st.sidebar:
        st.title("🥩 Panel de Control")
        st.write(f"👤 **Usuario:** {st.session_state.usuario}")
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False; st.session_state.usuario = ""; st.session_state.rol = ""
            st.rerun()

    st.title("🥩 Sistema de Gestión - Carnicería")
    st.divider()

    try:
        productos = requests.get(f"{API_URL}/productos/").json()
    except:
        productos = []

    # ¡NUEVA PESTAÑA DE CLIENTES!
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🛒 Venta", "📒 Clientes", "🥩 Inventario", "📦 Compras", "🗑️ Mermas", "💸 Gastos", "🧮 Caja y Reportes"])

    # --- 1. VENTAS ---
    with tab1:
        st.header("🛒 Registrar Venta")
        if productos and isinstance(productos, list):
            opciones_prod = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']:.3f} KG)": p for p in productos}
            prod_seleccionado = st.selectbox("Selecciona el corte de carne:", list(opciones_prod.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                cantidad = st.number_input("Cantidad (KG):", min_value=0.001, value=1.000, step=0.001, format="%.3f")
            
            precio_venta = opciones_prod[prod_seleccionado]["precio_venta"]
            id_prod = opciones_prod[prod_seleccionado]["id"]
            
            st.divider()
            # ¡SE AÑADE "FIADO"!
            metodo_pago = st.radio("💳 Método de pago:", ["Efectivo", "Tarjeta", "Transferencia", "Fiado"], horizontal=True)
            
            id_cliente_sel = None
            if metodo_pago == "Transferencia":
                with st.expander("📲 MOSTRAR CÓDIGO QR AL CLIENTE"):
                    try:
                        st.image("mi_qr.png", width=300)
                        st.info("Escanea el QR con la app de tu banco o Mercado Pago.")
                    except:
                        st.warning("⚠️ Falta subir la imagen 'mi_qr.png' a GitHub.")
            
            # SI ES FIADO, PREGUNTAMOS A QUIÉN
            elif metodo_pago == "Fiado":
                try:
                    res_cli = requests.get(f"{API_URL}/clientes/").json()
                    if res_cli and isinstance(res_cli, list) and len(res_cli) > 0:
                        opc_cli = {f"#{c['id']} - {c['nombre']}": c['id'] for c in res_cli}
                        cli_escogido = st.selectbox("👤 ¿A qué cliente le vas a fiar?", list(opc_cli.keys()))
                        id_cliente_sel = opc_cli[cli_escogido]
                    else:
                        st.error("⚠️ No hay clientes. Ve a la pestaña 'Clientes' para agregarlos primero.")
                except:
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
                            time.sleep(1.5)
                            st.rerun()
                    except:
                        st.error("Error al cobrar.")
        else:
            st.warning("No hay productos.")

    # --- 2. LIBRETA DE CLIENTES Y FIADOS (¡LA NUEVA PESTAÑA!) ---
    with tab2:
        st.header("📒 Libreta de Clientes y Deudores")
        
        with st.expander("➕ Registrar Nuevo Cliente"):
            with st.form("form_cliente"):
                nom_c = st.text_input("Nombre del Cliente o Negocio (Ej. Taquería El Primo):")
                tel_c = st.text_input("Teléfono / WhatsApp (Opcional):")
                if st.form_submit_button("Guardar Cliente"):
                    res_c = requests.post(f"{API_URL}/clientes/", json={"nombre": nom_c, "telefono": tel_c})
                    if "Error" not in res_c.json():
                        st.success("¡Cliente guardado exitosamente!")
                        time.sleep(1); st.rerun()
        
        try:
            clientes_data = requests.get(f"{API_URL}/clientes/").json()
        except:
            clientes_data = []

        st.subheader("👥 Lista de Clientes")
        if clientes_data and isinstance(clientes_data, list):
            df_c = pd.DataFrame(clientes_data)
            st.dataframe(df_c[["id", "nombre", "telefono", "deuda_total"]].rename(columns={"deuda_total": "Debe ($)"}), width=800)
            
            st.divider()
            c1, c2 = st.columns(2)
            
            # ABONOS
            with c1:
                st.subheader("💰 Registrar un Abono")
                opciones_abono = {f"#{c['id']} - {c['nombre']} (Debe: ${c['deuda_total']:,.2f})": c for c in clientes_data if c['deuda_total'] > 0}
                if opciones_abono:
                    cliente_abono = st.selectbox("Selecciona quién va a abonar:", list(opciones_abono.keys()))
                    deuda_act = float(opciones_abono[cliente_abono]['deuda_total'])
                    monto_abono = st.number_input("Monto a abonar ($):", min_value=1.0, max_value=deuda_act, step=50.0)
                    metodo_abono = st.selectbox("¿Cómo pagó el abono?", ["Efectivo", "Tarjeta", "Transferencia"])
                    
                    if st.button("📥 Recibir Abono", type="primary"):
                        res_ab = requests.post(f"{API_URL}/clientes/{opciones_abono[cliente_abono]['id']}/abono", 
                                               json={"monto": monto_abono, "metodo_pago": metodo_abono})
                        if "Error" not in res_ab.json():
                            st.success("¡Abono registrado! El dinero se sumó a tu Caja.")
                            time.sleep(1.5); st.rerun()
                        else:
                            st.error(res_ab.json()["Error"])
                else:
                    st.info("🏆 ¡Nadie te debe dinero actualmente!")
            
            # ELIMINAR
            with c2:
                st.subheader("🗑️ Eliminar Cliente")
                opciones_del_cli = {f"#{c['id']} - {c['nombre']}": c['id'] for c in clientes_data}
                cliente_elim = st.selectbox("Cliente a borrar:", list(opciones_del_cli.keys()))
                if st.button("Eliminar permanentemente"):
                    res_del = requests.delete(f"{API_URL}/clientes/{opciones_del_cli[cliente_elim]}")
                    if "Error" in res_del.json():
                        st.error(res_del.json()["Error"]) # Seguro Antibobadas
                    else:
                        st.success("Cliente eliminado.")
                        time.sleep(1); st.rerun()
        else:
            st.info("No hay clientes en tu libreta. Agrega uno arriba.")

    # --- 3. INVENTARIO ---
    with tab3:
        st.header("Catálogo y Existencias")
        # (Se mantiene igual, resumido aquí para que funcione tu app)
        if productos and isinstance(productos, list):
            df = pd.DataFrame(productos)
            try:
                df = df.rename(columns={"nombre": "Producto", "categoria": "Categoría", "precio_venta": "Precio Público ($)", "stock_actual": "Stock (KG)"})
                st.dataframe(df[["id", "Producto", "Categoría", "Precio Público ($)", "Stock (KG)"]])
            except: st.dataframe(df)

    # --- 4. COMPRAS ---
    with tab4:
        st.header("📦 Ingresar Nueva Mercancía (Resurtir)")
        if productos and isinstance(productos, list):
            opciones_compra = {f"#{p['id']} - {p['nombre']} (Disp: {p['stock_actual']} KG)": p["id"] for p in productos}
            prod_compra = st.selectbox("¿Qué producto estás resurtiendo?", list(opciones_compra.keys()), key="compra_box")
            c1, c2 = st.columns(2)
            with c1: kilos_comprados = st.number_input("Kilos (KG):", min_value=0.001, value=10.000, step=0.500, format="%.3f")
            with c2: costo_total = st.number_input("Costo Total ($):", min_value=0.0, step=100.0)
            if st.button("🚚 Registrar Entrada de Mercancía", type="primary"):
                try:
                    requests.post(f"{API_URL}/compras/", json={"id_producto": opciones_compra[prod_compra], "cantidad": kilos_comprados, "costo_total": costo_total, "descripcion": "Resurtido"})
                    st.success("¡Mercancía sumada!"); time.sleep(1); st.rerun()
                except: st.error("Error al conectar.")

    # --- 5. MERMAS ---
    with tab5:
        st.header("Registro de Mermas (Hueso/Grasa)")

    # --- 6. GASTOS ---
    with tab6:
        st.header("Registro de Gastos y Salidas de Dinero")

    # --- 7. CAJA Y REPORTES ---
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
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("1. Fondo Inicial", f"${fondo_inicial:,.2f}")
                    c2.metric("2. Entradas (EFECTIVO)", f"+ ${ventas_efectivo:,.2f}")
                    c3.metric("3. Salidas (Gastos)", f"- ${gastos_hoy:,.2f}")
                    c4.metric("EFECTIVO EN CAJÓN", f"${efectivo_esperado:,.2f}")
                    st.warning(f"**Instrucción:** Debes tener exactamente **${efectivo_esperado:,.2f} MXN** en billetes y monedas.")
                else: 
                    st.error(f"Error del motor: {res_rep['Error']}")
            except: 
                st.error("Error al generar el corte de caja.")