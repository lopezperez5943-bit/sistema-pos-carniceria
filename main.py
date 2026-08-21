from fastapi import FastAPI
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from typing import List

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS (AHORA ES LOCAL) ---
# Se comentó la conexión a Neon (Nube) para usar tu PC como servidor local
# URL_BASE_DATOS_NUBE = "postgresql+psycopg2://neondb_owner:npg_x0MisXCT7IwP@..."

# --- 1. CONEXIÓN A LA BASE DE DATOS EN LA NUBE (NEON) ---
URL_BASE_DATOS = "postgresql://neondb_owner:npg_Ycz1MT9nRBtL@ep-patient-term-axk6tdgq-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(URL_BASE_DATOS)

engine = create_engine(
    URL_BASE_DATOS, 
    connect_args={'client_encoding': 'utf8'} # Protegido contra acentos y eñes
)
app = FastAPI(title="API POS - Carnicería")

# --- 2. MODELOS DE DATOS (ADAPTADOS PARA GRAMOS Y MERMAS) ---

class CategoriaNueva(BaseModel):
    nombre: str

class ProductoNuevo(BaseModel):
    nombre: str
    id_categoria: int
    precio_compra: float  # Usamos float para aceptar decimales
    precio_venta: float
    stock_actual: float = 0.000 
    unidad_medida: str = "KG"

class DetalleVenta(BaseModel):
    id_producto: int
    cantidad: float       # Soporta vender 0.250 kg
    precio_unitario: float

class VentaNueva(BaseModel):
    detalles: List[DetalleVenta] # Recibe una lista de varios productos en un solo ticket

class MermaNueva(BaseModel):
    id_producto: int
    peso_merma: float
    descripcion: str = "Recorte de grasa / Hueso"

class GastoNuevo(BaseModel):
    categoria: str
    monto: float
    descripcion: str = ""

# --- 3. RUTAS / ENDPOINTS DEL SISTEMA ---

@app.get("/")
def probar_conexion():
    return {"Estado": "¡Éxito! Motor de la carnicería operando al 100% en local."}

# A) CATEGORÍAS
@app.get("/categorias/")
def ver_categorias():
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("SELECT id_categoria, nombre FROM categorias"))
            return [{"id": fila[0], "nombre": fila[1]} for fila in res.fetchall()]
    except Exception as e:
        return {"Error": str(e)}

# B) PRODUCTOS Y STOCK DIRECTO
@app.post("/productos/")
def agregar_producto(producto: ProductoNuevo):
    try:
        with engine.connect() as conexion:
            query = text("""
                INSERT INTO productos (nombre, id_categoria, precio_compra, precio_venta, stock_actual, unidad_medida) 
                VALUES (:nom, :cat, :compra, :venta, :stock, :unidad) RETURNING id_producto
            """)
            res = conexion.execute(query, {
                "nom": producto.nombre, "cat": producto.id_categoria,
                "compra": producto.precio_compra, "venta": producto.precio_venta,
                "stock": producto.stock_actual, "unidad": producto.unidad_medida
            })
            conexion.commit() 
            return {"mensaje": "¡Corte de carne agregado!", "id_producto": res.fetchone()[0]}
    except Exception as e:
        return {"Error": "No se pudo guardar", "Detalle": str(e)}

@app.get("/productos/")
def ver_productos():
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("""
                SELECT p.id_producto, p.nombre, c.nombre as categoria, p.precio_venta, p.stock_actual 
                FROM productos p
                JOIN categorias c ON p.id_categoria = c.id_categoria
                ORDER BY p.nombre ASC
            """))
            return [{"id": f[0], "nombre": f[1], "categoria": f[2], "precio_venta": float(f[3]), "stock_actual": float(f[4])} for f in res.fetchall()]
    except Exception as e:
        return {"Error": str(e)}

from sqlalchemy import text # Asegúrate de tener esto importado arriba si no lo tienes

@app.post("/ventas/")
def registrar_venta(datos: dict):
    try:
        with engine.connect() as conn:
            # 1. Crear el ticket de venta (iniciando el total en 0)
            res_venta = conn.execute(text("INSERT INTO ventas (total) VALUES (0) RETURNING id_venta;"))
            id_venta = res_venta.scalar()
            
            total_venta = 0
            
            # 2. Procesar cada producto en el carrito de compras
            for detalle in datos["detalles"]:
                id_prod = detalle["id_producto"]
                cantidad_vendida = detalle["cantidad"]
                precio = detalle["precio_unitario"]
                
                subtotal = cantidad_vendida * precio
                total_venta += subtotal
                
                # A) Guardar el registro en el detalle del ticket
                conn.execute(text("""
                    INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario)
                    VALUES (:id_v, :id_p, :cant, :precio)
                """), {"id_v": id_venta, "id_p": id_prod, "cant": cantidad_vendida, "precio": precio})
                
                # B) ¡LA PARTE QUE FALTABA! Descontar los kilos del inventario
                conn.execute(text("""
                    UPDATE productos 
                    SET stock_actual = stock_actual - :cant 
                    WHERE id_producto = :id_p
                """), {"cant": cantidad_vendida, "id_p": id_prod})
            
            # 3. Actualizar el costo total final del ticket
            conn.execute(text("UPDATE ventas SET total = :tot WHERE id_venta = :id_v"), 
                         {"tot": total_venta, "id_v": id_venta})
            
            # 4. Confirmar y guardar los cambios en Neon
            conn.commit()
            
            return {"mensaje": "Venta exitosa e inventario actualizado", "id_venta": id_venta}
    except Exception as e:
        return {"Error": str(e)}

