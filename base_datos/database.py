import hashlib
import hmac
import secrets
import sqlite3

from pathlib import Path


# Ubicación de la base de datos
DB_PATH = Path(__file__).with_name("autofix.db")


# Estados permitidos para las órdenes
ESTADOS = (
    "En recepción",
    "En diagnóstico",
    "En espera de repuestos",
    "En reparación",
    "Listo para entrega",
    "Entregado",
)


# Credenciales iniciales
USUARIO_INICIAL = "admin"
CLAVE_INICIAL = "AutoFix2026"
ITERACIONES_HASH = 200_000


def _crear_hash_clave(clave, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        clave.encode("utf-8"),
        salt,
        ITERACIONES_HASH
    )


def conectar():
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


def _agregar_columna_si_falta(
    conexion,
    tabla,
    columna,
    definicion
):
    """Agrega una columna sin borrar los datos existentes."""
    columnas = {
        fila[1]
        for fila in conexion.execute(
            f"PRAGMA table_info({tabla})"
        ).fetchall()
    }

    if columna not in columnas:
        conexion.execute(
            f"ALTER TABLE {tabla} "
            f"ADD COLUMN {columna} {definicion}"
        )


def crear_tablas():
    conexion = conectar()

    try:
        conexion.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                direccion TEXT
            );

            CREATE TABLE IF NOT EXISTS vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                placa TEXT NOT NULL UNIQUE,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                anio INTEGER,
                FOREIGN KEY (cliente_id)
                    REFERENCES clientes(id)
            );

            CREATE TABLE IF NOT EXISTS ordenes_servicio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehiculo_id INTEGER NOT NULL,
                fecha_ingreso TEXT NOT NULL
                    DEFAULT (datetime('now', 'localtime')),
                problema_reportado TEXT NOT NULL,
                diagnostico TEXT,
                estado TEXT NOT NULL
                    DEFAULT 'En recepción',
                fecha_entrega TEXT,
                costo_mano_obra REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (vehiculo_id)
                    REFERENCES vehiculos(id)
            );

            CREATE TABLE IF NOT EXISTS repuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                cantidad INTEGER NOT NULL DEFAULT 0,
                stock_minimo INTEGER NOT NULL DEFAULT 0,
                precio REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS repuestos_utilizados (
                orden_id INTEGER NOT NULL,
                repuesto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                PRIMARY KEY (orden_id, repuesto_id),
                FOREIGN KEY (orden_id)
                    REFERENCES ordenes_servicio(id),
                FOREIGN KEY (repuesto_id)
                    REFERENCES repuestos(id)
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_usuario TEXT NOT NULL UNIQUE,
                clave_hash BLOB NOT NULL,
                salt BLOB NOT NULL,
                rol TEXT NOT NULL
                    DEFAULT 'Administrador',
                activo INTEGER NOT NULL DEFAULT 1
            );
        """)

        # Migración segura para bases de datos creadas antes
        # de incorporar el módulo de gestión financiera.
        _agregar_columna_si_falta(
            conexion,
            "ordenes_servicio",
            "estado_pago",
            "TEXT NOT NULL DEFAULT 'Pendiente'"
        )

        _agregar_columna_si_falta(
            conexion,
            "ordenes_servicio",
            "fecha_pago",
            "TEXT"
        )

        usuario_existente = conexion.execute(
            """SELECT id
               FROM usuarios
               WHERE nombre_usuario = ?""",
            (USUARIO_INICIAL,)
        ).fetchone()

        if usuario_existente is None:
            salt = secrets.token_bytes(16)

            clave_hash = _crear_hash_clave(
                CLAVE_INICIAL,
                salt
            )

            conexion.execute(
                """INSERT INTO usuarios
                   (
                       nombre_usuario,
                       clave_hash,
                       salt,
                       rol
                   )
                   VALUES (?, ?, ?, ?)""",
                (
                    USUARIO_INICIAL,
                    clave_hash,
                    salt,
                    "Administrador"
                )
            )

        conexion.commit()

    finally:
        conexion.close()


def validar_usuario(nombre_usuario, clave):
    conexion = conectar()

    try:
        usuario = conexion.execute(
            """SELECT nombre_usuario,
                      clave_hash,
                      salt,
                      rol
               FROM usuarios
               WHERE nombre_usuario = ?
               AND activo = 1""",
            (nombre_usuario,)
        ).fetchone()

        if usuario is None:
            return None

        nombre = usuario[0]
        clave_guardada = usuario[1]
        salt = usuario[2]
        rol = usuario[3]

        clave_calculada = _crear_hash_clave(
            clave,
            salt
        )

        if not hmac.compare_digest(
            clave_guardada,
            clave_calculada
        ):
            return None

        return {
            "nombre_usuario": nombre,
            "rol": rol
        }

    finally:
        conexion.close()


def obtener_indicadores():
    conexion = conectar()

    try:
        vehiculos = conexion.execute(
            """SELECT COUNT(*)
               FROM ordenes_servicio
               WHERE estado != 'Entregado'"""
        ).fetchone()[0]

        repuestos = conexion.execute(
            """SELECT COUNT(*)
               FROM repuestos
               WHERE cantidad <= stock_minimo"""
        ).fetchone()[0]

        return vehiculos, repuestos

    finally:
        conexion.close()


def buscar_clientes(texto=""):
    conexion = conectar()

    try:
        patron = f"%{str(texto).strip()}%"
        return conexion.execute(
            """SELECT
                   c.id,
                   c.nombre,
                   COALESCE(c.telefono, ''),
                   COALESCE(c.direccion, ''),
                   COUNT(v.id) AS total_vehiculos
               FROM clientes AS c
               LEFT JOIN vehiculos AS v
                   ON c.id = v.cliente_id
               WHERE c.nombre LIKE ?
                  OR COALESCE(c.telefono, '') LIKE ?
               GROUP BY c.id, c.nombre, c.telefono, c.direccion
               ORDER BY c.nombre
               LIMIT 50""",
            (patron, patron)
        ).fetchall()

    finally:
        conexion.close()


def obtener_vehiculos_cliente(cliente_id):
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT id, placa, marca, modelo, anio
               FROM vehiculos
               WHERE cliente_id = ?
               ORDER BY placa""",
            (cliente_id,)
        ).fetchall()

    finally:
        conexion.close()


