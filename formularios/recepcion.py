import sqlite3
from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout
)

from base_datos.database import (
    buscar_clientes,
    obtener_vehiculos_cliente,
    registrar_recepcion
)


class RecepcionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.cliente_id = None
        self.vehiculo_id = None

        self.setWindowTitle("Recepción vehicular")
        self.resize(650, 720)
        self.setMinimumSize(590, 650)
        self.setStyleSheet(self.estilos())

        principal = QVBoxLayout(self)
        principal.setContentsMargins(20, 18, 20, 18)
        principal.setSpacing(12)

        titulo = QLabel("Recepción vehicular")
        titulo.setObjectName("titulo")
        ayuda = QLabel(
            "Busca un cliente registrado o selecciona la opción de cliente "
            "nuevo. Un mismo cliente puede tener varios vehículos."
        )
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        principal.addWidget(titulo)
        principal.addWidget(ayuda)

        principal.addWidget(self.crear_busqueda_cliente())
        principal.addWidget(self.crear_formulario_cliente())
        principal.addWidget(self.crear_formulario_vehiculo())

        self.lbl_estado = QLabel(
            "Modo actual: registrar un cliente y vehículo nuevos."
        )
        self.lbl_estado.setObjectName("estado")
        self.lbl_estado.setWordWrap(True)
        principal.addWidget(self.lbl_estado)

        botones = QHBoxLayout()
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("secundarioBoton")
        cancelar.clicked.connect(self.reject)
        guardar = QPushButton("Guardar recepción")
        guardar.clicked.connect(self.guardar)
        botones.addStretch()
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        principal.addLayout(botones)

    def estilos(self):
        return """
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QLabel { color: #E2E8F0; }
            QLabel#titulo {
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QLabel#tituloSeccion {
                color: white;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#secundario {
                color: #94A3B8;
                font-size: 12px;
            }
            QLabel#estado {
                color: #93C5FD;
                background-color: #172033;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 8px;
            }
            QFrame#panel {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                background-color: #1E293B;
                color: white;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 7px;
            }
            QLineEdit:focus, QComboBox:focus,
            QSpinBox:focus, QTextEdit:focus {
                border: 1px solid #3B82F6;
            }
            QLineEdit:disabled {
                color: #CBD5E1;
                background-color: #334155;
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
            QPushButton#secundarioBoton { background-color: #475569; }
        """

    def crear_busqueda_cliente(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 11, 12, 11)

        titulo = QLabel("1. Buscar cliente")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        fila = QHBoxLayout()
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Nombre o teléfono del cliente...")
        self.buscar.returnPressed.connect(self.ejecutar_busqueda)

        buscar_btn = QPushButton("Buscar")
        buscar_btn.clicked.connect(self.ejecutar_busqueda)
        nuevo_btn = QPushButton("Cliente nuevo")
        nuevo_btn.setObjectName("secundarioBoton")
        nuevo_btn.clicked.connect(self.preparar_cliente_nuevo)

        fila.addWidget(self.buscar, 1)
        fila.addWidget(buscar_btn)
        fila.addWidget(nuevo_btn)
        layout.addLayout(fila)

        self.combo_clientes = QComboBox()
        self.combo_clientes.addItem(
            "Registrar un cliente nuevo", None
        )
        self.combo_clientes.currentIndexChanged.connect(
            self.seleccionar_cliente
        )
        layout.addWidget(self.combo_clientes)
        return panel

    def crear_formulario_cliente(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 11, 12, 11)

        titulo = QLabel("2. Datos del cliente")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        formulario = QFormLayout()
        self.nombre = QLineEdit()
        self.telefono = QLineEdit()
        self.direccion = QLineEdit()
        self.nombre.setPlaceholderText("Nombre completo o empresa")
        self.telefono.setPlaceholderText("Número de contacto")
        self.direccion.setPlaceholderText("Dirección (opcional)")
        formulario.addRow("Nombre:", self.nombre)
        formulario.addRow("Teléfono:", self.telefono)
        formulario.addRow("Dirección:", self.direccion)
        layout.addLayout(formulario)
        return panel

    def crear_formulario_vehiculo(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 11, 12, 11)

        titulo = QLabel("3. Vehículo y servicio")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        self.combo_vehiculos = QComboBox()
        self.combo_vehiculos.addItem(
            "Registrar un vehículo nuevo", None
        )
        self.combo_vehiculos.currentIndexChanged.connect(
            self.seleccionar_vehiculo
        )
        layout.addWidget(self.combo_vehiculos)

        formulario = QFormLayout()
        self.placa = QLineEdit()
        self.marca = QLineEdit()
        self.modelo = QLineEdit()
        self.anio = QSpinBox()
        self.anio.setRange(1950, datetime.now().year + 1)
        self.anio.setValue(datetime.now().year)
        self.problema = QTextEdit()
        self.problema.setFixedHeight(75)
        self.placa.setPlaceholderText("Ejemplo: M 123456")
        self.problema.setPlaceholderText(
            "Describe el problema informado por el cliente..."
        )

        formulario.addRow("Placa:", self.placa)
        formulario.addRow("Marca:", self.marca)
        formulario.addRow("Modelo:", self.modelo)
        formulario.addRow("Año:", self.anio)
        formulario.addRow("Problema reportado:", self.problema)
        layout.addLayout(formulario)
        return panel

    def ejecutar_busqueda(self):
        texto = self.buscar.text().strip()
        if not texto:
            QMessageBox.information(
                self,
                "Escribe una búsqueda",
                "Ingresa parte del nombre o teléfono del cliente."
            )
            return

        try:
            clientes = buscar_clientes(texto)
        except sqlite3.Error as error:
            QMessageBox.critical(
                self, "Error de búsqueda", str(error)
            )
            return

        self.combo_clientes.blockSignals(True)
        self.combo_clientes.clear()
        self.combo_clientes.addItem(
            "Registrar un cliente nuevo", None
        )

        for cliente in clientes:
            texto_cliente = (
                f"{cliente[1]} | Tel.: {cliente[2] or 'Sin teléfono'} "
                f"| Vehículos: {cliente[4]}"
            )
            self.combo_clientes.addItem(texto_cliente, cliente)

        self.combo_clientes.blockSignals(False)

        if clientes:
            self.combo_clientes.setCurrentIndex(1)
            self.seleccionar_cliente(1)
        else:
            self.preparar_cliente_nuevo()
            QMessageBox.information(
                self,
                "Sin coincidencias",
                "No se encontró el cliente. Puedes registrarlo como nuevo."
            )

    def seleccionar_cliente(self, indice):
        cliente = self.combo_clientes.itemData(indice)
        if cliente is None:
            self.preparar_cliente_nuevo(False)
            return

        self.cliente_id = int(cliente[0])
        self.nombre.setText(str(cliente[1]))
        self.telefono.setText(str(cliente[2]))
        self.direccion.setText(str(cliente[3]))
        self.cargar_vehiculos_cliente()
        self.lbl_estado.setText(
            f"Cliente seleccionado: {cliente[1]}. "
            "Escoge un vehículo existente o registra uno nuevo."
        )

    def preparar_cliente_nuevo(self, cambiar_combo=True):
        self.cliente_id = None
        self.vehiculo_id = None
        if cambiar_combo:
            self.combo_clientes.setCurrentIndex(0)

        self.nombre.clear()
        self.telefono.clear()
        self.direccion.clear()
        self.combo_vehiculos.blockSignals(True)
        self.combo_vehiculos.clear()
        self.combo_vehiculos.addItem(
            "Registrar un vehículo nuevo", None
        )
        self.combo_vehiculos.blockSignals(False)
        self.limpiar_vehiculo()
        self.lbl_estado.setText(
            "Modo actual: registrar un cliente y vehículo nuevos."
        )

    def cargar_vehiculos_cliente(self):
        try:
            vehiculos = obtener_vehiculos_cliente(self.cliente_id)
        except sqlite3.Error as error:
            QMessageBox.critical(
                self, "Error de vehículos", str(error)
            )
            return

        self.combo_vehiculos.blockSignals(True)
        self.combo_vehiculos.clear()
        self.combo_vehiculos.addItem(
            "Registrar otro vehículo para este cliente", None
        )
        for vehiculo in vehiculos:
            self.combo_vehiculos.addItem(
                f"{vehiculo[1]} | {vehiculo[2]} {vehiculo[3]}",
                vehiculo
            )
        self.combo_vehiculos.blockSignals(False)
        self.combo_vehiculos.setCurrentIndex(0)
        self.limpiar_vehiculo()

    def seleccionar_vehiculo(self, indice):
        vehiculo = self.combo_vehiculos.itemData(indice)
        if vehiculo is None:
            self.vehiculo_id = None
            self.limpiar_vehiculo()
            if self.cliente_id is not None:
                self.lbl_estado.setText(
                    "Registrarás un vehículo nuevo para el cliente seleccionado."
                )
            return

        self.vehiculo_id = int(vehiculo[0])
        self.placa.setText(str(vehiculo[1]))
        self.marca.setText(str(vehiculo[2]))
        self.modelo.setText(str(vehiculo[3]))
        self.anio.setValue(
            int(vehiculo[4]) if vehiculo[4] else datetime.now().year
        )
        self.placa.setEnabled(False)
        self.lbl_estado.setText(
            f"Vehículo seleccionado: {vehiculo[1]}. "
            "Se creará una nueva orden en su historial."
        )

    def limpiar_vehiculo(self):
        self.vehiculo_id = None
        self.placa.setEnabled(True)
        self.placa.clear()
        self.marca.clear()
        self.modelo.clear()
        self.anio.setValue(datetime.now().year)
        self.problema.clear()

    def guardar(self):
        nombre = self.nombre.text().strip()
        telefono = self.telefono.text().strip()
        direccion = self.direccion.text().strip()
        placa = self.placa.text().strip().upper()
        marca = self.marca.text().strip()
        modelo = self.modelo.text().strip()
        problema = self.problema.toPlainText().strip()

        if not all((nombre, placa, marca, modelo, problema)):
            QMessageBox.warning(
                self,
                "Faltan datos",
                "Completa el nombre, la placa, la marca, "
                "el modelo y el problema reportado."
            )
            return

        try:
            numero_orden = registrar_recepcion(
                nombre,
                telefono,
                direccion,
                placa,
                marca,
                modelo,
                self.anio.value(),
                problema,
                self.cliente_id,
                self.vehiculo_id
            )
        except ValueError as error:
            QMessageBox.warning(
                self, "No se pudo registrar", str(error)
            )
            return
        except sqlite3.IntegrityError as error:
            QMessageBox.critical(
                self,
                "Error de integridad",
                f"No se pudo guardar la recepción:\n{error}"
            )
            return
        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo guardar la recepción:\n{error}"
            )
            return

        QMessageBox.information(
            self,
            "Recepción guardada",
            f"Se creó correctamente la orden de servicio N.º {numero_orden}."
        )
        self.accept()