# Prompt: Desarrollo de sistema de ventas de zapatillas (bajo volumen, sin stock, pagos a plazos)

## Contexto del negocio
Necesito una aplicación web para gestionar ventas de zapatillas (o tenis) con las siguientes características:
- Volumen de ventas bajo (menos de 50 ventas por mes).
- No se controla stock de productos.
- Las ventas se registran con uno o varios productos.
- El pago puede ser **quincenal o mensual** (el cliente elige la frecuencia y el número de cuotas).
- Si un cliente no paga una cuota en la fecha de vencimiento, se puede **reprogramar** la fecha de vencimiento de esa cuota (solo cambiar la fecha, sin dividir la cuota ni añadir intereses).
- Se necesita un reporte de "deudores" (clientes con cuotas pendientes de pago) con el total adeudado y el detalle de cada cuota impaga.

## Arquitectura requerida (no negociable)
Debes implementar una **arquitectura por capas** con las siguientes tecnologías exactas:

### Lenguaje y framework
- **Backend**: Python 3.12+ con **FastAPI** (no Spring Boot, no Node.js, no Django).
- **Frontend**: Renderizado en servidor con **Jinja2 templates** (sin framework JS pesado, solo HTML + Bootstrap CSS opcional).
- **ORM**: **SQLAlchemy** 2.0 (para mapeo objeto-relacional).
- **Migraciones**: **Alembic**.
- **Base de datos**: **PostgreSQL** (para despliegue en Render, aunque en desarrollo local se pueda usar SQLite, pero el código debe ser compatible con PostgreSQL).
- **Despliegue**: **Render.com** (web service gratuito + PostgreSQL gratuito).

### Estilo arquitectónico
- **Arquitectura hexagonal simplificada** o **capas tradicionales** con separación clara:
  1. Capa de presentación (templates HTML + rutas FastAPI que devuelven HTML).
  2. Capa de aplicación (servicios/lógica de negocio pura, sin dependencias de HTTP ni DB).
  3. Capa de dominio (modelos de datos y reglas: generación de cuotas, reprogramación, registro de pago).
  4. Capa de persistencia (repositorios usando SQLAlchemy).

### Patrones a incluir
- **Repository** para acceso a datos.
- **DTO/Schema** con Pydantic para validación de datos.
- **Unit of Work** implícito mediante sesiones de SQLAlchemy.

## Requisitos funcionales detallados

### Gestión de clientes
- Crear cliente (nombre, teléfono, dirección opcional).
- Listar clientes.

### Gestión de productos (catálogo)
- Crear producto (nombre, precio).
- Listar productos.

### Registro de venta
- Seleccionar cliente (de una lista).
- Seleccionar uno o varios productos (con cantidades, pero sin stock, solo para calcular el total).
- Fecha de la venta.
- Número de cuotas (entero >0) y frecuencia (quincenal o mensual).
- Campo "notas" opcional.
- **Regla de negocio**: Al guardar la venta, se deben generar automáticamente las cuotas con:
  - Monto = total de la venta dividido entre el número de cuotas (el último ajuste para que la suma dé exacto).
  - Fecha de vencimiento = fecha de venta + (15 días por cada cuota si es quincenal) o + (30 días por cuota si es mensual).
  - Cada cuota tiene un número secuencial.
  - Estado inicial: pendiente (fecha_pago_real = NULL).

### Gestión de pagos
- Ver detalle de una venta (mostrar todas las cuotas con su vencimiento, monto, y si está pagada o no).
- Acción **Pagar cuota**: registrar la fecha actual como fecha de pago real.
- Acción **Reprogramar cuota**: cambiar la fecha de vencimiento de una cuota pendiente a una nueva fecha (sin modificar el monto ni generar nuevas cuotas).

### Reportes
- **Deudores**: lista de clientes que tienen al menos una cuota pendiente (fecha_pago_real IS NULL). Para cada cliente mostrar:
  - Nombre del cliente.
  - Total adeudado (suma de montos de cuotas pendientes).
  - Lista de cuotas pendientes (venta asociada, número de cuota, monto, fecha de vencimiento actual).
  - Enlace al detalle de la venta para poder pagar o reprogramar.

### Restricciones técnicas
- No se requiere autenticación de usuarios (por bajo volumen).
- El frontend debe ser navegable (menú básico: Clientes, Productos, Nueva Venta, Reporte Deudores).
- Los formularios deben validar datos básicos (campos obligatorios, fechas correctas).
- Manejar errores de forma amigable (mostrar mensajes en la misma página).

## Entregables esperados (el código completo)

La IA debe generar una respuesta con:

1. **Estructura de carpetas del proyecto** (ej: `app/`, `templates/`, `migrations/`, etc.).
2. **Archivo `requirements.txt`** con todas las dependencias.
3. **Archivo `docker-compose.yml`** opcional (para desarrollo local con PostgreSQL).
4. **Código completo de los modelos SQLAlchemy** (`models.py`).
5. **Código completo de los esquemas Pydantic** (`schemas.py`).
6. **Lógica de negocio** (`services.py` o `crud.py`) con funciones:
   - `generar_cuotas(total, num_cuotas, fecha_inicio, frecuencia) -> list[PagoCreate]`
   - `registrar_pago(pago_id, fecha_pago)`
   - `reprogramar_cuota(pago_id, nueva_fecha)`
   - `obtener_deudores() -> list[dict]`
7. **Rutas/controladores FastAPI** (`main.py` o router separado) con endpoints que rendericen HTML (Jinja2). Incluir:
   - `GET /` (página de inicio con enlaces)
   - `GET /clientes` y `POST /clientes`
   - `GET /productos` y `POST /productos`
   - `GET /ventas/nueva` y `POST /ventas`
   - `GET /ventas/{id}` (detalle)
   - `POST /pagar/{pago_id}`
   - `POST /reprogramar/{pago_id}`
   - `GET /reporte/deudores`
8. **Templates Jinja2** (mínimo: `base.html`, `clientes.html`, `productos.html`, `nueva_venta.html`, `detalle_venta.html`, `reporte_deudores.html`).
   - Usar Bootstrap CDN para estilos (puede ser el básico de Bootstrap 5).
9. **Archivo `render.yaml`** para despliegue automático en Render.com, incluyendo la creación de la base de datos PostgreSQL.
10. **Instrucciones de configuración y despliegue** (variables de entorno, migraciones con Alembic, etc.).

## Consideraciones adicionales
- El código debe ser **limpio, comentado en español o inglés** (como prefieras), y seguir buenas prácticas.
- Asegurar que las fechas se manejen con `datetime.date` (no timezone complicado).
- La generación de cuotas debe redondear correctamente a 2 decimales y ajustar la última cuota para que la suma sea exacta al total.
- En el template `nueva_venta.html`, se puede permitir agregar productos dinámicamente con JavaScript simple (opcional), o bien se puede usar un campo "total" calculado por el usuario. Prefiero la segunda opción para simplicidad: un campo numérico "Total de la venta" que ingrese el usuario, y luego seleccione cliente, número de cuotas y frecuencia. Así evitamos complejidad JS.
- No es necesario implementar API REST, solo renderizado HTML.

## Formato de respuesta de la IA
La IA debe entregar **el código completo en formato texto** organizado por archivos, listo para copiar y pegar. No explicaciones extensas, solo el código y las instrucciones mínimas de uso.

---

**Este prompt ya contiene toda la información necesaria. Copia y pégaselo a tu IA generadora de código favorita.**