def registrar_recepcion(
    nombre,
    telefono,
    direccion,
    placa,
    marca,
    modelo,
    anio,
    problema,
    cliente_id=None,
    vehiculo_id=None
):
    conexion = conectar()

    try:
        with conexion:
            if cliente_id is not None:
                cliente = conexion.execute(
                    """SELECT id
                       FROM clientes
                       WHERE id = ?""",
                    (cliente_id,)
                ).fetchone()

                if cliente is None:
                    raise ValueError(
                        "El cliente seleccionado ya no existe."
                    )

                conexion.execute(
                    """UPDATE clientes
                       SET nombre = ?, telefono = ?, direccion = ?
                       WHERE id = ?""",
                    (nombre, telefono, direccion, cliente_id)
                )

            if vehiculo_id is not None:
                vehiculo_existente = conexion.execute(
                    """SELECT id, cliente_id
                       FROM vehiculos
                       WHERE id = ?""",
                    (vehiculo_id,)
                ).fetchone()

                if vehiculo_existente is None:
                    raise ValueError(
                        "El vehículo seleccionado ya no existe."
                    )

                if (
                    cliente_id is not None
                    and vehiculo_existente[1] != cliente_id
                ):
                    raise ValueError(
                        "El vehículo no pertenece al cliente seleccionado."
                    )
            else:
                vehiculo_existente = conexion.execute(
                    """SELECT id, cliente_id
                       FROM vehiculos
                       WHERE placa = ?""",
                    (placa,)
                ).fetchone()

            if vehiculo_existente:
                vehiculo_id = vehiculo_existente[0]
                propietario_id = vehiculo_existente[1]

                if cliente_id is not None and propietario_id != cliente_id:
                    raise ValueError(
                        "La placa indicada pertenece a otro cliente."
                    )

                cliente_id = propietario_id

                orden_activa = conexion.execute(
                    """SELECT id
                       FROM ordenes_servicio
                       WHERE vehiculo_id = ?
                       AND estado != 'Entregado'
                       ORDER BY id DESC
                       LIMIT 1""",
                    (vehiculo_id,)
                ).fetchone()

                if orden_activa:
                    raise ValueError(
                        "Este vehículo ya tiene la orden "
                        f"activa N.º {orden_activa[0]}."
                    )

                conexion.execute(
                    """UPDATE clientes
                       SET nombre = ?, telefono = ?, direccion = ?
                       WHERE id = ?""",
                    (nombre, telefono, direccion, cliente_id)
                )

                conexion.execute(
                    """UPDATE vehiculos
                       SET marca = ?,
                           modelo = ?,
                           anio = ?
                       WHERE id = ?""",
                    (
                        marca,
                        modelo,
                        anio,
                        vehiculo_id
                    )
                )

            elif cliente_id is None:
                cursor = conexion.execute(
                    """INSERT INTO clientes
                       (
                           nombre,
                           telefono,
                           direccion
                       )
                       VALUES (?, ?, ?)""",
                    (
                        nombre,
                        telefono,
                        direccion
                    )
                )

                cliente_id = cursor.lastrowid

            if vehiculo_existente is None:

                cursor = conexion.execute(
                    """INSERT INTO vehiculos
                       (
                           cliente_id,
                           placa,
                           marca,
                           modelo,
                           anio
                       )
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        cliente_id,
                        placa,
                        marca,
                        modelo,
                        anio
                    )
                )

                vehiculo_id = cursor.lastrowid

            cursor = conexion.execute(
                """INSERT INTO ordenes_servicio
                   (
                       vehiculo_id,
                       problema_reportado
                   )
                   VALUES (?, ?)""",
                (
                    vehiculo_id,
                    problema
                )
            )

            return cursor.lastrowid

    finally:
        conexion.close()


def obtener_ordenes():
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT
                   o.id,
                   c.nombre,
                   v.marca || ' ' || v.modelo,
                   o.estado
               FROM ordenes_servicio AS o
               JOIN vehiculos AS v
                   ON o.vehiculo_id = v.id
               JOIN clientes AS c
                   ON v.cliente_id = c.id
               ORDER BY o.id DESC"""
        ).fetchall()

    finally:
        conexion.close()


