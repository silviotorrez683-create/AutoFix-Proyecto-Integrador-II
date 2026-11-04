import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout
)

from base_datos.database import (
    actualizar_mano_obra,
    agregar_repuesto_a_orden,
    cambiar_estado_pago,
    obtener_detalle_financiero,
    obtener_ordenes_financieras,
    obtener_repuestos_disponibles,
    obtener_resumen_financiero,
    quitar_repuesto_de_orden
)


class FinanzasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.orden_id = None
        self.estado_pago = "Pendiente"
        self.ordenes = []
        self.total_repuestos_actual = 0.0

        self.setWindowTitle("Gestión financiera")
        self.resize(1220, 760)
        self.setMinimumSize(1050, 680)
        self.setStyleSheet(self.estilos())

        principal = QVBoxLayout(self)
        principal.setContentsMargins(20, 18, 20, 18)
        principal.setSpacing(12)

        # Encabezado de la ventana.
        encabezado = QHBoxLayout()

        textos = QVBoxLayout()
        titulo = QLabel("Gestión financiera")
        titulo.setObjectName("titulo")
        subtitulo = QLabel(
            "Busca una orden, registra sus costos y controla el pago."
        )
        subtitulo.setObjectName("textoSecundario")
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        btn_actualizar = QPushButton("Actualizar datos")
        btn_actualizar.setObjectName("botonSecundario")
        btn_actualizar.clicked.connect(self.cargar_todo)

        encabezado.addLayout(textos)
        encabezado.addStretch()
        encabezado.addWidget(btn_actualizar)
        principal.addLayout(encabezado)

        # Resumen general compacto.
        tarjetas = QGridLayout()
        tarjetas.setSpacing(12)

        self.lbl_facturado = self.crear_tarjeta(
            tarjetas, 0, "Total facturado", "#1E3A8A"
        )
        self.lbl_pagado = self.crear_tarjeta(
            tarjetas, 1, "Total pagado", "#166534"
        )
        self.lbl_pendiente = self.crear_tarjeta(
            tarjetas, 2, "Total pendiente", "#854D0E"
        )
        principal.addLayout(tarjetas)

        # Cuerpo dividido en dos paneles.
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(14)

        cuerpo.addWidget(self.crear_panel_ordenes(), 4)
        cuerpo.addWidget(self.crear_panel_detalle(), 7)
        principal.addLayout(cuerpo, 1)

        # Barra inferior.
        inferior = QHBoxLayout()
        self.lbl_estado = QLabel(
            "Selecciona una orden para comenzar."
        )
        self.lbl_estado.setObjectName("textoSecundario")

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("botonSecundario")
        btn_cerrar.clicked.connect(self.accept)

        inferior.addWidget(self.lbl_estado)
        inferior.addStretch()
        inferior.addWidget(btn_cerrar)
        principal.addLayout(inferior)

        self.habilitar_edicion(False)
        self.cargar_todo()

    def crear_panel_ordenes(self):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        paso = QLabel("1. Buscar y seleccionar una orden")
        paso.setObjectName("tituloSeccion")
        layout.addWidget(paso)

        ayuda = QLabel(
            "Puedes buscar por cliente, empresa, placa, vehículo "
            "o número de orden."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("textoSecundario")
        layout.addWidget(ayuda)

        filtros = QHBoxLayout()

        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText(
            "Buscar cliente, placa u orden..."
        )
        self.buscar.textChanged.connect(self.filtrar_ordenes)

        self.filtro_pago = QComboBox()
        self.filtro_pago.addItem(
            "Por cobrar / en proceso", "Activas"
        )
        self.filtro_pago.addItem(
            "Pagados y entregados", "Finalizadas"
        )
        self.filtro_pago.addItem(
            "Todas las órdenes", "Todas"
        )
        self.filtro_pago.currentIndexChanged.connect(
            self.filtrar_ordenes
        )

        filtros.addWidget(self.buscar, 2)
        filtros.addWidget(self.filtro_pago, 1)
        layout.addLayout(filtros)

        self.lbl_resultados = QLabel("0 órdenes encontradas")
        self.lbl_resultados.setObjectName("textoSecundario")
        layout.addWidget(self.lbl_resultados)

        self.tabla_ordenes = QTableWidget(0, 5)
        self.tabla_ordenes.setHorizontalHeaderLabels([
            "OS", "Cliente", "Placa", "Total", "Pago"
        ])
        self.configurar_tabla(self.tabla_ordenes)
        self.tabla_ordenes.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tabla_ordenes.itemSelectionChanged.connect(
            self.seleccionar_orden
        )
        layout.addWidget(self.tabla_ordenes, 1)

        return panel

    def crear_panel_detalle(self):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        paso = QLabel("2. Registrar costos y cobrar")
        paso.setObjectName("tituloSeccion")
        layout.addWidget(paso)

        # Resumen de la orden seleccionada.
        ficha = QFrame()
        ficha.setObjectName("ficha")
        ficha_layout = QVBoxLayout(ficha)
        ficha_layout.setContentsMargins(12, 10, 12, 10)

        self.lbl_orden = QLabel("Ninguna orden seleccionada")
        self.lbl_orden.setObjectName("tituloOrden")

        self.lbl_vehiculo = QLabel(
            "Selecciona una orden del panel izquierdo."
        )
        self.lbl_vehiculo.setObjectName("textoSecundario")
        self.lbl_vehiculo.setWordWrap(True)

        self.lbl_problema = QLabel("")
        self.lbl_problema.setObjectName("textoSecundario")
        self.lbl_problema.setWordWrap(True)

        ficha_layout.addWidget(self.lbl_orden)
        ficha_layout.addWidget(self.lbl_vehiculo)
        ficha_layout.addWidget(self.lbl_problema)
        layout.addWidget(ficha)

        # Paso 2A: mano de obra.
        bloque_mano_obra = QFrame()
        bloque_mano_obra.setObjectName("bloque")
        mano_layout = QHBoxLayout(bloque_mano_obra)
        mano_layout.setContentsMargins(12, 9, 12, 9)

        textos_mano = QVBoxLayout()
        titulo_mano = QLabel("2.1 Mano de obra")
        titulo_mano.setObjectName("subtitulo")
        ayuda_mano = QLabel("Ingresa el costo del trabajo realizado.")
        ayuda_mano.setObjectName("textoSecundario")
        textos_mano.addWidget(titulo_mano)
        textos_mano.addWidget(ayuda_mano)

        self.mano_obra = QDoubleSpinBox()
        self.mano_obra.setRange(0, 100_000_000)
        self.mano_obra.setDecimals(2)
        self.mano_obra.setPrefix("C$ ")
        self.mano_obra.setMinimumWidth(145)
        self.mano_obra.valueChanged.connect(
            self.previsualizar_total
        )

        self.btn_mano_obra = QPushButton("Guardar")
        self.btn_mano_obra.clicked.connect(
            self.guardar_mano_obra
        )

        mano_layout.addLayout(textos_mano, 1)
        mano_layout.addWidget(self.mano_obra)
        mano_layout.addWidget(self.btn_mano_obra)
        layout.addWidget(bloque_mano_obra)

        # Paso 2B: repuestos.
        bloque_repuestos = QFrame()
        bloque_repuestos.setObjectName("bloque")
        repuestos_layout = QVBoxLayout(bloque_repuestos)
        repuestos_layout.setContentsMargins(12, 9, 12, 9)

        titulo_repuesto = QLabel("2.2 Repuestos utilizados")
        titulo_repuesto.setObjectName("subtitulo")
        repuestos_layout.addWidget(titulo_repuesto)

        agregar = QHBoxLayout()
        self.combo_repuestos = QComboBox()
        self.combo_repuestos.setMinimumWidth(260)

        self.cantidad = QSpinBox()
        self.cantidad.setRange(1, 1_000_000)
        self.cantidad.setPrefix("Cantidad: ")
        self.cantidad.setMinimumWidth(120)

        self.btn_agregar = QPushButton("Agregar")
        self.btn_agregar.clicked.connect(self.agregar_repuesto)

        agregar.addWidget(self.combo_repuestos, 1)
        agregar.addWidget(self.cantidad)
        agregar.addWidget(self.btn_agregar)
        repuestos_layout.addLayout(agregar)

        self.tabla_repuestos = QTableWidget(0, 5)
        self.tabla_repuestos.setHorizontalHeaderLabels([
            "ID", "Repuesto", "Cant.", "Precio", "Subtotal"
        ])
        self.configurar_tabla(self.tabla_repuestos)
        self.tabla_repuestos.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tabla_repuestos.setMinimumHeight(145)
        self.tabla_repuestos.itemSelectionChanged.connect(
            self.actualizar_seleccion_repuesto
        )
        repuestos_layout.addWidget(self.tabla_repuestos)

        fila_quitar = QHBoxLayout()
        self.lbl_repuesto_seleccionado = QLabel(
            "Ningún repuesto seleccionado"
        )
        self.lbl_repuesto_seleccionado.setObjectName("textoSecundario")
        fila_quitar.addWidget(self.lbl_repuesto_seleccionado)
        fila_quitar.addStretch()
        self.btn_quitar = QPushButton("Quitar seleccionado")
        self.btn_quitar.setObjectName("botonPeligro")
        self.btn_quitar.clicked.connect(self.quitar_repuesto)
        self.btn_quitar.setEnabled(False)
        fila_quitar.addWidget(self.btn_quitar)
        repuestos_layout.addLayout(fila_quitar)

        layout.addWidget(bloque_repuestos, 1)

        # Paso 3: resumen y pago.
        resumen = QFrame()
        resumen.setObjectName("resumen")
        resumen_layout = QVBoxLayout(resumen)
        resumen_layout.setContentsMargins(14, 10, 14, 10)

        titulo_resumen = QLabel("3. Revisar total y registrar pago")
        titulo_resumen.setObjectName("subtitulo")
        resumen_layout.addWidget(titulo_resumen)

        valores = QHBoxLayout()
        self.lbl_total_mano_obra = QLabel("Mano de obra\nC$ 0.00")
        self.lbl_total_repuestos = QLabel("Repuestos\nC$ 0.00")
        self.lbl_total = QLabel("TOTAL\nC$ 0.00")

        self.lbl_total_mano_obra.setObjectName("valorResumen")
        self.lbl_total_repuestos.setObjectName("valorResumen")
        self.lbl_total.setObjectName("total")

        valores.addWidget(self.lbl_total_mano_obra)
        valores.addWidget(self.lbl_total_repuestos)
        valores.addStretch()
        valores.addWidget(self.lbl_total)
        resumen_layout.addLayout(valores)

        pago = QHBoxLayout()
        self.lbl_pago = QLabel("Estado: sin seleccionar")
        self.lbl_pago.setObjectName("estadoPago")

        self.btn_pago = QPushButton("Marcar como pagado")
        self.btn_pago.setObjectName("botonPago")
        self.btn_pago.clicked.connect(self.cambiar_pago)

        pago.addWidget(self.lbl_pago)
        pago.addStretch()
        pago.addWidget(self.btn_pago)
        resumen_layout.addLayout(pago)

        layout.addWidget(resumen)

        return panel

    def estilos(self):
        return """
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QLabel { color: #E2E8F0; }
            QLabel#titulo {
                color: white;
                font-size: 23px;
                font-weight: bold;
            }
            QLabel#tituloSeccion {
                color: white;
                font-size: 17px;
                font-weight: bold;
            }
            QLabel#tituloOrden {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#subtitulo {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#textoSecundario {
                color: #94A3B8;
                font-size: 12px;
            }
            QLabel#valorResumen {
                color: #CBD5E1;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#total {
                color: #86EFAC;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#estadoPago {
                color: #FDE68A;
                font-weight: bold;
            }
            QFrame#panel {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 9px;
            }
            QFrame#ficha, QFrame#bloque {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 7px;
            }
            QFrame#resumen {
                background-color: #172033;
                border: 1px solid #2563EB;
                border-radius: 8px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #0F172A;
                color: white;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 7px;
            }
            QLineEdit:focus, QComboBox:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #3B82F6;
            }
            QTableWidget {
                background-color: #1E293B;
                color: white;
                gridline-color: #475569;
                border: 1px solid #334155;
                selection-background-color: #2563EB;
                selection-color: white;
            }
            QTableWidget::item:selected {
                background-color: #2563EB;
                color: white;
                border: 1px solid #93C5FD;
            }
            QHeaderView::section {
                background-color: #0B1220;
                color: #CBD5E1;
                font-weight: bold;
                padding: 7px;
                border: none;
            }
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748B;
            }
            QPushButton#botonPeligro { background-color: #B91C1C; }
            QPushButton#botonPago { background-color: #15803D; }
            QPushButton#botonSecundario { background-color: #475569; }
        """

    def crear_tarjeta(self, layout, columna, titulo, color):
        tarjeta = QFrame()
        tarjeta.setFixedHeight(82)
        tarjeta.setStyleSheet(
            f"background-color: {color}; "
            "border-radius: 8px; padding: 4px;"
        )

        contenido = QVBoxLayout(tarjeta)
        contenido.setContentsMargins(12, 8, 12, 8)

        etiqueta = QLabel(titulo)
        etiqueta.setStyleSheet("color: #CBD5E1; font-size: 12px;")

        valor = QLabel("C$ 0.00")
        valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        valor.setStyleSheet(
            "color: white; font-size: 20px; font-weight: bold;"
        )

        contenido.addWidget(etiqueta)
        contenido.addWidget(valor)
        layout.addWidget(tarjeta, 0, columna)
        return valor

    def configurar_tabla(self, tabla):
        tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        tabla.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        tabla.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tabla.verticalHeader().setVisible(False)
        tabla.setAlternatingRowColors(False)

    def cargar_todo(self):
        orden_anterior = self.orden_id

        try:
            resumen = obtener_resumen_financiero()
            self.ordenes = obtener_ordenes_financieras()

            self.lbl_facturado.setText(
                f'C$ {resumen["total_facturado"]:,.2f}'
            )
            self.lbl_pagado.setText(
                f'C$ {resumen["total_pagado"]:,.2f}'
            )
            self.lbl_pendiente.setText(
                f'C$ {resumen["total_pendiente"]:,.2f}'
            )

            self.filtrar_ordenes()

            if orden_anterior is not None:
                encontrada = self.seleccionar_fila_por_id(orden_anterior)
                # Se vuelve a leer el detalle después de refrescar la lista.
                # Esto mantiene sincronizados mano de obra, repuestos y total.
                if encontrada:
                    self.cargar_detalle()
                else:
                    self.limpiar_detalle()

            self.lbl_estado.setText("Datos actualizados correctamente.")

        except sqlite3.Error as error:
            self.mostrar_error("Error financiero", error)

    def filtrar_ordenes(self):
        texto = self.buscar.text().strip().lower()
        vista = self.filtro_pago.currentData()
        filtradas = []

        for orden in self.ordenes:
            contenido = " ".join([
                str(orden[0]),
                str(orden[1]),
                str(orden[2]),
                str(orden[3]),
                str(orden[4])
            ]).lower()

            coincide_texto = not texto or texto in contenido
            esta_finalizada = (
                orden[4] == "Entregado"
                and orden[8] == "Pagado"
            )

            if vista == "Activas":
                coincide_vista = not esta_finalizada
            elif vista == "Finalizadas":
                coincide_vista = esta_finalizada
            else:
                coincide_vista = True

            if coincide_texto and coincide_vista:
                filtradas.append(orden)

        orden_anterior = self.orden_id
        self.tabla_ordenes.blockSignals(True)
        self.tabla_ordenes.clearContents()
        self.tabla_ordenes.setRowCount(len(filtradas))
        self.lbl_resultados.setText(
            f"{len(filtradas)} órdenes encontradas"
        )

        for fila, orden in enumerate(filtradas):
            valores = (
                orden[0],
                orden[1],
                orden[2],
                f"C$ {orden[7]:,.2f}",
                orden[8]
            )

            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setData(Qt.ItemDataRole.UserRole, orden[0])

                if columna in (0, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if columna == 4:
                    color = (
                        Qt.GlobalColor.green
                        if orden[8] == "Pagado"
                        else Qt.GlobalColor.yellow
                    )
                    item.setForeground(color)

                self.tabla_ordenes.setItem(fila, columna, item)

        self.tabla_ordenes.blockSignals(False)

        if orden_anterior is not None:
            encontrada = self.seleccionar_fila_por_id(orden_anterior)
            if not encontrada:
                self.limpiar_detalle()

    def seleccionar_fila_por_id(self, orden_id):
        for fila in range(self.tabla_ordenes.rowCount()):
            item = self.tabla_ordenes.item(fila, 0)
            if item and int(item.text()) == orden_id:
                self.tabla_ordenes.selectRow(fila)
                self.tabla_ordenes.scrollToItem(item)
                return True
        return False

    def limpiar_detalle(self):
        self.orden_id = None
        self.estado_pago = "Pendiente"
        self.total_repuestos_actual = 0.0

        self.lbl_orden.setText("Ninguna orden seleccionada")
        self.lbl_vehiculo.setText(
            "Selecciona una orden del panel izquierdo."
        )
        self.lbl_problema.setText("")

        self.mano_obra.blockSignals(True)
        self.mano_obra.setValue(0)
        self.mano_obra.blockSignals(False)
        self.tabla_repuestos.clearContents()
        self.tabla_repuestos.setRowCount(0)
        self.combo_repuestos.clear()

        self.lbl_total_mano_obra.setText("Mano de obra\nC$ 0.00")
        self.lbl_total_repuestos.setText("Repuestos\nC$ 0.00")
        self.lbl_total.setText("TOTAL\nC$ 0.00")
        self.lbl_pago.setText("Estado: sin seleccionar")
        self.lbl_repuesto_seleccionado.setText(
            "Ningún repuesto seleccionado"
        )
        self.habilitar_edicion(False)

    def seleccionar_orden(self):
        fila = self.tabla_ordenes.currentRow()
        if fila < 0:
            return

        self.orden_id = int(self.tabla_ordenes.item(fila, 0).text())
        self.cargar_detalle()

    def cargar_detalle(self):
        if self.orden_id is None:
            return

        try:
            detalle = obtener_detalle_financiero(self.orden_id)
        except (sqlite3.Error, ValueError) as error:
            self.mostrar_error("Error de la orden", error)
            return

        self.estado_pago = detalle["estado_pago"]

        self.lbl_orden.setText(
            f'Orden N.º {detalle["id"]} | {detalle["cliente"]}'
        )
        self.lbl_vehiculo.setText(
            f'{detalle["vehiculo"]} | Placa: {detalle["placa"]} | '
            f'Estado del servicio: {detalle["estado"]}'
        )
        self.lbl_problema.setText(
            f'Problema reportado: {detalle["problema"]}'
        )

        mano_obra = float(detalle["mano_obra"] or 0)
        total_repuestos = sum(
            float(repuesto[4] or 0)
            for repuesto in detalle["repuestos"]
        )
        total_orden = mano_obra + total_repuestos

        self.total_repuestos_actual = total_repuestos
        self.mano_obra.blockSignals(True)
        self.mano_obra.setValue(mano_obra)
        self.mano_obra.blockSignals(False)
        self.tabla_repuestos.blockSignals(True)
        self.tabla_repuestos.clearContents()
        self.tabla_repuestos.setRowCount(len(detalle["repuestos"]))

        for fila, repuesto in enumerate(detalle["repuestos"]):
            valores = (
                repuesto[0],
                repuesto[1],
                repuesto[2],
                f"C$ {repuesto[3]:,.2f}",
                f"C$ {repuesto[4]:,.2f}"
            )
            for columna, valor in enumerate(valores):
                self.tabla_repuestos.setItem(
                    fila, columna, QTableWidgetItem(str(valor))
                )

        self.tabla_repuestos.blockSignals(False)

        self.lbl_total_mano_obra.setText(
            f'Mano de obra\nC$ {mano_obra:,.2f}'
        )
        self.lbl_total_repuestos.setText(
            f'Repuestos\nC$ {total_repuestos:,.2f}'
        )
        self.lbl_total.setText(
            f'TOTAL\nC$ {total_orden:,.2f}'
        )
        self.lbl_pago.setText(
            f'Estado de pago: {detalle["estado_pago"]}'
        )

        if self.estado_pago == "Pagado":
            self.btn_pago.setText("Reabrir pago")
            self.habilitar_edicion(False)
            self.btn_pago.setEnabled(True)
        else:
            self.btn_pago.setText("Marcar como pagado")
            self.habilitar_edicion(True)

        self.cargar_repuestos_disponibles()
        self.actualizar_seleccion_repuesto()
        self.lbl_estado.setText(
            f'Orden N.º {self.orden_id} seleccionada.'
        )

    def previsualizar_total(self, valor_mano_obra):
        if self.orden_id is None:
            return

        total_previsualizado = (
            float(valor_mano_obra) + self.total_repuestos_actual
        )
        self.lbl_total_mano_obra.setText(
            f"Mano de obra\nC$ {float(valor_mano_obra):,.2f}"
        )
        self.lbl_total.setText(
            f"TOTAL\nC$ {total_previsualizado:,.2f}"
        )
        self.lbl_estado.setText(
            "Vista previa actualizada. Presiona Guardar para confirmar "
            "la mano de obra."
        )

    def actualizar_seleccion_repuesto(self):
        fila = self.tabla_repuestos.currentRow()
        puede_quitar = (
            fila >= 0
            and self.orden_id is not None
            and self.estado_pago != "Pagado"
        )
        self.btn_quitar.setEnabled(puede_quitar)

        if fila < 0:
            if self.tabla_repuestos.rowCount() == 0:
                self.lbl_repuesto_seleccionado.setText(
                    "Sin repuestos: se cobrará solamente la mano de obra."
                )
            else:
                self.lbl_repuesto_seleccionado.setText(
                    "Selecciona una fila para quitar el repuesto."
                )
            return

        nombre = self.tabla_repuestos.item(fila, 1)
        if nombre is not None:
            self.lbl_repuesto_seleccionado.setText(
                f"Seleccionado: {nombre.text()}"
            )

    def seleccionar_repuesto_por_id(self, repuesto_id):
        for fila in range(self.tabla_repuestos.rowCount()):
            item = self.tabla_repuestos.item(fila, 0)
            if item and int(item.text()) == int(repuesto_id):
                self.tabla_repuestos.selectRow(fila)
                self.tabla_repuestos.scrollToItem(item)
                return

    def cargar_repuestos_disponibles(self):
        self.combo_repuestos.clear()

        try:
            repuestos = obtener_repuestos_disponibles()
        except sqlite3.Error as error:
            self.mostrar_error("Error de inventario", error)
            return

        for repuesto in repuestos:
            self.combo_repuestos.addItem(
                f"{repuesto[1]} | Stock: {repuesto[2]} | "
                f"C$ {repuesto[3]:,.2f}",
                repuesto[0]
            )

        disponible = (
            self.combo_repuestos.count() > 0
            and self.estado_pago != "Pagado"
        )
        self.combo_repuestos.setEnabled(disponible)
        self.cantidad.setEnabled(disponible)
        self.btn_agregar.setEnabled(disponible)

    def habilitar_edicion(self, habilitado):
        estado = habilitado and self.orden_id is not None
        self.mano_obra.setEnabled(estado)
        self.btn_mano_obra.setEnabled(estado)
        self.combo_repuestos.setEnabled(estado)
        self.cantidad.setEnabled(estado)
        self.btn_agregar.setEnabled(estado)
        self.btn_quitar.setEnabled(
            estado and self.tabla_repuestos.currentRow() >= 0
        )
        self.btn_pago.setEnabled(self.orden_id is not None)

    def guardar_mano_obra(self):
        if not self.validar_orden_seleccionada():
            return

        try:
            actualizar_mano_obra(
                self.orden_id, self.mano_obra.value()
            )
        except (sqlite3.Error, ValueError) as error:
            self.mostrar_error("No se pudo guardar", error)
            return

        self.cargar_todo()
        self.cargar_detalle()
        QMessageBox.information(
            self,
            "Mano de obra guardada",
            "El costo de mano de obra se guardó correctamente."
        )

    def agregar_repuesto(self):
        if not self.validar_orden_seleccionada():
            return

        repuesto_id = self.combo_repuestos.currentData()
        if repuesto_id is None:
            QMessageBox.warning(
                self,
                "Sin existencias",
                "No hay repuestos disponibles en el inventario."
            )
            return

        try:
            agregar_repuesto_a_orden(
                self.orden_id,
                repuesto_id,
                self.cantidad.value()
            )
        except (sqlite3.Error, ValueError) as error:
            self.mostrar_error("No se pudo agregar", error)
            return

        self.cantidad.setValue(1)
        self.cargar_todo()
        self.cargar_detalle()
        self.seleccionar_repuesto_por_id(repuesto_id)
        QMessageBox.information(
            self,
            "Repuesto agregado",
            "El repuesto se agregó y se descontó del inventario."
        )

    def quitar_repuesto(self):
        if not self.validar_orden_seleccionada():
            return

        fila = self.tabla_repuestos.currentRow()
        if fila < 0:
            QMessageBox.warning(
                self,
                "Selecciona un repuesto",
                "Selecciona un repuesto utilizado en la tabla."
            )
            return

        repuesto_id = int(self.tabla_repuestos.item(fila, 0).text())
        nombre = self.tabla_repuestos.item(fila, 1).text()

        respuesta = QMessageBox.question(
            self,
            "Quitar repuesto",
            f"¿Deseas quitar {nombre} de la orden?\n"
            "La cantidad utilizada regresará al inventario.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        try:
            quitar_repuesto_de_orden(self.orden_id, repuesto_id)
        except (sqlite3.Error, ValueError) as error:
            self.mostrar_error("No se pudo quitar", error)
            return

        self.cargar_todo()
        self.cargar_detalle()
        QMessageBox.information(
            self,
            "Repuesto retirado",
            "El repuesto regresó correctamente al inventario."
        )

    def cambiar_pago(self):
        if not self.validar_orden_seleccionada():
            return

        if self.estado_pago == "Pagado":
            nuevo_estado = "Pendiente"
            mensaje = "¿Deseas reabrir esta orden como pago pendiente?"
        else:
            nuevo_estado = "Pagado"
            mensaje = "¿Confirmas que el cliente pagó esta orden?"

        respuesta = QMessageBox.question(
            self,
            "Confirmar estado de pago",
            mensaje,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        try:
            total = cambiar_estado_pago(self.orden_id, nuevo_estado)
        except (sqlite3.Error, ValueError) as error:
            self.mostrar_error("No se pudo actualizar el pago", error)
            return

        orden_finalizada = False
        ruta_factura = None
        error_factura = None

        if nuevo_estado == "Pagado":
            try:
                detalle = obtener_detalle_financiero(self.orden_id)
                orden_finalizada = detalle["estado"] == "Entregado"
                ruta_factura = self.generar_factura_pdf(detalle)
            except (ImportError, OSError, RuntimeError) as error:
                error_factura = str(error)

        if orden_finalizada:
            # Al completar pago y entrega, la orden desaparece de la vista
            # diaria. Se conserva en "Pagados y entregados" para consulta.
            indice = self.filtro_pago.findData("Activas")
            self.filtro_pago.blockSignals(True)
            self.filtro_pago.setCurrentIndex(indice)
            self.filtro_pago.blockSignals(False)
        elif nuevo_estado == "Pendiente":
            indice = self.filtro_pago.findData("Activas")
            self.filtro_pago.blockSignals(True)
            self.filtro_pago.setCurrentIndex(indice)
            self.filtro_pago.blockSignals(False)

        self.cargar_todo()
        if self.orden_id is not None:
            self.cargar_detalle()

        if ruta_factura is not None:
            QMessageBox.information(
                self,
                "Pago y factura registrados",
                f"La orden quedó como Pagado.\n"
                f"Total: C$ {total:,.2f}\n\n"
                f"Factura creada en:\n{ruta_factura}"
            )
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(ruta_factura))
            )
        elif error_factura is not None:
            QMessageBox.warning(
                self,
                "Pago registrado sin factura",
                f"El pago se guardó correctamente por C$ {total:,.2f}, "
                f"pero no se pudo crear la factura.\n\n{error_factura}"
            )
        else:
            QMessageBox.information(
                self,
                "Pago actualizado",
                f"La orden quedó como {nuevo_estado}.\n"
                f"Total de la orden: C$ {total:,.2f}"
            )

    def generar_factura_pdf(self, detalle):
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle
            )
        except ImportError as error:
            raise ImportError(
                "ReportLab no está instalado. Ejecuta en la terminal: "
                "& .\\.venv313\\Scripts\\python.exe -m pip install reportlab"
            ) from error

        carpeta = Path(__file__).resolve().parents[1] / "facturas"
        carpeta.mkdir(parents=True, exist_ok=True)

        momento = datetime.now()
        nombre = (
            f'factura_OS_{detalle["id"]}_'
            f'{momento.strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        ruta = carpeta / nombre

        documento = SimpleDocTemplate(
            str(ruta),
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm
        )
        estilos = getSampleStyleSheet()
        titulo = ParagraphStyle(
            "TituloAutoFix",
            parent=estilos["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1D4ED8")
        )
        derecha = ParagraphStyle(
            "DerechaAutoFix",
            parent=estilos["Normal"],
            alignment=TA_RIGHT
        )

        elementos = [
            Paragraph("AUTOFIX", titulo),
            Paragraph("Factura de servicio automotriz", estilos["Heading2"]),
            Spacer(1, 0.25 * cm),
            Paragraph(
                f'<b>Factura:</b> OS-{detalle["id"]} &nbsp;&nbsp; '
                f'<b>Fecha:</b> {momento.strftime("%d/%m/%Y %H:%M")}',
                derecha
            ),
            Spacer(1, 0.35 * cm),
            Paragraph(f'<b>Cliente:</b> {detalle["cliente"]}', estilos["Normal"]),
            Paragraph(
                f'<b>Vehículo:</b> {detalle["vehiculo"]} &nbsp;&nbsp; '
                f'<b>Placa:</b> {detalle["placa"]}',
                estilos["Normal"]
            ),
            Paragraph(
                f'<b>Servicio:</b> {detalle["problema"]}',
                estilos["Normal"]
            ),
            Spacer(1, 0.45 * cm)
        ]

        datos = [["Concepto", "Cantidad", "Precio", "Subtotal"]]
        mano_obra = float(detalle["mano_obra"] or 0)
        datos.append([
            "Mano de obra", "1", f"C$ {mano_obra:,.2f}",
            f"C$ {mano_obra:,.2f}"
        ])

        for repuesto in detalle["repuestos"]:
            datos.append([
                repuesto[1],
                str(repuesto[2]),
                f"C$ {float(repuesto[3]):,.2f}",
                f"C$ {float(repuesto[4]):,.2f}"
            ])

        tabla = Table(
            datos,
            colWidths=[8.2 * cm, 2.2 * cm, 3.2 * cm, 3.2 * cm]
        )
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white, colors.HexColor("#F1F5F9")
            ]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7)
        ]))
        elementos.extend([
            tabla,
            Spacer(1, 0.5 * cm),
            Paragraph(
                f'<b>TOTAL PAGADO: C$ {float(detalle["total"]):,.2f}</b>',
                ParagraphStyle(
                    "TotalAutoFix",
                    parent=estilos["Heading2"],
                    alignment=TA_RIGHT,
                    textColor=colors.HexColor("#166534")
                )
            ),
            Spacer(1, 0.4 * cm),
            Paragraph(
                "Estado: PAGADO. Gracias por confiar en AutoFix.",
                estilos["Normal"]
            )
        ])

        documento.build(elementos)
        return ruta

    def validar_orden_seleccionada(self):
        if self.orden_id is not None:
            return True

        QMessageBox.warning(
            self,
            "Selecciona una orden",
            "Primero selecciona una orden del panel izquierdo."
        )
        return False

    def mostrar_error(self, titulo, error):
        QMessageBox.critical(self, titulo, str(error))
