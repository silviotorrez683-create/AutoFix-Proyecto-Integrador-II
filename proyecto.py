import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QFrame,
    QGridLayout, QHeaderView, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QStatusBar,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from base_datos.database import (
    ESTADOS, actualizar_estado, crear_tablas,
    obtener_ordenes_financieras,
    obtener_repuestos_bajo_stock, obtener_resumen_financiero,
    obtener_resumen_reportes
)
from formularios.finanzas import FinanzasDialog
from formularios.inventario import InventarioDialog
from formularios.login import LoginDialog
from formularios.recepcion import RecepcionDialog
from formularios.reportes import ReportesDialog


class MainWindow(QMainWindow):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario
        self.ordenes = []

        self.setWindowTitle("AutoFix - Sistema de Gestión Operativa")
        self.resize(1220, 760)
        self.setMinimumSize(1080, 680)
        self.setStyleSheet(self.estilos())

        contenedor = QWidget()
        self.setCentralWidget(contenedor)
        principal = QVBoxLayout(contenedor)
        principal.setContentsMargins(0, 0, 0, 0)
        principal.setSpacing(0)
        principal.addWidget(self.crear_encabezado())

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(16, 16, 16, 14)
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self.crear_barra_lateral())
        cuerpo.addWidget(self.crear_panel_inicio(), 1)
        principal.addLayout(cuerpo, 1)

        barra = QStatusBar()
        barra.setObjectName("barraEstado")
        barra.showMessage("Base de datos local lista | Taller AutoFix")
        self.setStatusBar(barra)

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.actualizar_reloj)
        self.reloj.start(1000)
        self.actualizar_reloj()
        self.actualizar_panel()

    def estilos(self):
        return """
            QMainWindow, QWidget {
                background-color: #0F172A; color: #F8FAFC;
            }
            QLabel { color: #E2E8F0; }
            QLabel#marca {
                color: white; font-size: 20px; font-weight: bold;
            }
            QLabel#usuario, QLabel#secundario {
                color: #94A3B8; font-size: 12px;
            }
            QLabel#saludo {
                color: white; font-size: 22px; font-weight: bold;
            }
            QLabel#tituloSeccion {
                color: white; font-size: 16px; font-weight: bold;
            }
            QLabel#valorKpi {
                color: white; font-size: 24px; font-weight: bold;
            }
            QLabel#tituloKpi { color: #CBD5E1; font-size: 12px; }
            QFrame#encabezado {
                background-color: #1E293B;
                border-bottom: 1px solid #334155;
            }
            QFrame#sidebar, QFrame#panel {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 9px;
            }
            QFrame#alerta {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 7px;
            }
            QPushButton {
                background-color: #2563EB; color: white; border: none;
                border-radius: 5px; padding: 8px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton#menu {
                text-align: left; background-color: #1E293B;
                color: #E2E8F0; padding: 11px;
            }
            QPushButton#menu:hover { background-color: #2563EB; }
            QPushButton#salir { background-color: #B91C1C; }
            QPushButton#secundario { background-color: #475569; }
            QLineEdit, QComboBox {
                background-color: #0F172A; color: white;
                border: 1px solid #475569; border-radius: 5px; padding: 7px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3B82F6;
            }
            QTableWidget {
                background-color: #1E293B; color: white;
                gridline-color: #475569; border: 1px solid #334155;
                border-radius: 6px; selection-background-color: #2563EB;
                selection-color: white;
            }
            QTableWidget::item:selected {
                background-color: #2563EB; color: white;
            }
            QHeaderView::section {
                background-color: #0B1220; color: #CBD5E1;
                font-weight: bold; padding: 8px; border: none;
            }
            QStatusBar#barraEstado {
                background-color: #0B1220; color: #64748B;
                font-size: 12px;
            }
        """

    def crear_encabezado(self):
        marco = QFrame()
        marco.setObjectName("encabezado")
        layout = QHBoxLayout(marco)
        layout.setContentsMargins(18, 11, 18, 11)

        marca = QLabel("AutoFix | Taller Automotriz")
        marca.setObjectName("marca")
        self.lbl_reloj = QLabel()
        self.lbl_reloj.setObjectName("secundario")
        self.lbl_usuario = QLabel(
            f'{self.usuario["nombre_usuario"]} | {self.usuario["rol"]}'
        )
        self.lbl_usuario.setObjectName("usuario")

        actualizar = QPushButton("Actualizar panel")
        actualizar.setObjectName("secundario")
        actualizar.clicked.connect(self.actualizar_panel)
        salir = QPushButton("Cerrar sesión")
        salir.setObjectName("salir")
        salir.clicked.connect(self.cerrar_sesion)

        layout.addWidget(marca)
        layout.addStretch()
        layout.addWidget(self.lbl_reloj)
        layout.addSpacing(14)
        layout.addWidget(self.lbl_usuario)
        layout.addWidget(actualizar)
        layout.addWidget(salir)
        return marco

    def crear_barra_lateral(self):
        marco = QFrame()
        marco.setObjectName("sidebar")
        marco.setFixedWidth(220)
        layout = QVBoxLayout(marco)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(8)

        titulo = QLabel("Módulos del sistema")
        titulo.setObjectName("tituloSeccion")
        ayuda = QLabel("Selecciona una opción para comenzar.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(ayuda)
        layout.addSpacing(5)

        opciones = (
            ("Recepción vehicular", self.abrir_recepcion),
            ("Inventario de repuestos", self.abrir_inventario),
            ("Estado de reparación", self.cambiar_estado),
            ("Gestión financiera", self.abrir_finanzas),
            ("Reportes generales", self.abrir_reportes)
        )
        for texto, funcion in opciones:
            boton = QPushButton(texto)
            boton.setObjectName("menu")
            boton.clicked.connect(funcion)
            layout.addWidget(boton)

        layout.addStretch()
        info = QLabel(
            "AutoFix centraliza órdenes, inventario, cobros y reportes."
        )
        info.setObjectName("secundario")
        info.setWordWrap(True)
        layout.addWidget(info)
        return marco

    def crear_panel_inicio(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        bienvenida = QHBoxLayout()
        textos = QVBoxLayout()
        self.lbl_saludo = QLabel("Panel general de AutoFix")
        self.lbl_saludo.setObjectName("saludo")
        subtitulo = QLabel(
            "Consulta el estado operativo y accede rápidamente a cada módulo."
        )
        subtitulo.setObjectName("secundario")
        textos.addWidget(self.lbl_saludo)
        textos.addWidget(subtitulo)
        bienvenida.addLayout(textos)
        bienvenida.addStretch()
        layout.addLayout(bienvenida)

        tarjetas = QGridLayout()
        tarjetas.setSpacing(10)
        self.lbl_activas = self.crear_tarjeta(
            tarjetas, 0, "Órdenes activas", "#1E3A8A"
        )
        self.lbl_listas = self.crear_tarjeta(
            tarjetas, 1, "Listos para entrega", "#0F766E"
        )
        self.lbl_bajo_stock = self.crear_tarjeta(
            tarjetas, 2, "Repuestos con bajo stock", "#991B1B"
        )
        self.lbl_pendiente = self.crear_tarjeta(
            tarjetas, 3, "Pendiente de cobro", "#854D0E", True
        )
        layout.addLayout(tarjetas)

        contenido = QHBoxLayout()
        contenido.setSpacing(12)
        contenido.addWidget(self.crear_panel_ordenes(), 7)
        contenido.addWidget(self.crear_panel_resumen(), 3)
        layout.addLayout(contenido, 1)
        return panel

    def crear_tarjeta(self, layout, columna, titulo, color, moneda=False):
        tarjeta = QFrame()
        tarjeta.setFixedHeight(92)
        tarjeta.setStyleSheet(
            f"background-color: {color}; border-radius: 8px;"
        )
        contenido = QVBoxLayout(tarjeta)
        contenido.setContentsMargins(14, 10, 14, 10)
        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloKpi")
        valor = QLabel("C$ 0.00" if moneda else "0")
        valor.setObjectName("valorKpi")
        contenido.addWidget(etiqueta)
        contenido.addStretch()
        contenido.addWidget(valor)
        layout.addWidget(tarjeta, 0, columna)
        return valor

    def crear_panel_ordenes(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(9)

        superior = QHBoxLayout()
        titulo = QLabel("Órdenes de servicio")
        titulo.setObjectName("tituloSeccion")
        cambiar = QPushButton("Cambiar estado seleccionado")
        cambiar.clicked.connect(self.cambiar_estado)
        superior.addWidget(titulo)
        superior.addStretch()
        superior.addWidget(cambiar)
        layout.addLayout(superior)

        filtros = QHBoxLayout()
        self.buscar_orden = QLineEdit()
        self.buscar_orden.setPlaceholderText(
            "Buscar por orden, cliente, vehículo o estado..."
        )
        self.buscar_orden.textChanged.connect(self.filtrar_ordenes)
        self.filtro_estado = QComboBox()
        self.filtro_estado.addItem("Todos los estados", "Todos")
        for estado in ESTADOS:
            self.filtro_estado.addItem(estado, estado)
        self.filtro_estado.currentIndexChanged.connect(self.filtrar_ordenes)
        filtros.addWidget(self.buscar_orden, 2)
        filtros.addWidget(self.filtro_estado, 1)
        layout.addLayout(filtros)

        self.lbl_resultados = QLabel("0 órdenes encontradas")
        self.lbl_resultados.setObjectName("secundario")
        layout.addWidget(self.lbl_resultados)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(
            ["N.º OS", "Cliente", "Vehículo", "Estado"]
        )
        self.tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tabla.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tabla.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.tabla, 1)
        return panel

    def crear_panel_resumen(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(10)

        titulo = QLabel("Resumen y alertas")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        self.lbl_resumen_operativo = QLabel()
        self.lbl_resumen_financiero = QLabel()
        self.lbl_alerta_stock = QLabel()
        for etiqueta in (
            self.lbl_resumen_operativo,
            self.lbl_resumen_financiero,
            self.lbl_alerta_stock
        ):
            etiqueta.setWordWrap(True)
            etiqueta.setObjectName("secundario")

        layout.addWidget(self.crear_bloque_alerta(
            "Operación del taller", self.lbl_resumen_operativo
        ))
        layout.addWidget(self.crear_bloque_alerta(
            "Control financiero", self.lbl_resumen_financiero
        ))
        layout.addWidget(self.crear_bloque_alerta(
            "Inventario crítico", self.lbl_alerta_stock
        ))
        layout.addStretch()

        recepcion = QPushButton("Registrar nueva recepción")
        recepcion.clicked.connect(self.abrir_recepcion)
        finanzas = QPushButton("Abrir gestión financiera")
        finanzas.clicked.connect(self.abrir_finanzas)
        layout.addWidget(recepcion)
        layout.addWidget(finanzas)
        return panel

    def crear_bloque_alerta(self, titulo, contenido):
        bloque = QFrame()
        bloque.setObjectName("alerta")
        layout = QVBoxLayout(bloque)
        layout.setContentsMargins(10, 9, 10, 9)
        etiqueta = QLabel(titulo)
        etiqueta.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(etiqueta)
        layout.addWidget(contenido)
        return bloque

    def actualizar_reloj(self):
        ahora = datetime.now()
        self.lbl_reloj.setText(ahora.strftime("%d/%m/%Y  %H:%M:%S"))
        if ahora.hour < 12:
            saludo = "Buenos días"
        elif ahora.hour < 18:
            saludo = "Buenas tardes"
        else:
            saludo = "Buenas noches"
        self.lbl_saludo.setText(
            f'{saludo}, {self.usuario["nombre_usuario"]}'
        )

    def actualizar_panel(self):
        try:
            reporte = obtener_resumen_reportes()
            financiero = obtener_resumen_financiero()
            bajo_stock = obtener_repuestos_bajo_stock()
            ordenes_financieras = obtener_ordenes_financieras()

            # El inicio muestra únicamente órdenes pendientes o en proceso.
            # Una orden pagada y entregada permanece guardada en el historial
            # financiero, pero deja de mostrarse en la operación diaria.
            self.ordenes = [
                (orden[0], orden[1], orden[3], orden[4])
                for orden in ordenes_financieras
                if not (
                    orden[4] == "Entregado"
                    and orden[8] == "Pagado"
                )
            ]
        except Exception as error:
            QMessageBox.critical(
                self, "No se pudo actualizar",
                f"Ocurrió un error al consultar los datos:\n{error}"
            )
            return

        listas = sum(
            1 for orden in self.ordenes
            if orden[3] == "Listo para entrega"
        )
        self.lbl_activas.setText(str(reporte["ordenes_activas"]))
        self.lbl_listas.setText(str(listas))
        self.lbl_bajo_stock.setText(str(reporte["repuestos_bajo_stock"]))
        self.lbl_pendiente.setText(
            f'C$ {financiero["total_pendiente"]:,.2f}'
        )
        self.lbl_resumen_operativo.setText(
            f'Órdenes registradas: {reporte["total_ordenes"]}\n'
            f'Entregadas: {reporte["ordenes_entregadas"]}\n'
            f'Listas para entrega: {listas}'
        )
        self.lbl_resumen_financiero.setText(
            f'Total facturado: C$ {financiero["total_facturado"]:,.2f}\n'
            f'Total pagado: C$ {financiero["total_pagado"]:,.2f}\n'
            f'Pendiente: C$ {financiero["total_pendiente"]:,.2f}'
        )

        if bajo_stock:
            lineas = [
                f"• {fila[0]}: {fila[1]} disponibles (mín. {fila[2]})"
                for fila in bajo_stock[:3]
            ]
            if len(bajo_stock) > 3:
                lineas.append(f"• Y {len(bajo_stock) - 3} repuestos más")
            self.lbl_alerta_stock.setText("\n".join(lineas))
            self.lbl_alerta_stock.setStyleSheet("color: #FCA5A5;")
        else:
            self.lbl_alerta_stock.setText(
                "El inventario no presenta alertas de bajo stock."
            )
            self.lbl_alerta_stock.setStyleSheet("color: #86EFAC;")

        self.filtrar_ordenes()
        self.statusBar().showMessage(
            "Panel actualizado correctamente | Taller AutoFix", 4000
        )

    def filtrar_ordenes(self):
        texto = self.buscar_orden.text().strip().lower()
        estado = self.filtro_estado.currentData()
        filtradas = []
        for orden in self.ordenes:
            contenido = " ".join(str(valor) for valor in orden).lower()
            if (not texto or texto in contenido) and (
                estado == "Todos" or orden[3] == estado
            ):
                filtradas.append(orden)

        self.tabla.clearContents()
        self.tabla.setRowCount(len(filtradas))
        self.lbl_resultados.setText(f"{len(filtradas)} órdenes encontradas")
        colores = {
            "En recepción": "#93C5FD",
            "En diagnóstico": "#C4B5FD",
            "En espera de repuestos": "#FDE68A",
            "En reparación": "#FDBA74",
            "Listo para entrega": "#5EEAD4",
            "Entregado": "#86EFAC"
        }
        for fila, orden in enumerate(filtradas):
            for columna, valor in enumerate(orden):
                item = QTableWidgetItem(str(valor))
                if columna in (0, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if columna == 3:
                    item.setForeground(
                        QColor(colores.get(str(valor), "#FFFFFF"))
                    )
                self.tabla.setItem(fila, columna, item)

    def abrir_recepcion(self):
        RecepcionDialog(self).exec()
        self.actualizar_panel()

    def abrir_inventario(self):
        InventarioDialog(self).exec()
        self.actualizar_panel()

    def abrir_finanzas(self):
        FinanzasDialog(self).exec()
        self.actualizar_panel()

    def abrir_reportes(self):
        ReportesDialog(self).exec()
        self.actualizar_panel()

    def cambiar_estado(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(
                self, "Selecciona una orden",
                "Primero selecciona una fila de la tabla de órdenes."
            )
            return

        orden_id = int(self.tabla.item(fila, 0).text())
        estado_actual = self.tabla.item(fila, 3).text()
        indice = ESTADOS.index(estado_actual) if estado_actual in ESTADOS else 0
        nuevo_estado, aceptado = QInputDialog.getItem(
            self, "Estado de reparación",
            f"Orden N.º {orden_id}\nSelecciona el nuevo estado:",
            ESTADOS, indice, False
        )
        if not aceptado or nuevo_estado == estado_actual:
            return
        try:
            actualizar_estado(orden_id, nuevo_estado)
        except ValueError as error:
            QMessageBox.warning(
                self, "No se pudo actualizar", str(error)
            )
            return
        self.actualizar_panel()
        QMessageBox.information(
            self, "Estado actualizado",
            f"La orden N.º {orden_id} ahora está: {nuevo_estado}."
        )

    def cerrar_sesion(self):
        respuesta = QMessageBox.question(
            self, "Cerrar sesión", "¿Deseas cerrar la sesión actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.hide()
        login = LoginDialog()
        if login.exec() == QDialog.DialogCode.Accepted:
            self.usuario = login.usuario_autenticado
            self.lbl_usuario.setText(
                f'{self.usuario["nombre_usuario"]} | {self.usuario["rol"]}'
            )
            self.actualizar_reloj()
            self.actualizar_panel()
            self.show()
        else:
            self.close()


if __name__ == "__main__":
    crear_tablas()
    app = QApplication(sys.argv)
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    ventana = MainWindow(login.usuario_autenticado)
    ventana.show()
    sys.exit(app.exec())