def actualizar_estado(orden_id, nuevo_estado):
    if nuevo_estado not in ESTADOS:
        raise ValueError("Estado no válido.")

    conexion = conectar()

    try:
        with conexion:
            if nuevo_estado == "Entregado":
                cursor = conexion.execute(
                    """UPDATE ordenes_servicio
                       SET estado = ?,
                           fecha_entrega =
                               datetime('now', 'localtime')
                       WHERE id = ?""",
                    (
                        nuevo_estado,
                        orden_id
                    )
                )

            else:
                cursor = conexion.execute(
                    """UPDATE ordenes_servicio
                       SET estado = ?,
                           fecha_entrega = NULL
                       WHERE id = ?""",
                    (
                        nuevo_estado,
                        orden_id
                    )
                )

            if cursor.rowcount == 0:
                raise ValueError(
                    "La orden seleccionada no existe."
                )

            return cursor.rowcount

    finally:
        conexion.close()


def obtener_repuestos():
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT
                   id,
                   nombre,
                   descripcion,
                   cantidad,
                   stock_minimo,
                   precio
               FROM repuestos
               ORDER BY nombre"""
        ).fetchall()

    finally:
        conexion.close()


def registrar_repuesto(
    nombre,
    descripcion,
    cantidad,
    stock_minimo,
    precio
):
    conexion = conectar()

    try:
        with conexion:
            conexion.execute(
                """INSERT INTO repuestos
                   (
                       nombre,
                       descripcion,
                       cantidad,
                       stock_minimo,
                       precio
                   )
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    nombre,
                    descripcion,
                    cantidad,
                    stock_minimo,
                    precio
                )
            )

    finally:
        conexion.close()


def actualizar_cantidad_repuesto(
    repuesto_id,
    nueva_cantidad
):
    conexion = conectar()

    try:
        with conexion:
            cursor = conexion.execute(
                """UPDATE repuestos
                   SET cantidad = ?
                   WHERE id = ?""",
                (
                    nueva_cantidad,
                    repuesto_id
                )
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "El repuesto seleccionado no existe."
                )

            return cursor.rowcount

    finally:
        conexion.close()


# ============================================================
# GESTIÓN FINANCIERA
# ============================================================

