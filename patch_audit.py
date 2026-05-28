import sqlite3
import os

db_path = "ventas.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("Conectado a ventas.db para Parche Arquitectónico Final...")

    # MovimientoStock: stock_comprometido_anterior, stock_comprometido_nuevo
    try:
        cur.execute("ALTER TABLE movimientos_stock ADD COLUMN stock_comprometido_anterior INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE movimientos_stock ADD COLUMN stock_comprometido_nuevo INTEGER NOT NULL DEFAULT 0")
        print("Columnas añadidas a movimientos_stock.")
    except Exception as e:
        print(f"Nota (movimientos_stock): {e}")

    # Pagos: cobrado_por
    try:
        cur.execute("ALTER TABLE pagos ADD COLUMN cobrado_por VARCHAR(100) NOT NULL DEFAULT ''")
        print("Columna añadida a pagos.")
    except Exception as e:
        print(f"Nota (pagos): {e}")

    # VentaEliminada: total_pagado_reembolsado
    try:
        cur.execute("ALTER TABLE ventas_eliminadas ADD COLUMN total_pagado_reembolsado DECIMAL(14, 2) NOT NULL DEFAULT 0")
        print("Columna añadida a ventas_eliminadas.")
    except Exception as e:
        print(f"Nota (ventas_eliminadas): {e}")

    conn.commit()
    conn.close()
    print("Migración Estructural Finalizada Correctamente.")
else:
    print("No se encontró base de datos ventas.db local.")
