from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout
)

from base_datos.database import validar_usuario


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.usuario_autenticado = None
        self.setWindowTitle("Acceso a AutoFix")
        self.setFixedSize(390, 300)

        self.setStyleSheet("""
            QDialog {
                background-color: #121826;
                color: #F8FAFC;
            }

            QLabel {
                color: #CBD5E1;
                font-size: 13px;
            }

            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 8px;
            }

            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }

            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        titulo = QLabel("AutoFix")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet(
            "color: white; font-size: 26px; font-weight: bold;"
        )

        subtitulo = QLabel("Inicia sesión para acceder al sistema")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet("color: #94A3B8;")

        formulario = QFormLayout()
        formulario.setSpacing(12)

        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Nombre de usuario")

        self.clave = QLineEdit()
        self.clave.setPlaceholderText("Contraseña")
        self.clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.clave.returnPressed.connect(self.iniciar_sesion)

        formulario.addRow("Usuario:", self.usuario)
        formulario.addRow("Contraseña:", self.clave)

        btn_ingresar = QPushButton("Iniciar sesión")
        btn_ingresar.clicked.connect(self.iniciar_sesion)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addLayout(formulario)
        layout.addWidget(btn_ingresar)

        self.usuario.setFocus()

    def iniciar_sesion(self):
        nombre_usuario = self.usuario.text().strip()
        clave = self.clave.text()

        if not nombre_usuario or not clave:
            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Escribe el usuario y la contraseña."
            )
            return

        usuario = validar_usuario(nombre_usuario, clave)

        if usuario is None:
            self.clave.clear()
            self.clave.setFocus()

            QMessageBox.warning(
                self,
                "Acceso denegado",
                "El usuario o la contraseña son incorrectos."
            )
            return

        self.usuario_autenticado = usuario
        self.accept()