def obtener_ordenes_financieras():
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT
                   o.id,
                   c.nombre,
                   v.placa,
                   v.marca || ' ' || v.modelo,
                   o.estado,
                   o.costo_mano_obra,
                   COALESCE(SUM(
                       ru.cantidad * ru.precio_unitario
                   ), 0) AS total_repuestos,
                   o.costo_mano_obra + COALESCE(SUM(
                       ru.cantidad * ru.precio_unitario
                   ), 0) AS total_orden,
                   o.estado_pago,
                   o.fecha_pago
               FROM ordenes_servicio AS o
               JOIN vehiculos AS v
                   ON o.vehiculo_id = v.id
               JOIN clientes AS c
                   ON v.cliente_id = c.id
               LEFT JOIN repuestos_utilizados AS ru
                   ON o.id = ru.orden_id
               GROUP BY
                   o.id,
                   c.nombre,
                   v.placa,
                   v.marca,
                   v.modelo,
                   o.estado,
                   o.costo_mano_obra,
                   o.estado_pago,
                   o.fecha_pago
               ORDER BY o.id DESC"""
        ).fetchall()

    finally:
        conexion.close()


def obtener_detalle_financiero(orden_id):
    conexion = conectar()

    try:
        orden = conexion.execute(
            """SELECT
                   o.id,
                   c.nombre,
                   v.placa,
                   v.marca || ' ' || v.modelo,
                   o.problema_reportado,
                   o.estado,
                   o.costo_mano_obra,
                   o.estado_pago,
                   o.fecha_pago
               FROM ordenes_servicio AS o
               JOIN vehiculos AS v
                   ON o.vehiculo_id = v.id
               JOIN clientes AS c
                   ON v.cliente_id = c.id
               WHERE o.id = ?""",
            (orden_id,)
        ).fetchone()

        if orden is None:
            raise ValueError(
                "La orden seleccionada no existe."
            )

        repuestos = conexion.execute(
            """SELECT
                   ru.repuesto_id,
                   r.nombre,
                   ru.cantidad,
                   ru.precio_unitario,
                   ru.cantidad * ru.precio_unitario
               FROM repuestos_utilizados AS ru
               JOIN repuestos AS r
                   ON ru.repuesto_id = r.id
               WHERE ru.orden_id = ?
               ORDER BY r.nombre""",
            (orden_id,)
        ).fetchall()

        total_repuestos = sum(
            fila[4] for fila in repuestos
        )

        return {
            "id": orden[0],
            "cliente": orden[1],
            "placa": orden[2],
            "vehiculo": orden[3],
            "problema": orden[4],
            "estado": orden[5],
            "mano_obra": float(orden[6]),
            "estado_pago": orden[7],
            "fecha_pago": orden[8],
            "repuestos": repuestos,
            "total_repuestos": float(total_repuestos),
            "total": float(orden[6]) + float(total_repuestos)
        }

    finally:
        conexion.close()


def obtener_repuestos_disponibles():
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT
                   id,
                   nombre,
                   cantidad,
                   precio
               FROM repuestos
               WHERE cantidad > 0
               ORDER BY nombre"""
        ).fetchall()

    finally:
        conexion.close()


def actualizar_mano_obra(orden_id, costo_mano_obra):
    try:
        costo = float(costo_mano_obra)
    except (TypeError, ValueError):
        raise ValueError(
            "El costo de mano de obra no es válido."
        )

    if costo < 0:
        raise ValueError(
            "El costo de mano de obra no puede ser negativo."
        )

    conexion = conectar()

    try:
        with conexion:
            orden = conexion.execute(
                """SELECT estado_pago
                   FROM ordenes_servicio
                   WHERE id = ?""",
                (orden_id,)
            ).fetchone()

            if orden is None:
                raise ValueError(
                    "La orden seleccionada no existe."
                )

            if orden[0] == "Pagado":
                raise ValueError(
                    "No se puede modificar una orden pagada."
                )

            conexion.execute(
                """UPDATE ordenes_servicio
                   SET costo_mano_obra = ?
                   WHERE id = ?""",
                (costo, orden_id)
            )

    finally:
        conexion.close()


