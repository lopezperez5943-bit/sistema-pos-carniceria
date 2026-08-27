from fastapi import FastAPI
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from typing import List, Optional

# --- 1. CONEXIÓN A LA BASE DE DATOS EN LA NUBE (NEON) ---
URL_BASE_DATOS = "postgresql://neondb_owner:npg_Ycz1MT9nRBtL@ep-patient-term-axk6tdgq-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(
    URL_BASE_DATOS, 
    connect_args={'client_encoding': 'utf8'}
)
app = FastAPI(title="API POS - Carnicería")

# --- 2. MODELOS DE DATOS ---
class CategoriaNueva(BaseModel):
    nombre: str

class ProductoNuevo(BaseModel):
    nombre: str
    id_categoria: int
    precio_compra: float
    precio_venta: float
    stock_actual: float = 0.000 
    unidad_medida: str = "KG"
    codigo_barras: str = ""  # <--- ¡NUEVO CAMPO!

class DetalleVenta(BaseModel):
    id_producto: int
    cantidad: float
    precio_unitario: float

class VentaNueva(BaseModel):
    detalles: List[DetalleVenta]
    metodo_pago: str = "Efectivo"
    id_cliente: Optional[int] = None 

class ClienteNuevo(BaseModel):
    nombre: str
    telefono: str = ""

class AbonoData(BaseModel):
    monto: float
    metodo_pago: str = "Efectivo"

class MermaNueva(BaseModel):
    id_producto: int
    peso_merma: float
    descripcion: str = "Recorte de grasa / Hueso"

class GastoNuevo(BaseModel):
    categoria: str
    monto: float
    descripcion: str = ""

class CompraData(BaseModel):
    id_producto: int
    cantidad: float
    costo_total: float
    descripcion: str

class PrecioData(BaseModel):
    precio_compra: float
    precio_venta: float


# --- 3. RUTAS / ENDPOINTS ---

@app.get("/")
def probar_conexion():
    return {"Estado": "¡Éxito! Motor de la carnicería operando al 100% en la nube."}

@app.get("/clientes/")
def ver_clientes():
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT id_cliente, nombre, telefono, deuda_total FROM clientes ORDER BY nombre ASC"))
            return [{"id": f[0], "nombre": f[1], "telefono": f[2], "deuda_total": float(f[3])} for f in res.fetchall()]
    except Exception as e:
        return {"Error": str(e)}

@app.post("/clientes/")
def agregar_cliente(cliente: ClienteNuevo):
    try:
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO clientes (nombre, telefono) VALUES (:nom, :tel)"), 
                         {"nom": cliente.nombre, "tel": cliente.telefono})
            conn.commit()
            return {"mensaje": "Cliente registrado exitosamente."}
    except Exception as e:
        return {"Error": str(e)}

@app.delete("/clientes/{id_cliente}")
def eliminar_cliente(id_cliente: int):
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT deuda_total FROM clientes WHERE id_cliente = :id"), {"id": id_cliente}).fetchone()
            if res and res[0] > 0:
                return {"Error": "Este cliente aún tiene deuda. Debe liquidarla antes de poder eliminarlo."}
            
            conn.execute(text("DELETE FROM clientes WHERE id_cliente = :id"), {"id": id_cliente})
            conn.commit()
            return {"mensaje": "Cliente eliminado permanentemente."}
    except Exception as e:
        return {"Error": "No se pudo eliminar al cliente."}

@app.post("/clientes/{id_cliente}/abono")
def registrar_abono(id_cliente: int, datos: AbonoData):
    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE clientes SET deuda_total = deuda_total - :monto WHERE id_cliente = :id_c"),
                         {"monto": datos.monto, "id_c": id_cliente})
            conn.execute(text("""
                INSERT INTO ventas (total, metodo_pago, id_cliente) 
                VALUES (:monto, :pago, :id_c)
            """), {"monto": datos.monto, "pago": "Abono " + datos.metodo_pago, "id_c": id_cliente})
            
            conn.commit()
            return {"mensaje": "Abono registrado con éxito"}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/productos/")
