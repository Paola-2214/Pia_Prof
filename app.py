
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

BASE_DATOS = "database/techsolutions.db"


def conectar():
    conexion = sqlite3.connect(BASE_DATOS)
    conexion.row_factory = sqlite3.Row
    return conexion


def correo_valido(correo):
    patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.fullmatch(patron, correo) is not None


@app.context_processor
def contador_notificaciones():

    resultado = {
        "notificaciones_pendientes": 0,
        "notificaciones_admin_pendientes": 0
    }

    if "usuario_id" not in session:
        return resultado

    conexion = conectar()

    cantidad = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM notificaciones
        WHERE usuario_id = ?
          AND leida = 0
    """, (session["usuario_id"],)).fetchone()["total"]

    conexion.close()

    if session.get("rol") == "cliente":
        resultado["notificaciones_pendientes"] = cantidad

    elif session.get("rol") == "admin":
        resultado["notificaciones_admin_pendientes"] = cantidad

    return resultado



def iniciar_base_datos():
    os.makedirs("database", exist_ok=True)

    conexion = conectar()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL,
            servicio TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'cliente'
                CHECK (rol IN ('cliente', 'admin')),
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    columnas = conexion.execute("""
        PRAGMA table_info(cotizaciones)
    """).fetchall()

    nombres_columnas = [columna["name"] for columna in columnas]

    if "estado" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN estado TEXT NOT NULL DEFAULT 'Pendiente'
        """)

    if "usuario_id" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)
        """)

    if "precio" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN precio REAL
        """)


    if "decision" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN decision TEXT NOT NULL DEFAULT 'Pendiente'
        """)

    
    if "fecha_aceptacion" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN fecha_aceptacion TEXT
        """)

    if "fecha_inicio" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN fecha_inicio TEXT
        """)

    if "fecha_finalizacion" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE cotizaciones
            ADD COLUMN fecha_finalizacion TEXT
        """)


    conexion.execute("""
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            cotizacion_id INTEGER,
            titulo TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            leida INTEGER NOT NULL DEFAULT 0,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id)
        )
    """)


    conexion.commit()
    conexion.close()


iniciar_base_datos()


@app.route("/")
def inicio():
    return render_template("index.html")


SERVICIOS = {
    "mantenimiento": {
        "nombre": "Mantenimiento de computadoras",
        "categoria": "SOPORTE TÉCNICO",
        "descripcion": "Mejoramos el funcionamiento de tus equipos mediante diagnóstico, limpieza, reparación y optimización.",
        "incluye": [
            "Diagnóstico general del equipo",
            "Limpieza y mantenimiento preventivo",
            "Revisión de componentes",
            "Optimización del sistema",
            "Recomendaciones para mejorar el rendimiento"
        ],
        "imagenes": [
            "https://images.unsplash.com/photo-1581092921461-eab62e97a780?auto=format&fit=crop&w=1200&q=85",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=85"
        ]
    },
    "desarrollo-web": {
        "nombre": "Desarrollo de páginas web",
        "categoria": "DESARROLLO DIGITAL",
        "descripcion": "Creamos sitios web modernos, funcionales y adaptables para emprendedores y empresas.",
        "incluye": [
            "Diseño de la estructura del sitio",
            "Desarrollo de páginas responsivas",
            "Formularios y secciones informativas",
            "Adaptación para computadoras y celulares",
            "Pruebas de funcionamiento"
        ],
        "imagenes": [
            "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=85",
            "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=1000&q=85"
        ]
    },
    "redes": {
        "nombre": "Instalación y configuración de redes",
        "categoria": "CONECTIVIDAD",
        "descripcion": "Configuramos soluciones de conectividad para hogares, oficinas y pequeños negocios.",
        "incluye": [
            "Evaluación de necesidades de conectividad",
            "Instalación y configuración de redes",
            "Configuración de routers y dispositivos",
            "Pruebas de conexión",
            "Recomendaciones de seguridad de red"
        ],
        "imagenes": [
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1200&q=85",
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=1000&q=85"
        ]
    }
}


