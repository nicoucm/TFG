from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import os

# --------------------------------------------------------------------
# Configuración básica de Flask
# --------------------------------------------------------------------

app = Flask(__name__)

# Clave para sesiones (cámbiala por algo más seguro en producción)
app.config["SECRET_KEY"] = "super-secreto-tfg"

# --------------------------------------------------------------------
# Configuración de la base de datos (SQLite)
# --------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "tfg.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --------------------------------------------------------------------
# Configuración de Flask-Login
# --------------------------------------------------------------------

login_manager = LoginManager(app)
login_manager.login_view = "login"  # si no está logueado redirige a /login


# --------------------------------------------------------------------
# Modelo de Usuario
# --------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="estudiante")
    # roles: "admin", "profesor", "estudiante", "invitado"

    def set_password(self, password: str) -> None:
        """Genera y guarda el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Comprueba si la contraseña introducida es correcta."""
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------------------------------------------------------
# Rutas principales de la plataforma
# --------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/asignaturas")
def subjects():
    return render_template("subjects.html")


@app.route("/materiales")
def materials():
    return render_template("materials.html")


@app.route("/incidencias")
@login_required
def incidents():
    # aquí más adelante filtrarás incidencias por usuario/rol
    return render_template("incidents.html")


@app.route("/actividades")
def activities():
    return render_template("activities.html")


@app.route("/anuncios")
def ads():
    return render_template("ads.html")


@app.route("/accesible")
def accessible_mode():
    return render_template("accessible.html")


# --------------------------------------------------------------------
# Autenticación: registro, login, logout
# --------------------------------------------------------------------

@app.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form.get("role", "estudiante")

        # ¿Existe ya un usuario con ese email?
        if User.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese email.", "error")
            return redirect(url_for("register"))

        user = User(email=email, name=name, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Usuario creado correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Has iniciado sesión correctamente.", "success")
            return redirect(url_for("home"))
        else:
            flash("Email o contraseña incorrectos.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("¡Sesión cerrada correctamente!", "success")
    return redirect(url_for("home"))

# --------------------------------------------------------------------
# Ejemplo de ruta solo para admins (opcional, para más adelante)
# --------------------------------------------------------------------

@app.route("/admin/panel")
@login_required
def admin_panel():
    if current_user.role != "admin":
        flash("No tienes permiso para acceder a esta sección.", "error")
        return redirect(url_for("home"))
    return render_template("admin_panel.html")


# --------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------

if __name__ == "__main__":
    # OJO: antes de la primera ejecución, crea la BD con:
    # >>> from app import db
    # >>> db.create_all()
    app.run(debug=True)