def agregar_repuesto_a_orden(
    orden_id,
    repuesto_id,
    cantidad
):
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValueError(
            "La cantidad del repuesto no es válida."
        )

    if cantidad <= 0:
        raise ValueError(
            "La cantidad debe ser mayor que cero."
        )

    conexion = conectar()

    try:
        with conexion:
            orden = conexion.execute(
                """SELECT estado_pago
                   FROM ordenes_servicio
                   WHERE id = ?""",
                (orden_id,)
            ).fetchone()

            if orden is None:
                raise ValueError(
                    "La orden seleccionada no existe."
                )

            if orden[0] == "Pagado":
                raise ValueError(
                    "No se pueden agregar repuestos "
                    "a una orden pagada."
                )

            repuesto = conexion.execute(
                """SELECT nombre, cantidad, precio
                   FROM repuestos
                   WHERE id = ?""",
                (repuesto_id,)
            ).fetchone()

            if repuesto is None:
                raise ValueError(
                    "El repuesto seleccionado no existe."
                )

            nombre, existencia, precio = repuesto

            if existencia < cantidad:
                raise ValueError(
                    f"Stock insuficiente para {nombre}. "
                    f"Disponible: {existencia}."
                )

            utilizado = conexion.execute(
                """SELECT cantidad
                   FROM repuestos_utilizados
                   WHERE orden_id = ?
                   AND repuesto_id = ?""",
                (orden_id, repuesto_id)
            ).fetchone()

            if utilizado is None:
                conexion.execute(
                    """INSERT INTO repuestos_utilizados
                       (
                           orden_id,
                           repuesto_id,
                           cantidad,
                           precio_unitario
                       )
                       VALUES (?, ?, ?, ?)""",
                    (
                        orden_id,
                        repuesto_id,
                        cantidad,
                        precio
                    )
                )

            else:
                conexion.execute(
                    """UPDATE repuestos_utilizados
                       SET cantidad = cantidad + ?
                       WHERE orden_id = ?
                       AND repuesto_id = ?""",
                    (
                        cantidad,
                        orden_id,
                        repuesto_id
                    )
                )

            cursor = conexion.execute(
                """UPDATE repuestos
                   SET cantidad = cantidad - ?
                   WHERE id = ?
                   AND cantidad >= ?""",
                (
                    cantidad,
                    repuesto_id,
                    cantidad
                )
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "No fue posible descontar el inventario."
                )

    finally:
        conexion.close()


def quitar_repuesto_de_orden(orden_id, repuesto_id):
    conexion = conectar()

    try:
        with conexion:
            orden = conexion.execute(
                """SELECT estado_pago
                   FROM ordenes_servicio
                   WHERE id = ?""",
                (orden_id,)
            ).fetchone()

            if orden is None:
                raise ValueError(
                    "La orden seleccionada no existe."
                )

            if orden[0] == "Pagado":
                raise ValueError(
                    "No se pueden quitar repuestos "
                    "de una orden pagada."
                )

            utilizado = conexion.execute(
                """SELECT cantidad
                   FROM repuestos_utilizados
                   WHERE orden_id = ?
                   AND repuesto_id = ?""",
                (orden_id, repuesto_id)
            ).fetchone()

            if utilizado is None:
                raise ValueError(
                    "El repuesto no está registrado en la orden."
                )

            cantidad = utilizado[0]

            conexion.execute(
                """UPDATE repuestos
                   SET cantidad = cantidad + ?
                   WHERE id = ?""",
                (cantidad, repuesto_id)
            )

            conexion.execute(
                """DELETE FROM repuestos_utilizados
                   WHERE orden_id = ?
                   AND repuesto_id = ?""",
                (orden_id, repuesto_id)
            )

    finally:
        conexion.close()


def cambiar_estado_pago(orden_id, nuevo_estado):
    if nuevo_estado not in ("Pendiente", "Pagado"):
        raise ValueError(
            "El estado de pago no es válido."
        )

    conexion = conectar()

    try:
        with conexion:
            orden = conexion.execute(
                """SELECT
                       costo_mano_obra,
                       estado_pago
                   FROM ordenes_servicio
                   WHERE id = ?""",
                (orden_id,)
            ).fetchone()

            if orden is None:
                raise ValueError(
                    "La orden seleccionada no existe."
                )

            total_repuestos = conexion.execute(
                """SELECT COALESCE(SUM(
                       cantidad * precio_unitario
                   ), 0)
                   FROM repuestos_utilizados
                   WHERE orden_id = ?""",
                (orden_id,)
            ).fetchone()[0]

            total = float(orden[0]) + float(total_repuestos)

            if nuevo_estado == "Pagado" and total <= 0:
                raise ValueError(
                    "La orden no puede marcarse como pagada "
                    "porque su total es cero."
                )

            if nuevo_estado == "Pagado":
                conexion.execute(
                    """UPDATE ordenes_servicio
                       SET estado_pago = 'Pagado',
                           fecha_pago =
                               datetime('now', 'localtime')
                       WHERE id = ?""",
                    (orden_id,)
                )

            else:
                conexion.execute(
                    """UPDATE ordenes_servicio
                       SET estado_pago = 'Pendiente',
                           fecha_pago = NULL
                       WHERE id = ?""",
                    (orden_id,)
                )

            return total

    finally:
        conexion.close()


