import csv
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout
)

from base_datos.database import (
    DB_PATH,
    obtener_repuestos_bajo_stock,
    obtener_resumen_financiero,
    obtener_resumen_reportes
)


# ============================================================
# HILO 1: GENERACIÓN DEL REPORTE
# ============================================================
# Este trabajador consulta la base de datos en segundo plano.
# Los resultados se envían mediante señales para evitar que la
# interfaz gráfica se congele mientras se genera el reporte.
class ReporteWorker(QObject):
    terminado = Signal(dict, list)
    error = Signal(str)

    @Slot()
    def ejecutar(self):
        try:
            resumen = obtener_resumen_reportes()
            repuestos = obtener_repuestos_bajo_stock()

            self.terminado.emit(resumen, repuestos)

        except Exception as error:
            self.error.emit(str(error))


# ============================================================
# HILO 2: EXPORTACIÓN DEL REPORTE A CSV
# ============================================================
# Este trabajador crea el archivo CSV en un hilo secundario.
# La señal "progreso" permite mostrar visualmente el avance del
# proceso mediante una barra de progreso.
class ExportarCSVWorker(QObject):
    progreso = Signal(int)
    terminado = Signal(str)
    error = Signal(str)

    def __init__(self, ruta):
        super().__init__()
        self.ruta = ruta

    @Slot()
    def ejecutar(self):
        try:
            self.progreso.emit(10)

            resumen = obtener_resumen_reportes()

            self.progreso.emit(35)

            repuestos = obtener_repuestos_bajo_stock()

            self.progreso.emit(55)

            with open(
                self.ruta,
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as archivo:

                escritor = csv.writer(archivo)

                escritor.writerow([
                    "REPORTE GENERAL DE AUTOFIX"
                ])

                escritor.writerow([])

                escritor.writerow([
                    "Indicador",
                    "Valor"
                ])

                escritor.writerow([
                    "Órdenes registradas",
                    resumen["total_ordenes"]
                ])

                escritor.writerow([
                    "Órdenes activas",
                    resumen["ordenes_activas"]
                ])

                escritor.writerow([
                    "Órdenes entregadas",
                    resumen["ordenes_entregadas"]
                ])

                escritor.writerow([
                    "Repuestos registrados",
                    resumen["total_repuestos"]
                ])

                escritor.writerow([
                    "Repuestos con bajo stock",
                    resumen["repuestos_bajo_stock"]
                ])

                escritor.writerow([
                    "Valor del inventario",
                    f'C$ {resumen["valor_inventario"]:,.2f}'
                ])

                self.progreso.emit(75)

                escritor.writerow([])

                escritor.writerow([
                    "REPUESTOS QUE NECESITAN REPOSICIÓN"
                ])

                escritor.writerow([
                    "Repuesto",
                    "Cantidad actual",
                    "Nivel de alerta",
                    "Precio unitario"
                ])

                for repuesto in repuestos:
                    escritor.writerow([
                        repuesto[0],
                        repuesto[1],
                        repuesto[2],
                        f"C$ {repuesto[3]:,.2f}"
                    ])

            self.progreso.emit(100)
            self.terminado.emit(self.ruta)

        except Exception as error:
            self.error.emit(str(error))


# ============================================================
# HILO 3: EXPORTACIÓN DEL REPORTE A PDF CON REPORTLAB
# ============================================================
# Este trabajador genera el PDF en segundo plano. El uso de
# QThread evita bloquear la interfaz mientras ReportLab crea
# las tablas, aplica estilos y escribe el documento en disco.
class ExportarPDFWorker(QObject):
    progreso = Signal(int)
    terminado = Signal(str)
    error = Signal(str)

    def __init__(self, ruta):
        super().__init__()
        self.ruta = ruta

    @Slot()
    def ejecutar(self):
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import (
                ParagraphStyle,
                getSampleStyleSheet
            )
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table
            )

            self.progreso.emit(10)
            resumen = obtener_resumen_reportes()
            financiero = obtener_resumen_financiero()
            repuestos = obtener_repuestos_bajo_stock()

            self.progreso.emit(35)

            documento = SimpleDocTemplate(
                self.ruta,
                pagesize=A4,
                rightMargin=1.5 * cm,
                leftMargin=1.5 * cm,
                topMargin=1.4 * cm,
                bottomMargin=1.4 * cm
            )

            estilos = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle(
                "TituloAutoFix",
                parent=estilos["Title"],
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1D4ED8")
            )
            estilo_derecha = ParagraphStyle(
                "DerechaAutoFix",
                parent=estilos["Normal"],
                alignment=TA_RIGHT
            )

            elementos = [
                Paragraph("AUTOFIX", estilo_titulo),
                Paragraph(
                    "Reporte general operativo y financiero",
                    estilos["Heading2"]
                ),
                Paragraph(
                    "Generado: "
                    + datetime.now().strftime("%d/%m/%Y %H:%M"),
                    estilo_derecha
                ),
                Spacer(1, 0.4 * cm),
                Paragraph("Resumen operativo", estilos["Heading2"])
            ]

            datos_operativos = [
                ["Indicador", "Valor"],
                ["Órdenes registradas", resumen["total_ordenes"]],
                ["Órdenes activas", resumen["ordenes_activas"]],
                ["Órdenes entregadas", resumen["ordenes_entregadas"]],
                ["Repuestos registrados", resumen["total_repuestos"]],
                [
                    "Repuestos con bajo stock",
                    resumen["repuestos_bajo_stock"]
                ],
                [
                    "Valor del inventario",
                    f'C$ {resumen["valor_inventario"]:,.2f}'
                ]
            ]
            tabla_operativa = Table(
                datos_operativos,
                colWidths=[12.5 * cm, 5 * cm]
            )
            self.aplicar_estilo_tabla(tabla_operativa, colors)
            elementos.extend([
                tabla_operativa,
                Spacer(1, 0.45 * cm),
                Paragraph("Resumen financiero", estilos["Heading2"])
            ])

            datos_financieros = [
                ["Indicador", "Monto"],
                [
                    "Total facturado",
                    f'C$ {financiero["total_facturado"]:,.2f}'
                ],
                [
                    "Total pagado",
                    f'C$ {financiero["total_pagado"]:,.2f}'
                ],
                [
                    "Total pendiente",
                    f'C$ {financiero["total_pendiente"]:,.2f}'
                ]
            ]
            tabla_financiera = Table(
                datos_financieros,
                colWidths=[12.5 * cm, 5 * cm]
            )
            self.aplicar_estilo_tabla(tabla_financiera, colors)
            elementos.extend([
                tabla_financiera,
                Spacer(1, 0.45 * cm),
                Paragraph(
                    "Repuestos que necesitan reposición",
                    estilos["Heading2"]
                )
            ])

            self.progreso.emit(65)

            datos_repuestos = [[
                "Repuesto", "Cantidad", "Nivel de alerta", "Precio"
            ]]
            if repuestos:
                for repuesto in repuestos:
                    datos_repuestos.append([
                        repuesto[0],
                        repuesto[1],
                        repuesto[2],
                        f"C$ {repuesto[3]:,.2f}"
                    ])
            else:
                datos_repuestos.append([
                    "Sin repuestos con bajo stock", "-", "-", "-"
                ])

            tabla_repuestos = Table(
                datos_repuestos,
                colWidths=[8 * cm, 3 * cm, 3.5 * cm, 3 * cm],
                repeatRows=1
            )
            self.aplicar_estilo_tabla(tabla_repuestos, colors)
            elementos.extend([
                tabla_repuestos,
                Spacer(1, 0.45 * cm),
                Paragraph(
                    "Documento generado por el sistema AutoFix.",
                    estilos["Normal"]
                )
            ])

            self.progreso.emit(85)
            documento.build(elementos)
            self.progreso.emit(100)
            self.terminado.emit(self.ruta)

        except ImportError as error:
            self.error.emit(
                "ReportLab no está instalado. Ejecuta: "
                "& .\\.venv313\\Scripts\\python.exe "
                "-m pip install reportlab"
            )
        except Exception as error:
            self.error.emit(str(error))

    @staticmethod
    def aplicar_estilo_tabla(tabla, colors):
        # Importación local necesaria porque este método se ejecuta
        # fuera del alcance de las importaciones de ejecutar().
        from reportlab.platypus import TableStyle

        tabla.setStyle(TableStyle([
            (
                "BACKGROUND", (0, 0), (-1, 0),
                colors.HexColor("#1E3A8A")
            ),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            (
                "GRID", (0, 0), (-1, -1), 0.5,
                colors.HexColor("#94A3B8")
            ),
            (
                "ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#F1F5F9")]
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
        ]))


