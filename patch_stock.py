import sqlite3
import os

db_path = "ventas.db" 

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("Conectado a la base de datos...")
    
    # 1. Try to add new column if missed by create_all
    try:
        cur.execute("ALTER TABLE productos ADD COLUMN stock_comprometido INTEGER NOT NULL DEFAULT 0")
        print("Columna stock_comprometido agregada.")
    except sqlite3.OperationalError:
        print("La columna stock_comprometido ya existe.")

    # 2. Patch logic for WMS transition
    cur.execute("UPDATE productos SET stock_comprometido = 0")
    
    # 3. For each pending delivery, add back to physical stock and register it as committed
    cur.execute("SELECT id, producto_id, cantidad FROM venta_detalles WHERE entregado = 0")
    detalles = cur.fetchall()
    
    migraciones = 0
    for d in detalles:
        vd_id, prod_id, cant = d
        cur.execute("UPDATE productos SET stock = stock + ?, stock_comprometido = stock_comprometido + ? WHERE id = ?", (cant, cant, prod_id))
        migraciones += 1

    conn.commit()
    conn.close()
    print(f"Migración Completada. Se restauraron {migraciones} pedidos pendientes. El Stock Físico ahora está saneado bajo el nuevo patrón WMS.")
else:
    print(f"Base de datos {db_path} no encontrada.")