def obtener_resumen_financiero():
    conexion = conectar()

    try:
        fila = conexion.execute(
            """SELECT
                   COALESCE(SUM(
                       costo_mano_obra + COALESCE((
                           SELECT SUM(
                               ru.cantidad * ru.precio_unitario
                           )
                           FROM repuestos_utilizados AS ru
                           WHERE ru.orden_id = o.id
                       ), 0)
                   ), 0),
                   COALESCE(SUM(CASE
                       WHEN estado_pago = 'Pagado' THEN
                           costo_mano_obra + COALESCE((
                               SELECT SUM(
                                   ru.cantidad * ru.precio_unitario
                               )
                               FROM repuestos_utilizados AS ru
                               WHERE ru.orden_id = o.id
                           ), 0)
                       ELSE 0
                   END), 0),
                   COALESCE(SUM(CASE
                       WHEN estado_pago = 'Pendiente' THEN
                           costo_mano_obra + COALESCE((
                               SELECT SUM(
                                   ru.cantidad * ru.precio_unitario
                               )
                               FROM repuestos_utilizados AS ru
                               WHERE ru.orden_id = o.id
                           ), 0)
                       ELSE 0
                   END), 0)
               FROM ordenes_servicio AS o"""
        ).fetchone()

        return {
            "total_facturado": float(fila[0]),
            "total_pagado": float(fila[1]),
            "total_pendiente": float(fila[2])
        }

    finally:
        conexion.close()


def obtener_resumen_reportes():
    conexion = conectar()

    try:
        total_ordenes = conexion.execute(
            """SELECT COUNT(*)
               FROM ordenes_servicio"""
        ).fetchone()[0]

        ordenes_activas = conexion.execute(
            """SELECT COUNT(*)
               FROM ordenes_servicio
               WHERE estado != 'Entregado'"""
        ).fetchone()[0]

        ordenes_entregadas = conexion.execute(
            """SELECT COUNT(*)
               FROM ordenes_servicio
               WHERE estado = 'Entregado'"""
        ).fetchone()[0]

        total_repuestos = conexion.execute(
            """SELECT COUNT(*)
               FROM repuestos"""
        ).fetchone()[0]

        repuestos_bajo_stock = conexion.execute(
            """SELECT COUNT(*)
               FROM repuestos
               WHERE cantidad <= stock_minimo"""
        ).fetchone()[0]

        valor_inventario = conexion.execute(
            """SELECT COALESCE(
                   SUM(cantidad * precio),
                   0
               )
               FROM repuestos"""
        ).fetchone()[0]

        return {
            "total_ordenes": total_ordenes,
            "ordenes_activas": ordenes_activas,
            "ordenes_entregadas": ordenes_entregadas,
            "total_repuestos": total_repuestos,
            "repuestos_bajo_stock": repuestos_bajo_stock,
            "valor_inventario": valor_inventario
        }

    finally:
        conexion.close()


def obtener_repuestos_bajo_stock():
    conexion = conectar()

    try:
        return conexion.execute(
            """SELECT
                   nombre,
                   cantidad,
                   stock_minimo,
                   precio
               FROM repuestos
               WHERE cantidad <= stock_minimo
               ORDER BY cantidad ASC, nombre ASC"""
        ).fetchall()

    finally:
        conexion.close()

if __name__ == "__main__":
    crear_tablas()

    conexion = conectar()

    try:
        tablas = conexion.execute(
            """SELECT name
               FROM sqlite_master
               WHERE type = 'table'
               AND name != 'sqlite_sequence'
               ORDER BY name"""
        ).fetchall()

    finally:
        conexion.close()

    print(
        "Base de datos creada en:",
        DB_PATH
    )

    print(
        "Tablas:",
        ", ".join(
            nombre for (nombre,) in tablas
        )
    )