# D) CONTROL ESTRICTO DE MERMAS
@app.post("/mermas/")
def registrar_merma(merma: MermaNueva):
    try:
        with engine.connect() as conexion:
            query_merma = text("""
                INSERT INTO mermas (id_producto, peso_merma, descripcion)
                VALUES (:prod, :peso, :desc) RETURNING id_merma
            """)
            res = conexion.execute(query_merma, {
                "prod": merma.id_producto, "peso": merma.peso_merma, "desc": merma.descripcion
            })
            id_m = res.fetchone()[0]
            
            # Descontamos el hueso/grasa del stock principal
            conexion.execute(text("UPDATE productos SET stock_actual = stock_actual - :peso WHERE id_producto = :prod"), 
                             {"peso": merma.peso_merma, "prod": merma.id_producto})
            conexion.commit()
            
        return {"mensaje": "¡Merma registrada y descontada del inventario!", "id_merma": id_m, "kilos_descontados": merma.peso_merma}
    except Exception as e:
        return {"Error": "No se pudo registrar la merma", "Detalle": str(e)}
    
# E) CONTROL DE GASTOS
@app.post("/gastos/")
def registrar_gasto(gasto: GastoNuevo):
    try:
        with engine.connect() as conexion:
            query = text("""
                INSERT INTO gastos (categoria, monto, descripcion)
                VALUES (:cat, :monto, :desc) RETURNING id_gasto
            """)
            res = conexion.execute(query, {
                "cat": gasto.categoria, 
                "monto": gasto.monto, 
                "desc": gasto.descripcion
            })
            conexion.commit()
            return {"mensaje": "Gasto guardado con éxito", "id_gasto": res.fetchone()[0]}
    except Exception as e:
        return {"Error": "No se pudo guardar el gasto", "Detalle": str(e)}
    
# F) ELIMINAR PRODUCTOS
@app.delete("/productos/{id_producto}")
def eliminar_producto(id_producto: int):
    try:
        with engine.connect() as conexion:
            conexion.execute(text("DELETE FROM productos WHERE id_producto = :id"), {"id": id_producto})
            conexion.commit()
            return {"mensaje": "Producto eliminado exitosamente."}
    except Exception:
        return {"Error": "No se puede eliminar porque ya tiene ventas o mermas asociadas."}

# G) VER HISTORIAL DE GASTOS
@app.get("/gastos/")
def ver_gastos():
    try:
        with engine.connect() as conexion:
            res = conexion.execute(text("SELECT categoria, monto, descripcion FROM gastos ORDER BY fecha DESC"))
            return [{"categoria": f[0], "monto": float(f[1]), "descripcion": f[2]} for f in res.fetchall()]
    except Exception:
        return []

# H) REPORTES Y GRÁFICAS FINANCIERAS (AHORA CON FILTRO DE TIEMPO)
@app.get("/reportes/")
def ver_reportes(periodo: str = "General"):
    try:
        with engine.connect() as conexion:
            # 1. Configurar el filtro de fecha según lo que pida la pantalla
            filtro = ""
            if periodo == "Hoy":
                filtro = "WHERE fecha >= CURRENT_DATE"
            elif periodo == "Semana":
                filtro = "WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'"
            elif periodo == "Mes":
                filtro = "WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'"

            # 2. Consultas con el filtro aplicado
            ventas = conexion.execute(text(f"SELECT total FROM ventas {filtro}")).fetchall()
            gastos = conexion.execute(text(f"SELECT monto, categoria FROM gastos {filtro}")).fetchall()
            
            # Para las mermas, especificamos que la fecha es de la tabla mermas (m)
            filtro_mermas = filtro.replace("fecha", "m.fecha")
            mermas = conexion.execute(text(f"SELECT m.peso_merma, p.precio_compra FROM mermas m JOIN productos p ON m.id_producto = p.id_producto {filtro_mermas}")).fetchall()
            
            # 3. Sumatorias
            t_ventas = sum([float(v[0]) for v in ventas]) if ventas else 0.0
            t_gastos = sum([float(g[0]) for g in gastos]) if gastos else 0.0
            t_mermas = sum([float(m[0]) * float(m[1]) for m in mermas]) if mermas else 0.0
            
            return {
                "ventas": t_ventas, "gastos": t_gastos, "mermas": t_mermas,
                "ganancia_neta": t_ventas - t_gastos - t_mermas,
                "detalle_gastos": [{"categoria": g[1], "monto": float(g[0])} for g in gastos]
            }
    except Exception as e:
        return {"Error": str(e)}