def agregar_producto(producto: ProductoNuevo):
    try:
        with engine.connect() as conexion:
            # ¡MODIFICADO PARA GUARDAR CÓDIGO DE BARRAS!
            query = text("""
                INSERT INTO productos (nombre, id_categoria, precio_compra, precio_venta, stock_actual, unidad_medida, codigo_barras) 
                VALUES (:nom, :cat, :compra, :venta, :stock, :unidad, :codigo) RETURNING id_producto
            """)
            res = conexion.execute(query, {
                "nom": producto.nombre, "cat": producto.id_categoria,
                "compra": producto.precio_compra, "venta": producto.precio_venta,
                "stock": producto.stock_actual, "unidad": producto.unidad_medida,
                "codigo": producto.codigo_barras
            })
            conexion.commit() 
            return {"mensaje": "¡Producto agregado!", "id_producto": res.fetchone()[0]}
    except Exception as e:
        return {"Error": "No se pudo guardar", "Detalle": str(e)}

@app.get("/productos/")
def ver_productos():
    try:
        with engine.connect() as conexion:
            # ¡MODIFICADO PARA ENVIAR EL CÓDIGO DE BARRAS A LA PANTALLA!
            res = conexion.execute(text("""
                SELECT p.id_producto, p.nombre, c.nombre as categoria, p.precio_venta, p.stock_actual, p.precio_compra, p.codigo_barras
                FROM productos p
                JOIN categorias c ON p.id_categoria = c.id_categoria
                ORDER BY p.nombre ASC
            """))
            return [{"id": f[0], "nombre": f[1], "categoria": f[2], "precio_venta": float(f[3]), "stock_actual": float(f[4]), "precio_compra": float(f[5]), "codigo_barras": f[6]} for f in res.fetchall()]
    except Exception as e:
        return {"Error": str(e)}

@app.put("/productos/{id_producto}")
def actualizar_precios(id_producto: int, datos: PrecioData):
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE productos 
                SET precio_compra = :compra, precio_venta = :venta 
                WHERE id_producto = :id_p
            """), {"compra": datos.precio_compra, "venta": datos.precio_venta, "id_p": id_producto})
            conn.commit()
            return {"mensaje": "Precios actualizados con éxito."}
    except Exception as e:
        return {"Error": str(e)}

@app.delete("/productos/{id_producto}")
def eliminar_producto(id_producto: int):
    try:
        with engine.connect() as conexion:
            conexion.execute(text("DELETE FROM productos WHERE id_producto = :id"), {"id": id_producto})
            conexion.commit()
            return {"mensaje": "Producto eliminado exitosamente."}
    except Exception:
        return {"Error": "No se puede eliminar porque ya tiene ventas o mermas asociadas."}

@app.post("/compras/")
def registrar_compra(datos: CompraData):
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE productos 
                SET stock_actual = stock_actual + :cant 
                WHERE id_producto = :id_p
            """), {"cant": datos.cantidad, "id_p": datos.id_producto})
            
            conn.execute(text("""
                INSERT INTO gastos (categoria, monto, descripcion)
                VALUES ('Flete / Viaje a Central de Abastos', :monto, :desc)
            """), {"monto": datos.costo_total, "desc": datos.descripcion})
            
            conn.commit()
            return {"mensaje": "Compra registrada con éxito."}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/ventas/")
def registrar_venta(datos: VentaNueva):
    try:
        with engine.connect() as conn:
            res_venta = conn.execute(
                text("INSERT INTO ventas (total, metodo_pago, id_cliente) VALUES (0, :pago, :cliente) RETURNING id_venta;"),
                {"pago": datos.metodo_pago, "cliente": datos.id_cliente}
            )
            id_venta = res_venta.scalar()
            total_venta = 0
            
            for detalle in datos.detalles:
                id_prod = detalle.id_producto
                cantidad_vendida = detalle.cantidad
                precio = detalle.precio_unitario
                
                subtotal = cantidad_vendida * precio
                total_venta += subtotal
                
                conn.execute(text("""
                    INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario)
                    VALUES (:id_v, :id_p, :cant, :precio)
                """), {"id_v": id_venta, "id_p": id_prod, "cant": cantidad_vendida, "precio": precio})
                
                conn.execute(text("""
                    UPDATE productos 
                    SET stock_actual = stock_actual - :cant 
                    WHERE id_producto = :id_p
                """), {"cant": cantidad_vendida, "id_p": id_prod})
            
            conn.execute(text("UPDATE ventas SET total = :tot WHERE id_venta = :id_v"), 
                         {"tot": total_venta, "id_v": id_venta})
            
            if datos.metodo_pago == "Fiado" and datos.id_cliente:
                conn.execute(text("UPDATE clientes SET deuda_total = deuda_total + :tot WHERE id_cliente = :id_c"),
                             {"tot": total_venta, "id_c": datos.id_cliente})
                
            conn.commit()
            return {"mensaje": "Venta exitosa", "id_venta": id_venta}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/tickets/{id_venta}")
