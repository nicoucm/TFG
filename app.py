import os
import pathlib
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- LIBRERÍAS DE GOOGLE ---
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from google.auth.transport import requests as google_requests

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secreto-tfg"

# --- CONFIGURACIÓN GOOGLE ---
# Esto permite que funcione en tu ordenador (http) sin certificado de seguridad
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Buscamos el archivo JSON que acabas de descargar
CLIENT_SECRETS_FILE = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

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
    role = db.Column(db.String(20), nullable=False, default="estudiante")
    password_hash = db.Column(db.String(200), nullable=True)

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

class Incident(db.Model):
    __tablename__ = "incidents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Abierta")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # El user_id es opcional (nullable=True) para permitir incidencias ANÓNIMAS
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="incidents")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS DE LOGIN GOOGLE ---

@app.route("/login_google")
def login_google():
    """Paso 1: El usuario pulsa el botón y le enviamos a Google"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
    )
    # Le decimos a Google que vuelva a nuestra ruta /callback
    flow.redirect_uri = url_for("callback", _external=True)
    
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    """Paso 2: Google nos devuelve al usuario. Verificamos quién es."""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
            state=session["state"]
        )
        flow.redirect_uri = url_for("callback", _external=True)

        # Canjeamos el código que nos da Google por un Token real
        flow.fetch_token(authorization_response=request.url)

        # Verificamos la identidad
        credentials = flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google_requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=credentials.client_id
        )

        email = id_info.get("email")
        name = id_info.get("name")

        # --- FILTRO UCM (Opcional) ---
        # if not email.endswith("@ucm.es"):
        #     flash("Lo sentimos, solo se permite acceso con cuenta @ucm.es", "error")
        #     return redirect(url_for("login"))

        # Buscamos si el usuario ya existe, si no, lo creamos
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name=name, role="estudiante")
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        flash(f"¡Bienvenido/a {name}!", "success")
        return redirect(url_for("home"))

    except Exception as e:
        flash(f"Error en el inicio de sesión con Google: {str(e)}", "error")
        return redirect(url_for("login"))

# --- RESTO DE RUTAS ---

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
            flash("Sesión iniciada correctamente.", "success")
            return redirect(url_for("home"))
        else:
            flash("Credenciales incorrectas.", "error")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("home"))

@app.route("/asignaturas")
def subjects(): 
    return render_template("subjects.html")

@app.route("/materiales")
def materials(): 
    return render_template("materials.html")

@app.route("/incidencias", methods=["GET", "POST"])
@login_required
def incidents():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        is_anonymous = request.form.get("anonymous") # Comprueba si marcaron la casilla
        
        # LA MAGIA DEL ANONIMATO:
        # Si marcan la casilla, guardamos 'None' en el ID de usuario. 
        # Si no la marcan, guardamos su ID real para que puedan ver el estado luego.
        user_id_to_save = None if is_anonymous else current_user.id
        
        nueva_incidencia = Incident(
            title=title,
            description=description,
            user_id=user_id_to_save
        )
        db.session.add(nueva_incidencia)
        db.session.commit()
        
        flash("Tu incidencia ha sido enviada correctamente al equipo de moderación.", "success")
        return redirect(url_for("incidents"))
        
    # Cuando entran a la página (GET), buscamos solo las incidencias que SÍ tienen su nombre
    # para mostrárselas en una tablita y que vean si están resueltas.
    mis_incidencias = Incident.query.filter_by(user_id=current_user.id).order_by(Incident.created_at.desc()).all()
    
    return render_template("incidents.html", incidencias=mis_incidencias)

@app.route("/actividades")
def activities(): 
    return render_template("activities.html")

@app.route("/accesible")
def accessible_mode():
    return render_template("accessible.html")

# --- RUTAS DE GESTIÓN DE ANUNCIOS ---
@app.route("/anuncios")
def ads():
    now = datetime.utcnow()
    # Muestra solo los anuncios que no han caducado, ordenados por fecha
    anuncios = Announcement.query.filter(Announcement.expires_at >= now).order_by(Announcement.created_at.desc()).all()
    return render_template("ads/ads.html", anuncios=anuncios)

@app.route("/anuncios/nuevo", methods=["GET", "POST"])
@login_required
def ad_create():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        # Convertimos la fecha del formulario (string) a objeto datetime
        expires_at_str = request.form["expires_at"]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        
        nuevo_anuncio = Announcement(
            title=title,
            content=content,
            expires_at=expires_at,
            user_id=current_user.id
        )
        db.session.add(nuevo_anuncio)
        db.session.commit()
        flash("Anuncio publicado con éxito.", "success")
        return redirect(url_for("ads"))
        
    return render_template("ads/ad_form.html", mode="nuevo")

@app.route("/anuncios/<int:ad_id>")
def ad_detail(ad_id):
    anuncio = Announcement.query.get_or_404(ad_id)
    return render_template("ads/ad_detail.html", anuncio=anuncio)

@app.route("/anuncios/<int:ad_id>/editar", methods=["GET", "POST"])
@login_required
def ad_edit(ad_id):
    anuncio = Announcement.query.get_or_404(ad_id)
    
    # Seguridad: Solo el dueño o un admin pueden editar
    if current_user.role != 'admin' and current_user.id != anuncio.user_id:
        flash("No tienes permiso para editar este anuncio.", "error")
        return redirect(url_for("ads"))
        
    if request.method == "POST":
        anuncio.title = request.form["title"]
        anuncio.content = request.form["content"]
        expires_at_str = request.form["expires_at"]
        anuncio.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        
        db.session.commit()
        flash("Anuncio actualizado correctamente.", "success")
        return redirect(url_for("ad_detail", ad_id=anuncio.id))
        
    return render_template("ads/ad_form.html", mode="editar", anuncio=anuncio)

@app.route("/anuncios/<int:ad_id>/eliminar", methods=["POST"])
@login_required
def ad_delete(ad_id):
    anuncio = Announcement.query.get_or_404(ad_id)
    
    # Seguridad: Solo el dueño o un admin pueden borrar
    if current_user.role != 'admin' and current_user.id != anuncio.user_id:
        flash("No tienes permiso para eliminar este anuncio.", "error")
        return redirect(url_for("ads"))
        
    db.session.delete(anuncio)
    db.session.commit()
    flash("Anuncio eliminado.", "success")
    return redirect(url_for("ads"))
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)