from flask import Flask, render_template, redirect, url_for, request, flash, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import identity.web  # Requiere: pip install identity

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secreto-tfg"

# --- CONFIGURACIÓN SSO UCM (Microsoft Azure AD) ---
# Se recomienda crear un archivo .env con estos valores
CLIENT_ID = os.getenv("CLIENT_ID", "pon-aqui-tu-client-id")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "pon-aqui-tu-client-secret")
AUTHORITY = os.getenv("AUTHORITY", "https://login.microsoftonline.com/common") 

# Configuración de Sesión (Necesaria para manejar el flujo de SSO)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Adaptador de identidad para gestionar el login con Microsoft
auth = identity.web.Auth(
    session=session,
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY,
)

# --- CONFIGURACIÓN BASE DE DATOS ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "tfg.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- MODELOS ---
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=True) # Nullable para usuarios SSO
    role = db.Column(db.String(20), nullable=False, default="estudiante")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash: return False
        return check_password_hash(self.password_hash, password)

class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="announcements")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS DE AUTENTICACIÓN SSO ---

@app.route("/getAToken")
def auth_response():
    """Callback donde Microsoft redirige al usuario tras el login"""
    result = auth.complete_log_in(request.args)
    if "error" in result:
        flash(f"Error en SSO: {result.get('error_description')}", "error")
        return redirect(url_for("login"))
    
    user_claims = result.get("id_token_claims")
    email = user_claims.get("preferred_username").lower()
    name = user_claims.get("name")

    # Verificar si el usuario ya existe en tfg.db
    user = User.query.filter_by(email=email).first()

    if not user:
        # Registro automático de nuevos alumnos UCM
        user = User(email=email, name=name, role="estudiante")
        db.session.add(user)
        db.session.commit()
        flash(f"Cuenta creada automáticamente para {name}.", "success")
    
    login_user(user)
    return redirect(url_for("home"))

# --- RUTAS DE NAVEGACIÓN Y LOGICA ---

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Sesión local iniciada.", "success")
            return redirect(url_for("home"))
        else:
            flash("Credenciales incorrectas.", "error")
            return redirect(url_for("login"))
    
    # Preparamos la URL de SSO para el botón en la plantilla
    sso_context = auth.log_in(
        scopes=["User.Read"],
        redirect_uri=url_for("auth_response", _external=True)
    )
    return render_template("login.html", auth_url=sso_context["auth_uri"])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    # Redirige también al logout de Microsoft para cierre completo
    return redirect(auth.log_out(url_for("home", _external=True)))

@app.route("/asignaturas")
def subjects(): 
    return render_template("subjects.html")

@app.route("/materiales")
def materials(): 
    return render_template("materials.html")

@app.route("/incidencias")
@login_required
def incidents(): 
    return render_template("incidents.html")

@app.route("/actividades")
def activities(): 
    return render_template("activities.html")

@app.route("/accesible")
def accessible_mode():
    return render_template("accessible.html")

@app.route("/anuncios")
def ads():
    # Limpieza rápida de anuncios expirados (opcional aquí)
    now = datetime.utcnow()
    anuncios = Announcement.query.filter(Announcement.expires_at >= now).order_by(Announcement.created_at.desc()).all()
    return render_template("ads/ads.html", anuncios=anuncios)

# --- INICIO DE LA APP ---

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Asegura que tfg.db tenga las tablas actualizadas
    app.run(debug=True)