import sqlite3

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout
)

from base_datos.database import (
    actualizar_cantidad_repuesto,
    obtener_repuestos,
    registrar_repuesto
)


class InventarioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Inventario de repuestos")
        self.resize(850, 520)

        layout = QVBoxLayout(self)

        # Tabla de repuestos
        self.tabla = QTableWidget(0, 6)

        self.tabla.setHorizontalHeaderLabels(
            [
                "ID",
                "Nombre",
                "Descripción",
                "Cantidad",
                "Stock mínimo",
                "Precio"
            ]
        )

        self.tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Seleccionar filas completas
        self.tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        # Permitir seleccionar solamente una fila
        self.tabla.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Evitar editar directamente las celdas
        self.tabla.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        layout.addWidget(self.tabla)

        # Formulario
        formulario = QFormLayout()

        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText(
            "Nombre del repuesto"
        )

        self.descripcion = QLineEdit()
        self.descripcion.setPlaceholderText(
            "Descripción del repuesto"
        )

        self.cantidad = QSpinBox()
        self.cantidad.setRange(0, 1_000_000)

        self.stock_minimo = QSpinBox()
        self.stock_minimo.setRange(0, 1_000_000)

        self.precio = QDoubleSpinBox()
        self.precio.setRange(0, 100_000_000)
        self.precio.setDecimals(2)
        self.precio.setPrefix("C$ ")

        formulario.addRow(
            "Nombre:",
            self.nombre
        )
        formulario.addRow(
            "Descripción:",
            self.descripcion
        )
        formulario.addRow(
            "Cantidad:",
            self.cantidad
        )
        formulario.addRow(
            "Stock mínimo:",
            self.stock_minimo
        )
        formulario.addRow(
            "Precio:",
            self.precio
        )

        layout.addLayout(formulario)

        # Botones
        botones = QHBoxLayout()

        btn_guardar = QPushButton(
            "Guardar repuesto"
        )
        btn_actualizar = QPushButton(
            "Actualizar cantidad"
        )
        btn_cerrar = QPushButton("Cerrar")

        botones.addWidget(btn_guardar)
        botones.addWidget(btn_actualizar)
        botones.addWidget(btn_cerrar)

        layout.addLayout(botones)

        btn_guardar.clicked.connect(
            self.guardar_repuesto
        )
        btn_actualizar.clicked.connect(
            self.actualizar_cantidad
        )
        btn_cerrar.clicked.connect(
            self.accept
        )

        self.cargar_repuestos()

    def cargar_repuestos(self):
        try:
            repuestos = obtener_repuestos()

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Error de inventario",
                "No se pudieron cargar los repuestos:\n"
                f"{error}"
            )
            return

        self.tabla.setRowCount(len(repuestos))

        for fila, repuesto in enumerate(repuestos):
            for columna, valor in enumerate(repuesto):
                if valor is None:
                    texto = ""

                elif columna == 5:
                    texto = f"C$ {float(valor):.2f}"

                else:
                    texto = str(valor)

                item = QTableWidgetItem(texto)

                self.tabla.setItem(
                    fila,
                    columna,
                    item
                )

    def guardar_repuesto(self):
        nombre = self.nombre.text().strip()
        descripcion = self.descripcion.text().strip()
        cantidad = self.cantidad.value()
        stock_minimo = self.stock_minimo.value()
        precio = self.precio.value()

        if not nombre:
            QMessageBox.warning(
                self,
                "Falta el nombre",
                "Escribe el nombre del repuesto."
            )
            self.nombre.setFocus()
            return

        if precio <= 0:
            QMessageBox.warning(
                self,
                "Precio no válido",
                "El precio del repuesto debe ser mayor que cero."
            )
            self.precio.setFocus()
            return

        try:
            registrar_repuesto(
                nombre,
                descripcion,
                cantidad,
                stock_minimo,
                precio
            )

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Error al guardar",
                "No se pudo guardar el repuesto:\n"
                f"{error}"
            )
            return

        self.cargar_repuestos()
        self.limpiar_formulario()

        QMessageBox.information(
            self,
            "Repuesto guardado",
            "El repuesto se guardó correctamente."
        )

    def actualizar_cantidad(self):
        fila = self.tabla.currentRow()

        if fila < 0:
            QMessageBox.warning(
                self,
                "Selecciona un repuesto",
                "Primero selecciona una fila de la tabla."
            )
            return

        repuesto_id = int(
            self.tabla.item(fila, 0).text()
        )

        nombre = self.tabla.item(
            fila,
            1
        ).text()

        cantidad_actual = int(
            self.tabla.item(fila, 3).text()
        )

        nueva_cantidad, aceptado = QInputDialog.getInt(
            self,
            "Actualizar cantidad",
            f"Nueva cantidad para {nombre}:",
            cantidad_actual,
            0,
            1_000_000
        )

        if not aceptado:
            return

        try:
            actualizar_cantidad_repuesto(
                repuesto_id,
                nueva_cantidad
            )

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Repuesto no encontrado",
                str(error)
            )
            return

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Error al actualizar",
                "No se pudo actualizar la cantidad:\n"
                f"{error}"
            )
            return

        self.cargar_repuestos()

        QMessageBox.information(
            self,
            "Cantidad actualizada",
            f"{nombre} ahora tiene "
            f"{nueva_cantidad} unidades."
        )

    def limpiar_formulario(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.cantidad.setValue(0)
        self.stock_minimo.setValue(0)
        self.precio.setValue(0)

        self.nombre.setFocus()