def generar_ticket(id_venta: int):
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT v.id_venta, v.fecha, p.nombre, dv.cantidad, dv.precio_unitario, (dv.cantidad * dv.precio_unitario) as subtotal, v.total
                FROM ventas v
                JOIN detalle_ventas dv ON v.id_venta = dv.id_venta
                JOIN productos p ON dv.id_producto = p.id_producto
                WHERE v.id_venta = :id_v
            """)
            res = conn.execute(query, {"id_v": id_venta}).fetchall()

            if not res:
                return {"Error": "Ticket no encontrado"}

            detalles = [{"producto": f[2], "cantidad": float(f[3]), "precio_unitario": float(f[4]), "subtotal": float(f[5])} for f in res]
            return {"id_venta": res[0][0], "fecha": str(res[0][1]), "total": float(res[0][6]), "detalles": detalles}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/mermas/")
def registrar_merma(merma: MermaNueva):
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("INSERT INTO mermas (id_producto, peso_merma, descripcion) VALUES (:prod, :peso, :desc) RETURNING id_merma"), 
                                   {"prod": merma.id_producto, "peso": merma.peso_merma, "desc": merma.descripcion})
            id_m = res.fetchone()[0]
            conexion.execute(text("UPDATE productos SET stock_actual = stock_actual - :peso WHERE id_producto = :prod"), 
                             {"peso": merma.peso_merma, "prod": merma.id_producto})
            conexion.commit()
        return {"mensaje": "¡Merma registrada!", "id_merma": id_m}
    except Exception as e:
        return {"Error": str(e)}
    
@app.post("/gastos/")
def registrar_gasto(gasto: GastoNuevo):
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("INSERT INTO gastos (categoria, monto, descripcion) VALUES (:cat, :monto, :desc) RETURNING id_gasto"), 
                                   {"cat": gasto.categoria, "monto": gasto.monto, "desc": gasto.descripcion})
            conexion.commit()
            return {"mensaje": "Gasto guardado con éxito"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/gastos/")
def ver_gastos():
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("SELECT categoria, monto, descripcion FROM gastos ORDER BY fecha DESC"))
            return [{"categoria": f[0], "monto": float(f[1]), "descripcion": f[2]} for f in res.fetchall()]
    except Exception:
        return []

@app.get("/reportes/")
def ver_reportes(periodo: str = "General"):
    try:
        with engine.connect() as conexion:
            filtro = ""
            if periodo == "Hoy":
                filtro = "WHERE fecha >= CURRENT_DATE"
            elif periodo == "Semana":
                filtro = "WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'"
            elif periodo == "Mes":
                filtro = "WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'"

            ventas = conexion.execute(text(f"SELECT total, metodo_pago FROM ventas {filtro}")).fetchall()
            gastos = conexion.execute(text(f"SELECT monto, categoria FROM gastos {filtro}")).fetchall()
            filtro_mermas = filtro.replace("fecha", "m.fecha")
            mermas = conexion.execute(text(f"SELECT m.peso_merma, p.precio_compra FROM mermas m JOIN productos p ON m.id_producto = p.id_producto {filtro_mermas}")).fetchall()
            
            t_ventas_efectivo = sum([float(v[0]) for v in ventas if v[1] in ['Efectivo', 'Abono Efectivo'] or v[1] is None])
            t_ventas_banco = sum([float(v[0]) for v in ventas if v[1] in ['Tarjeta', 'Transferencia', 'Abono Tarjeta', 'Abono Transferencia']])
            t_ventas_total = t_ventas_efectivo + t_ventas_banco
            
            t_gastos = sum([float(g[0]) for g in gastos]) if gastos else 0.0
            t_mermas = sum([float(m[0]) * float(m[1]) for m in mermas]) if mermas else 0.0
            
            return {
                "ventas_totales": t_ventas_total,
                "ventas_efectivo": t_ventas_efectivo,
                "ventas_banco": t_ventas_banco,
                "gastos": t_gastos,
                "mermas": t_mermas,
                "ganancia_neta": t_ventas_total - t_gastos - t_mermas,
                "detalle_gastos": [{"categoria": g[1], "monto": float(g[0])} for g in gastos]
            }
    except Exception as e:
        return {"Error": str(e)}