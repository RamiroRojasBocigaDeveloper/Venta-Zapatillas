import sqlite3

conn = sqlite3.connect('ventas.db')
conn.row_factory = sqlite3.Row

print("=== TABLAS ===")
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
for t in tables:
    c = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"  {t}: {c}")

print("\n=== CLIENTES ===")
for r in conn.execute("SELECT * FROM clientes"):
    print(f"  #{r['id']}: {r['nombre']} - {r['telefono']}")

print("\n=== PRODUCTOS ===")
for r in conn.execute("SELECT * FROM productos"):
    print(f"  #{r['id']}: {r['nombre']} ({r['marca']})")
    print(f"    Precio: ${r['precio']} | Costo: ${r['precio_compra']}")
    print(f"    Stock: {r['stock']} | Comprometido: {r['stock_comprometido']}")

print("\n=== VENTAS ===")
for r in conn.execute("""
    SELECT v.*, c.nombre as cliente_nombre 
    FROM ventas v JOIN clientes c ON v.cliente_id=c.id
"""):
    pagado = conn.execute("SELECT COALESCE(SUM(monto),0) FROM pagos WHERE venta_id=? AND fecha_pago IS NOT NULL", (r['id'],)).fetchone()[0]
    print(f"  #{r['id']}: {r['fecha']} - {r['cliente_nombre']}")
    print(f"    Total: ${r['total']} | Pagado: ${pagado} | Cuotas: {r['num_cuotas']} ({r['frecuencia']})")
    print(f"    Vendedor: {r['vendedor']} | Notas: {r['notas'] or 'N/A'}")

print("\n=== PAGOS ===")
for r in conn.execute("SELECT * FROM pagos ORDER BY venta_id, numero_cuota"):
    estado = "PAGADO" if r['fecha_pago'] else "PENDIENTE"
    print(f"  Venta #{r['venta_id']} - Cuota {r['numero_cuota']}: ${r['monto']} vence {r['fecha_vencimiento']} - {estado} {r['fecha_pago'] or ''}")

print("\n=== DETALLES ===")
for r in conn.execute("""
    SELECT d.*, p.nombre as prod_nombre FROM venta_detalles d 
    JOIN productos p ON d.producto_id=p.id
"""):
    ent = "ENTREGADO" if r['entregado'] else "PENDIENTE"
    print(f"  Venta #{r['venta_id']}: {r['prod_nombre']} x{r['cantidad']} @ ${r['precio_unitario']} (costo: ${r['precio_compra']}) - {ent}")

print("\n=== MOVIMIENTOS STOCK ===")
for r in conn.execute("""
    SELECT m.*, p.nombre FROM movimientos_stock m 
    JOIN productos p ON m.producto_id=p.id ORDER BY m.id
"""):
    print(f"  #{r['id']}: {r['nombre']} {r['cantidad']:+d} ({r['stock_anterior']}->{r['stock_nuevo']}) | {r['tipo']} | {r['motivo']} | {r['usuario']}")

conn.close()
