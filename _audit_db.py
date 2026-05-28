import sqlite3
from collections import defaultdict

conn = sqlite3.connect('ventas.db')
conn.row_factory = sqlite3.Row

# Tablas y conteos
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("=== TABLAS ===")
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t}: {count} registros")

print("\n=== CLIENTES ===")
for r in conn.execute("SELECT id, nombre, telefono FROM clientes ORDER BY id").fetchall():
    print(f"  #{r['id']}: {r['nombre']} - {r['telefono']}")

print("\n=== PRODUCTOS ===")
for r in conn.execute("SELECT id, nombre, marca, precio, stock FROM productos ORDER BY id").fetchall():
    print(f"  #{r['id']}: {r['nombre']} ({r['marca']}) - ${r['precio']} - stock: {r['stock']}")

print("\n=== VENTAS ===")
for r in conn.execute("""
    SELECT v.id, v.fecha, c.nombre as cliente, v.total, v.num_cuotas, v.frecuencia, v.vendedor
    FROM ventas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id
""").fetchall():
    total_pagado = conn.execute("SELECT COALESCE(SUM(monto),0) FROM pagos WHERE venta_id=? AND fecha_pago IS NOT NULL", (r['id'],)).fetchone()[0]
    print(f"  #{r['id']}: {r['fecha']} - {r['cliente']} - Total: ${r['total']} - Pagado: ${total_pagado} - Cuotas: {r['num_cuotas']} ({r['frecuencia']}) - Vend: {r['vendedor']}")

print("\n=== PAGOS ===")
for r in conn.execute("""
    SELECT p.id, p.venta_id, p.numero_cuota, p.monto, p.fecha_vencimiento, p.fecha_pago
    FROM pagos p ORDER BY p.venta_id, p.numero_cuota
""").fetchall():
    estado = "PAGADO" if r['fecha_pago'] else "PENDIENTE"
    print(f"  Venta #{r['venta_id']} - Cuota {r['numero_cuota']}: ${r['monto']} - Vence {r['fecha_vencimiento']} - {estado} {r['fecha_pago'] or ''}")

print("\n=== DETALLES DE VENTA ===")
for r in conn.execute("""
    SELECT d.id, d.venta_id, p.nombre as producto, d.cantidad, d.precio_unitario, d.precio_compra, d.entregado
    FROM venta_detalles d JOIN productos p ON d.producto_id = p.id ORDER BY d.venta_id
""").fetchall():
    print(f"  Venta #{r['venta_id']} - {r['producto']} x{r['cantidad']} @ ${r['precio_unitario']} (costo: ${r['precio_compra']}) - {'ENTREGADO' if r['entregado'] else 'PENDIENTE'}")

print("\n=== MOVIMIENTOS STOCK ===")
for r in conn.execute("""
    SELECT m.id, p.nombre, m.cantidad, m.stock_anterior, m.stock_nuevo, m.tipo, m.motivo, m.usuario, m.fecha_hora
    FROM movimientos_stock m JOIN productos p ON m.producto_id = p.id ORDER BY m.id
""").fetchall():
    print(f"  {r['nombre']}: {r['cantidad']:+d} ({r['stock_anterior']} -> {r['stock_nuevo']}) - {r['tipo']} - {r['motivo']} - {r['usuario']} @ {r['fecha_hora']}")

print("\n=== VENTAS ELIMINADAS ===")
for r in conn.execute("SELECT * FROM ventas_eliminadas ORDER BY id").fetchall():
    print(f"  #{r['id']}: Venta original #{r['venta_id_original']} - {r['cliente_nombre']} - ${r['total']} - Eliminó: {r['usuario_que_elimino']} - {r['fecha_eliminacion']}")

# Validaciones de integridad
print("\n\n=== VALIDACIONES DE INTEGRIDAD ===")

# 1. Ventas con pagos que suman mas que el total
print("\n1. Pagos totales vs Total de venta:")
for r in conn.execute("""
    SELECT v.id, v.total, COALESCE(SUM(p.monto),0) as pagado,
           CASE WHEN p.fecha_pago IS NOT NULL THEN 1 ELSE 0 END as pagado_flag
    FROM ventas v LEFT JOIN pagos p ON p.venta_id = v.id
    GROUP BY v.id
""").fetchall():
    estado = "OK" if r['pagado'] <= r['total'] else f"EXCESO: ${r['pagado'] - r['total']}"
    print(f"  Venta #{r['id']}: Total=${r['total']}, Pagado=${r['pagado']} - {estado}")

# 2. Stock que deberia dar negativo
print("\n2. Productos con stock negativo:")
for r in conn.execute("SELECT id, nombre, stock FROM productos WHERE stock < 0").fetchall():
    print(f"  #{r['id']}: {r['nombre']} - stock={r['stock']}")

# 3. Cuotas vencidas impagas
print("\n3. Cuotas vencidas impagas:")
for r in conn.execute("""
    SELECT p.id, p.venta_id, p.numero_cuota, p.monto, p.fecha_vencimiento, c.nombre as cliente
    FROM pagos p JOIN ventas v ON p.venta_id = v.id JOIN clientes c ON v.cliente_id = c.id
    WHERE p.fecha_pago IS NULL AND p.fecha_vencimiento < date('now')
    ORDER BY p.fecha_vencimiento
""").fetchall():
    print(f"  Venta #{r['venta_id']} - Cuota {r['numero_cuota']}: ${r['monto']} vence {r['fecha_vencimiento']} - Cliente: {r['cliente']}")

# 4. Verificar que ganancia_periodo funcione correctamente
print("\n4. Ganancia estimada (precio_venta - precio_compra) por detalle:")
for r in conn.execute("""
    SELECT v.id as venta_id, p.nombre, d.cantidad, d.precio_unitario, d.precio_compra,
           (d.precio_unitario - COALESCE(d.precio_compra, 0)) * d.cantidad as ganancia
    FROM venta_detalles d JOIN productos p ON d.producto_id = p.id JOIN ventas v ON d.venta_id = v.id
    ORDER BY v.id
""").fetchall():
    margen = ((r['precio_unitario'] - r['precio_compra']) / r['precio_compra'] * 100) if r['precio_compra'] and r['precio_compra'] > 0 else 0
    print(f"  Venta #{r['venta_id']} - {r['nombre']}: {r['cantidad']}x ${r['precio_unitario']} (costo ${r['precio_compra']}) -> ganancia ${r['ganancia']} ({margen:.0f}% margen)")

conn.close()