# ============================================================
# HILO 4: RESPALDO DE LA BASE DE DATOS
# ============================================================
# Este trabajador copia la base de datos SQLite en segundo plano.
# La utilización del hilo permite mantener disponible la interfaz
# aunque la base de datos aumente considerablemente de tamaño.
class RespaldoWorker(QObject):
    progreso = Signal(int)
    terminado = Signal(str)
    error = Signal(str)

    def __init__(self, ruta_destino):
        super().__init__()
        self.ruta_destino = ruta_destino

    @Slot()
    def ejecutar(self):
        try:
            self.progreso.emit(15)

            if not DB_PATH.exists():
                raise FileNotFoundError(
                    "No se encontró la base de datos autofix.db."
                )

            self.progreso.emit(45)

            shutil.copy2(
                DB_PATH,
                self.ruta_destino
            )

            self.progreso.emit(100)
            self.terminado.emit(self.ruta_destino)

        except Exception as error:
            self.error.emit(str(error))


# ============================================================
# HILO PRINCIPAL: VENTANA DE REPORTES
# ============================================================
# Esta clase se ejecuta en el hilo principal de la aplicación.
# Es la única encargada de modificar los componentes visuales.
# Los trabajadores secundarios se comunican con ella mediante
# señales, respetando las reglas de seguridad de PySide6.
class ReportesDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Referencias utilizadas para controlar el hilo activo.
        self.hilo = None
        self.worker = None

        self.setWindowTitle("Reportes generales")
        self.resize(930, 660)

        self.setStyleSheet(
            "background-color: #121826;"
            "color: #F8FAFC;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        titulo = QLabel("Resumen operativo de AutoFix")
        titulo.setStyleSheet(
            "font-size: 22px;"
            "font-weight: bold;"
        )

        layout.addWidget(titulo)

        # ----------------------------------------------------
        # TARJETAS DEL RESUMEN GENERAL
        # ----------------------------------------------------
        tarjetas = QGridLayout()

        self.lbl_total_ordenes = self.crear_tarjeta(
            tarjetas,
            0,
            0,
            "Órdenes registradas",
            "#1E3A8A"
        )

        self.lbl_activas = self.crear_tarjeta(
            tarjetas,
            0,
            1,
            "Órdenes activas",
            "#854D0E"
        )

        self.lbl_entregadas = self.crear_tarjeta(
            tarjetas,
            0,
            2,
            "Órdenes entregadas",
            "#166534"
        )

        self.lbl_total_repuestos = self.crear_tarjeta(
            tarjetas,
            1,
            0,
            "Repuestos registrados",
            "#334155"
        )

        self.lbl_bajo_stock = self.crear_tarjeta(
            tarjetas,
            1,
            1,
            "Repuestos con bajo stock",
            "#7F1D1D"
        )

        self.lbl_valor_inventario = self.crear_tarjeta(
            tarjetas,
            1,
            2,
            "Valor del inventario",
            "#581C87"
        )

        layout.addLayout(tarjetas)

        # ----------------------------------------------------
        # TABLA DE REPUESTOS CON BAJO STOCK
        # ----------------------------------------------------
        subtitulo = QLabel(
            "Repuestos que necesitan reposición"
        )

        subtitulo.setStyleSheet(
            "font-size: 16px;"
            "font-weight: bold;"
        )

        layout.addWidget(subtitulo)

        self.tabla = QTableWidget(0, 4)

        self.tabla.setHorizontalHeaderLabels([
            "Repuesto",
            "Cantidad actual",
            "Nivel de alerta",
            "Precio unitario"
        ])

        self.tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.tabla.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.tabla.setStyleSheet(
            "QTableWidget {"
            "background-color: #1E293B;"
            "color: white;"
            "gridline-color: #475569;"
            "border: none;"
            "}"

            "QHeaderView::section {"
            "background-color: #0F172A;"
            "color: #CBD5E1;"
            "font-weight: bold;"
            "padding: 7px;"
            "border: none;"
            "}"
        )

        layout.addWidget(self.tabla)

        # ----------------------------------------------------
        # BARRA DE PROGRESO
        # ----------------------------------------------------
        # Esta barra permite que el jurado observe visualmente
        # el avance de los procesos ejecutados con QThread.
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)
        self.barra_progreso.setTextVisible(True)

        self.barra_progreso.setStyleSheet(
            "QProgressBar {"
            "background-color: #1E293B;"
            "color: white;"
            "border: 1px solid #475569;"
            "border-radius: 5px;"
            "text-align: center;"
            "height: 20px;"
            "}"

            "QProgressBar::chunk {"
            "background-color: #2563EB;"
            "border-radius: 4px;"
            "}"
        )

        layout.addWidget(self.barra_progreso)

        # ----------------------------------------------------
        # MENSAJE DEL ESTADO DEL HILO
        # ----------------------------------------------------
        self.lbl_estado = QLabel(
            "Preparando reporte..."
        )

        self.lbl_estado.setStyleSheet(
            "color: #94A3B8;"
            "font-size: 12px;"
        )

        layout.addWidget(self.lbl_estado)

        # ----------------------------------------------------
        # BOTONES
        # ----------------------------------------------------
        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_actualizar = QPushButton(
            "Actualizar reporte"
        )

        self.btn_exportar = QPushButton(
            "Exportar CSV"
        )

        self.btn_pdf = QPushButton(
            "Generar PDF"
        )

        self.btn_respaldo = QPushButton(
            "Crear respaldo"
        )

        self.btn_cerrar = QPushButton(
            "Cerrar"
        )

        self.btn_actualizar.clicked.connect(
            self.cargar_datos
        )

        self.btn_exportar.clicked.connect(
            self.exportar_csv
        )

        self.btn_pdf.clicked.connect(
            self.exportar_pdf
        )

        self.btn_respaldo.clicked.connect(
            self.crear_respaldo
        )

        self.btn_cerrar.clicked.connect(
            self.cerrar_ventana
        )

        for boton in (
            self.btn_actualizar,
            self.btn_exportar,
            self.btn_pdf,
            self.btn_respaldo
        ):
            boton.setStyleSheet(
                "background-color: #2563EB;"
                "color: white;"
                "padding: 8px 14px;"
                "border: none;"
                "border-radius: 5px;"
                "font-weight: bold;"
            )

        self.btn_cerrar.setStyleSheet(
            "background-color: #475569;"
            "color: white;"
            "padding: 8px 14px;"
            "border: none;"
            "border-radius: 5px;"
        )

        botones.addWidget(self.btn_actualizar)
        botones.addWidget(self.btn_exportar)
        botones.addWidget(self.btn_pdf)
        botones.addWidget(self.btn_respaldo)
        botones.addWidget(self.btn_cerrar)

        layout.addLayout(botones)

        # Genera el reporte al abrir la ventana.
        self.cargar_datos()

    def crear_tarjeta(
        self,
        layout,
        fila,
        columna,
        titulo,
        color
    ):
        tarjeta = QFrame()

        tarjeta.setStyleSheet(
            f"background-color: {color};"
            "border-radius: 8px;"
            "padding: 10px;"
        )

        contenido = QVBoxLayout(tarjeta)

        etiqueta = QLabel(titulo)

        etiqueta.setStyleSheet(
            "color: #CBD5E1;"
            "font-size: 12px;"
        )

        valor = QLabel("0")
        valor.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        valor.setStyleSheet(
            "color: white;"
            "font-size: 24px;"
            "font-weight: bold;"
        )

        contenido.addWidget(etiqueta)
        contenido.addWidget(valor)

        layout.addWidget(
            tarjeta,
            fila,
            columna
        )

        return valor

    def hay_hilo_activo(self):
        return (
            self.hilo is not None
            and self.hilo.isRunning()
        )

    def cambiar_botones(self, habilitados):
        self.btn_actualizar.setEnabled(habilitados)
        self.btn_exportar.setEnabled(habilitados)
        self.btn_pdf.setEnabled(habilitados)
        self.btn_respaldo.setEnabled(habilitados)

    # ========================================================
    # INICIO DEL HILO 1: GENERACIÓN DEL REPORTE
    # ========================================================
    def cargar_datos(self):
        if self.hay_hilo_activo():
            return

        self.cambiar_botones(False)

        # Rango 0, 0 muestra una barra en movimiento porque una
        # consulta no permite calcular un porcentaje exacto.
        self.barra_progreso.setRange(0, 0)

        self.lbl_estado.setText(
            "Generando reporte mediante QThread..."
        )

        # Se crea el hilo secundario.
        self.hilo = QThread(self)

        # Se crea el trabajador que realizará la consulta.
        self.worker = ReporteWorker()

        # El trabajador se traslada al hilo secundario.
        self.worker.moveToThread(self.hilo)

        # Cuando el hilo inicia, ejecuta el trabajador.
        self.hilo.started.connect(
            self.worker.ejecutar
        )

        # Las señales devuelven los resultados al hilo principal.
        self.worker.terminado.connect(
            self.mostrar_datos
        )

        self.worker.error.connect(
            self.mostrar_error
        )

        # El hilo se cierra al terminar o producirse un error.
        self.worker.terminado.connect(
            self.hilo.quit
        )

        self.worker.error.connect(
            self.hilo.quit
        )

        # Se libera correctamente la memoria utilizada.
        self.worker.terminado.connect(
            self.worker.deleteLater
        )

        self.worker.error.connect(
            self.worker.deleteLater
        )

        self.hilo.finished.connect(
            self.finalizar_hilo
        )

        self.hilo.finished.connect(
            self.hilo.deleteLater
        )

        # Se inicia la ejecución del hilo.
        self.hilo.start()

    @Slot(dict, list)
    def mostrar_datos(self, resumen, repuestos):
        self.lbl_total_ordenes.setText(
            str(resumen["total_ordenes"])
        )

        self.lbl_activas.setText(
            str(resumen["ordenes_activas"])
        )

        self.lbl_entregadas.setText(
            str(resumen["ordenes_entregadas"])
        )

        self.lbl_total_repuestos.setText(
            str(resumen["total_repuestos"])
        )

        self.lbl_bajo_stock.setText(
            str(resumen["repuestos_bajo_stock"])
        )

        self.lbl_valor_inventario.setText(
            f'C$ {resumen["valor_inventario"]:,.2f}'
        )

        self.tabla.setRowCount(
            len(repuestos)
        )

        for fila, repuesto in enumerate(repuestos):
            valores = (
                repuesto[0],
                repuesto[1],
                repuesto[2],
                f"C$ {repuesto[3]:,.2f}"
            )

            for columna, valor in enumerate(valores):
                self.tabla.setItem(
                    fila,
                    columna,
                    QTableWidgetItem(str(valor))
                )

        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(100)

        self.lbl_estado.setText(
            "Reporte generado mediante QThread correctamente."
        )

    # ========================================================
    # INICIO DEL HILO 2: EXPORTACIÓN DEL REPORTE A CSV
    # ========================================================
    def exportar_csv(self):
        if self.hay_hilo_activo():
            return

        nombre = (
            "reporte_autofix_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".csv"
        )

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte CSV",
            nombre,
            "Archivo CSV (*.csv)"
        )

        if not ruta:
            return

        self.cambiar_botones(False)
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)

        self.lbl_estado.setText(
            "Exportando CSV mediante QThread..."
        )

        # Creación del segundo hilo secundario.
        self.hilo = QThread(self)

        # El trabajador recibe la ruta seleccionada.
        self.worker = ExportarCSVWorker(ruta)

        self.worker.moveToThread(self.hilo)

        self.hilo.started.connect(
            self.worker.ejecutar
        )

        # Actualiza visualmente la barra de progreso.
        self.worker.progreso.connect(
            self.barra_progreso.setValue
        )

        self.worker.terminado.connect(
            self.csv_terminado
        )

        self.worker.error.connect(
            self.mostrar_error
        )

        self.worker.terminado.connect(
            self.hilo.quit
        )

        self.worker.error.connect(
            self.hilo.quit
        )

        self.worker.terminado.connect(
            self.worker.deleteLater
        )

        self.worker.error.connect(
            self.worker.deleteLater
        )

        self.hilo.finished.connect(
            self.finalizar_hilo
        )

        self.hilo.finished.connect(
            self.hilo.deleteLater
        )

        self.hilo.start()

    @Slot(str)
    def csv_terminado(self, ruta):
        self.lbl_estado.setText(
            "CSV exportado mediante QThread correctamente."
        )

        QMessageBox.information(
            self,
            "Exportación completada",
            f"El reporte se guardó en:\n{ruta}"
        )

    # ========================================================
    # INICIO DEL HILO 3: REPORTE GENERAL PDF CON REPORTLAB
    # ========================================================
    def exportar_pdf(self):
        if self.hay_hilo_activo():
            return

        nombre = (
            "reporte_general_autofix_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".pdf"
        )

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte general PDF",
            nombre,
            "Documento PDF (*.pdf)"
        )

        if not ruta:
            return

        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"

        self.cambiar_botones(False)
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)
        self.lbl_estado.setText(
            "Generando PDF con ReportLab mediante QThread..."
        )

        # HILO VISIBLE PARA EL JURADO:
        # ReportLab trabaja dentro de este hilo secundario y
        # comunica su progreso sin bloquear la ventana.
        self.hilo = QThread(self)
        self.worker = ExportarPDFWorker(ruta)
        self.worker.moveToThread(self.hilo)

        self.hilo.started.connect(self.worker.ejecutar)
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.terminado.connect(self.pdf_terminado)
        self.worker.error.connect(self.mostrar_error)
        self.worker.terminado.connect(self.hilo.quit)
        self.worker.error.connect(self.hilo.quit)
        self.worker.terminado.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.hilo.finished.connect(self.finalizar_hilo)
        self.hilo.finished.connect(self.hilo.deleteLater)
        self.hilo.start()

    @Slot(str)
    def pdf_terminado(self, ruta):
        self.lbl_estado.setText(
            "PDF generado con ReportLab y QThread correctamente."
        )
        QMessageBox.information(
            self,
            "PDF completado",
            f"El reporte general se guardó en:\n{ruta}"
        )
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(ruta)
        )

    # ========================================================
    # INICIO DEL HILO 4: RESPALDO DE LA BASE DE DATOS
    # ========================================================
    def crear_respaldo(self):
        if self.hay_hilo_activo():
            return

        carpeta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta para el respaldo"
        )

        if not carpeta:
            return

        nombre = (
            "autofix_respaldo_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".db"
        )

        ruta_destino = str(
            Path(carpeta) / nombre
        )

        self.cambiar_botones(False)
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)

        self.lbl_estado.setText(
            "Creando respaldo mediante QThread..."
        )

        # Creación del tercer hilo secundario.
        self.hilo = QThread(self)

        # El trabajador recibe la ruta del respaldo.
        self.worker = RespaldoWorker(
            ruta_destino
        )

        self.worker.moveToThread(self.hilo)

        self.hilo.started.connect(
            self.worker.ejecutar
        )

        self.worker.progreso.connect(
            self.barra_progreso.setValue
        )

        self.worker.terminado.connect(
            self.respaldo_terminado
        )

        self.worker.error.connect(
            self.mostrar_error
        )

        self.worker.terminado.connect(
            self.hilo.quit
        )

        self.worker.error.connect(
            self.hilo.quit
        )

        self.worker.terminado.connect(
            self.worker.deleteLater
        )

        self.worker.error.connect(
            self.worker.deleteLater
        )

        self.hilo.finished.connect(
            self.finalizar_hilo
        )

        self.hilo.finished.connect(
            self.hilo.deleteLater
        )

        self.hilo.start()

    @Slot(str)
    def respaldo_terminado(self, ruta):
        self.lbl_estado.setText(
            "Respaldo creado mediante QThread correctamente."
        )

        QMessageBox.information(
            self,
            "Respaldo completado",
            f"La base de datos se respaldó en:\n{ruta}"
        )

    # ========================================================
    # CONTROL DE ERRORES DE LOS HILOS
    # ========================================================
    @Slot(str)
    def mostrar_error(self, mensaje):
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)

        self.lbl_estado.setText(
            "El proceso secundario presentó un error."
        )

        QMessageBox.critical(
            self,
            "Error del proceso",
            mensaje
        )

    # Este método se ejecuta cuando cualquiera de los hilos
    # termina. Reactiva los botones y elimina las referencias.
    @Slot()
    def finalizar_hilo(self):
        self.cambiar_botones(True)
        self.worker = None
        self.hilo = None

    def cerrar_ventana(self):
        # Impide cerrar la ventana mientras un hilo está activo.
        if self.hay_hilo_activo():
            QMessageBox.information(
                self,
                "Proceso en ejecución",
                "Espera a que finalice el hilo secundario."
            )
            return

        self.accept()