@app.route("/servicios/<slug>")
def detalle_servicio(slug):
    servicio = SERVICIOS.get(slug)

    if servicio is None:
        return "Servicio no encontrado.", 404

    return render_template(
        "servicio.html",
        servicio=servicio
    )


@app.route("/cotizacion", methods=["GET", "POST"])
def cotizacion():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        servicio = request.form.get("servicio", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not nombre or not correo or not servicio or not descripcion:
            return "Debes completar todos los campos.", 400

        conexion = conectar()
        
        if not correo_valido(correo):
            return "Ingresa un correo electrónico válido.", 400

        servicios_validos = [
            "Mantenimiento de computadoras",
            "Desarrollo de páginas web",
            "Instalación y configuración de redes"
        ]

        if servicio not in servicios_validos:
            return "Selecciona un servicio válido.", 400

        conexion.execute("""
            INSERT INTO cotizaciones
            (nombre, correo, servicio, descripcion, usuario_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            nombre,
            correo,
            servicio,
            descripcion,
            session["usuario_id"]
        ))

        conexion.commit()
        conexion.close()

        return render_template("cotizacion.html", exito=True)

    
    servicio_seleccionado = request.args.get("servicio", "")

    servicios_validos = [
        "Mantenimiento de computadoras",
        "Desarrollo de páginas web",
        "Instalación y configuración de redes"
    ]

    if servicio_seleccionado not in servicios_validos:
        servicio_seleccionado = ""

    return render_template(
        "cotizacion.html",
        exito=False,
        servicio_seleccionado=servicio_seleccionado
    )



@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not nombre or not correo or not contrasena:
            return render_template(
                "registro.html",
                error="Completa todos los campos."
            )

        if not correo_valido(correo):
            return render_template(
                "registro.html",
                error="Ingresa un correo electrónico válido."
            )
        
        if len(contrasena) < 8:
            return render_template(
                "registro.html",
                error="La contraseña debe tener al menos 8 caracteres."
            )

        conexion = conectar()

        existente = conexion.execute("""
            SELECT id FROM usuarios
            WHERE correo = ?
        """, (correo,)).fetchone()

        if existente:
            conexion.close()

            return render_template(
                "registro.html",
                error="Este correo ya está registrado."
            )

        contrasena_segura = generate_password_hash(contrasena)

        conexion.execute("""
            INSERT INTO usuarios
            (nombre, correo, contrasena, rol)
            VALUES (?, ?, ?, 'cliente')
        """, (nombre, correo, contrasena_segura))

        conexion.commit()
        conexion.close()

        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        conexion = conectar()

        usuario = conexion.execute("""
            SELECT * FROM usuarios
            WHERE correo = ?
        """, (correo,)).fetchone()

        conexion.close()

        if usuario and check_password_hash(usuario["contrasena"], contrasena):
            session.clear()

            session["usuario_id"] = usuario["id"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]

            if usuario["rol"] == "admin":
                return redirect(url_for("administrador"))

            return redirect(url_for("inicio"))

        return render_template(
            "login.html",
            error="Correo o contraseña incorrectos."
        )

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("inicio"))


@app.route("/admin")
def administrador():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return (
            "Acceso denegado. Esta sección es exclusiva para administradores.",
            403
        )

    conexion = conectar()

    cotizaciones = conexion.execute("""
        SELECT * FROM cotizaciones
        ORDER BY id DESC
    """).fetchall()

    total_cotizaciones = conexion.execute("""
        SELECT COUNT(*) FROM cotizaciones
    """).fetchone()[0]

    total_clientes = conexion.execute("""
        SELECT COUNT(*) FROM usuarios
        WHERE rol = 'cliente'
    """).fetchone()[0]

    total_mantenimiento = conexion.execute("""
        SELECT COUNT(*) FROM cotizaciones
        WHERE servicio = 'Mantenimiento de computadoras'
    """).fetchone()[0]

    total_web = conexion.execute("""
        SELECT COUNT(*) FROM cotizaciones
        WHERE servicio = 'Desarrollo de páginas web'
    """).fetchone()[0]

    total_redes = conexion.execute("""
        SELECT COUNT(*) FROM cotizaciones
        WHERE servicio = 'Instalación y configuración de redes'
    """).fetchone()[0]

    conexion.close()

    return render_template(
        "admin.html",
        cotizaciones=cotizaciones,
        total_cotizaciones=total_cotizaciones,
        total_clientes=total_clientes,
        total_mantenimiento=total_mantenimiento,
        total_web=total_web,
        total_redes=total_redes
    )



@app.route("/admin/cotizacion/<int:cotizacion_id>/precio", methods=["POST"])
def asignar_precio(cotizacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "Acceso denegado.", 403

    precio_texto = request.form.get("precio", "").strip()

    try:
        from decimal import Decimal, InvalidOperation

        precio = Decimal(precio_texto)

        if not precio.is_finite() or precio <= 0:
            return "El precio debe ser mayor que cero.", 400

        if precio.as_tuple().exponent < -2:
            return "El precio solo puede tener dos decimales.", 400

        if precio > Decimal("99999999.99"):
            return "El precio es demasiado alto.", 400

    except InvalidOperation:
        return "Ingresa un precio válido.", 400

    conexion = conectar()

    
    cotizacion = conexion.execute("""
        SELECT usuario_id, servicio
        FROM cotizaciones
        WHERE id = ?
          AND decision = 'Pendiente'
    """, (cotizacion_id,)).fetchone()

    if cotizacion is None:
        conexion.close()
        return "Cotización no encontrada o ya respondida.", 404

    resultado = conexion.execute("""
        UPDATE cotizaciones
        SET precio = ?
        WHERE id = ?
          AND decision = 'Pendiente'
    """, (float(precio), cotizacion_id))

    if resultado.rowcount == 1:

        titulo = "¡Ya tienes una propuesta de precio!"

        mensaje = (
            f"TechSolutions ha propuesto un precio de "
            f"${float(precio):,.2f} MXN para tu servicio de "
            f"{cotizacion['servicio']}. "
            f"Entra a Mis cotizaciones para aceptarlo o rechazarlo."
        )

        conexion.execute("""
            INSERT INTO notificaciones (
                usuario_id,
                cotizacion_id,
                titulo,
                mensaje
            )
            VALUES (?, ?, ?, ?)
        """, (
            cotizacion["usuario_id"],
            cotizacion_id,
            titulo,
            mensaje
        ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("administrador"))




@app.route("/cliente/cotizacion/<int:cotizacion_id>/decision", methods=["POST"])
def decidir_cotizacion(cotizacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return "Acceso denegado.", 403

    decision = request.form.get("decision", "")

    if decision not in ["Aceptada", "Rechazada"]:
        return "Decisión no válida.", 400

    conexion = conectar()

    cotizacion = conexion.execute("""
        SELECT id, precio, decision, servicio
        FROM cotizaciones
        WHERE id = ? AND usuario_id = ?
    """, (cotizacion_id, session["usuario_id"])).fetchone()

    if cotizacion is None:
        conexion.close()
        return "Cotización no encontrada.", 404

    if cotizacion["precio"] is None:
        conexion.close()
        return "Esta cotización todavía no tiene precio.", 400

    if cotizacion["decision"] != "Pendiente":
        conexion.close()
        return "Esta cotización ya tiene una decisión registrada.", 400

    resultado = conexion.execute("""
        UPDATE cotizaciones
        SET decision = ?,
            fecha_aceptacion = CASE
                WHEN ? = 'Aceptada' THEN CURRENT_TIMESTAMP
                ELSE NULL
            END
        WHERE id = ?
          AND usuario_id = ?
          AND decision = 'Pendiente'
          AND precio IS NOT NULL
    """, (
        decision,
        decision,
        cotizacion_id,
        session["usuario_id"]
    ))

    if resultado.rowcount == 1:

        if decision == "Aceptada":
            titulo = "Cotización aceptada"
            mensaje = (
                f"El cliente {session['nombre']} aceptó "
                f"la cotización #{cotizacion_id} de "
                f"{cotizacion['servicio']}."
            )

        else:
            titulo = "Cotización rechazada"
            mensaje = (
                f"El cliente {session['nombre']} rechazó "
                f"la cotización #{cotizacion_id} de "
                f"{cotizacion['servicio']}."
            )

        administradores = conexion.execute("""
            SELECT id
            FROM usuarios
            WHERE rol = 'admin'
        """).fetchall()

        for administrador in administradores:

            conexion.execute("""
                INSERT INTO notificaciones (
                    usuario_id,
                    cotizacion_id,
                    titulo,
                    mensaje
                )
                VALUES (?, ?, ?, ?)
            """, (
                administrador["id"],
                cotizacion_id,
                titulo,
                mensaje
            ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("panel_cliente"))



@app.route("/cliente")
def panel_cliente():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return redirect(url_for("administrador"))

    conexion = conectar()

    cotizaciones = conexion.execute("""
        SELECT *
        FROM cotizaciones
        WHERE usuario_id = ?
        ORDER BY id DESC
    """, (session["usuario_id"],)).fetchall()

    total_cotizaciones = len(cotizaciones)

    pendientes = sum(
        1 for cotizacion in cotizaciones
        if cotizacion["estado"] == "Pendiente"
    )

    en_proceso = sum(
        1 for cotizacion in cotizaciones
        if cotizacion["estado"] == "En proceso"
    )

    finalizadas = sum(
        1 for cotizacion in cotizaciones
        if cotizacion["estado"] == "Finalizada"
    )

    conexion.close()

    return render_template(
        "cliente.html",
        cotizaciones=cotizaciones,
        total_cotizaciones=total_cotizaciones,
        pendientes=pendientes,
        en_proceso=en_proceso,
        finalizadas=finalizadas
    )




@app.route("/admin/cotizacion/<int:cotizacion_id>/estado", methods=["POST"])
def cambiar_estado(cotizacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "Acceso denegado.", 403

    nuevo_estado = request.form.get("estado", "")

    conexion = conectar()

    cotizacion = conexion.execute("""
        SELECT estado, decision, usuario_id, servicio
        FROM cotizaciones
        WHERE id = ?
    """, (cotizacion_id,)).fetchone()

    if cotizacion is None:
        conexion.close()
        return "Cotización no encontrada.", 404

    if cotizacion["decision"] != "Aceptada":
        conexion.close()
        return "El cliente debe aceptar la cotización primero.", 400

    estado_actual = cotizacion["estado"]

    transiciones = {
        "Pendiente": "En proceso",
        "En proceso": "Finalizada"
    }

    if estado_actual not in transiciones:
        conexion.close()
        return "Este servicio ya está finalizado.", 400

    if nuevo_estado != transiciones[estado_actual]:
        conexion.close()
        return "Debes seguir el orden de los estados.", 400

  
    resultado = conexion.execute("""
    UPDATE cotizaciones
        SET estado = ?,
            fecha_inicio = CASE
                WHEN ? = 'En proceso'
                THEN CURRENT_TIMESTAMP
                ELSE fecha_inicio
            END,
            fecha_finalizacion = CASE
                WHEN ? = 'Finalizada'
                THEN CURRENT_TIMESTAMP
                ELSE fecha_finalizacion
            END
        WHERE id = ?
          AND estado = ?
          AND decision = 'Aceptada'
    """, (
        nuevo_estado,
        nuevo_estado,
        nuevo_estado,
        cotizacion_id,
        estado_actual
    ))


    if nuevo_estado == "En proceso":
        titulo = "Tu servicio está en proceso"
        mensaje = (
            f"Comenzamos a trabajar en tu servicio de "
            f"{cotizacion['servicio']}."
        )

    elif nuevo_estado == "Finalizada":
        titulo = "¡Tu servicio fue finalizado!"
        mensaje = (
            f"El servicio de {cotizacion['servicio']} "
            f"ha sido completado."
        )

    if resultado.rowcount == 1:
        conexion.execute("""
            INSERT INTO notificaciones (
                usuario_id,
                cotizacion_id,
                titulo,
                mensaje
            )
            VALUES (?, ?, ?, ?)
        """, (
            cotizacion["usuario_id"],
            cotizacion_id,
            titulo,
            mensaje
        ))


    conexion.commit()
    conexion.close()

    return redirect(url_for("administrador"))




@app.route("/mis-contrataciones")
def mis_contrataciones():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return "Acceso denegado.", 403

    conexion = conectar()

    contrataciones = conexion.execute("""
        SELECT *
        FROM cotizaciones
        WHERE usuario_id = ?
          AND decision = 'Aceptada'
        ORDER BY id DESC
    """, (session["usuario_id"],)).fetchall()

    conexion.close()

    imagenes = {
        "Mantenimiento de computadoras":
            "https://images.unsplash.com/photo-1581092921461-eab62e97a780?auto=format&fit=crop&w=1000&q=85",

        "Desarrollo de páginas web":
            "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1000&q=85",

        "Instalación y configuración de redes":
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1000&q=85"
    }

    return render_template(
        "contrataciones.html",
        contrataciones=contrataciones,
        imagenes=imagenes
    )


@app.route("/mis-contrataciones/<int:cotizacion_id>")
def detalle_contratacion(cotizacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return "Acceso denegado.", 403

    conexion = conectar()

    contratacion = conexion.execute("""
        SELECT *
        FROM cotizaciones
        WHERE id = ?
          AND usuario_id = ?
          AND decision = 'Aceptada'
    """, (
        cotizacion_id,
        session["usuario_id"]
    )).fetchone()

    conexion.close()

    if contratacion is None:
        return "Contratación no encontrada.", 404

    servicio = None

    for datos_servicio in SERVICIOS.values():
        if datos_servicio["nombre"] == contratacion["servicio"]:
            servicio = datos_servicio
            break

    if servicio is None:
        return "Información del servicio no disponible.", 404

    return render_template(
        "detalle_contratacion.html",
        contratacion=contratacion,
        servicio=servicio
    )


@app.route("/notificaciones")
def notificaciones():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return "Acceso denegado.", 403

    conexion = conectar()

    avisos = conexion.execute("""
        SELECT *
        FROM notificaciones
        WHERE usuario_id = ?
        ORDER BY fecha DESC, id DESC
    """, (session["usuario_id"],)).fetchall()

    no_leidas = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM notificaciones
        WHERE usuario_id = ? AND leida = 0
    """, (session["usuario_id"],)).fetchone()["total"]

    conexion.close()

    return render_template(
        "notificaciones.html",
        avisos=avisos,
        no_leidas=no_leidas
    )


@app.route("/notificaciones/<int:notificacion_id>/leer", methods=["POST"])
def marcar_notificacion_leida(notificacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "cliente":
        return "Acceso denegado.", 403

    conexion = conectar()

    conexion.execute("""
        UPDATE notificaciones
        SET leida = 1
        WHERE id = ?
          AND usuario_id = ?
          AND leida = 0
    """, (notificacion_id, session["usuario_id"]))

    conexion.commit()
    conexion.close()

    return redirect(url_for("notificaciones"))


@app.route("/admin/notificaciones")
def notificaciones_admin():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "Acceso denegado.", 403

    conexion = conectar()

    avisos = conexion.execute("""
        SELECT *
        FROM notificaciones
        WHERE usuario_id = ?
        ORDER BY fecha DESC, id DESC
    """, (session["usuario_id"],)).fetchall()

    no_leidas = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM notificaciones
        WHERE usuario_id = ?
          AND leida = 0
    """, (session["usuario_id"],)).fetchone()["total"]

    conexion.close()

    return render_template(
        "notificaciones_admin.html",
        avisos=avisos,
        no_leidas=no_leidas
    )


@app.route("/admin/notificaciones/<int:notificacion_id>/leer", methods=["POST"])
def marcar_notificacion_admin_leida(notificacion_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "Acceso denegado.", 403

    conexion = conectar()

    conexion.execute("""
        UPDATE notificaciones
        SET leida = 1
        WHERE id = ?
          AND usuario_id = ?
          AND leida = 0
    """, (notificacion_id, session["usuario_id"]))

    conexion.commit()
    conexion.close()

    return redirect(url_for("notificaciones_admin"))


if __name__ == "__main__":
    app.run(debug=True)
