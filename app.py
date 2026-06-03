import os
import pathlib
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# LIBRERÍAS DE GOOGLE
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from google.auth.transport import requests as google_requests

# IMPORTAMOS LA BASE DE DATOS Y LOS MODELOS DESDE EL NUEVO ARCHIVO
from models import db, User, Announcement, Incident, Activity, Document, Review
app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secreto-tfg"

# --- CONFIGURACIÓN GOOGLE ---
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
CLIENT_SECRETS_FILE = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

# --- CONFIGURACIÓN DB Y ARCHIVOS ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "tfg.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# INICIALIZAMOS LA DB CON LA APP
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- RUTAS DE LOGIN GOOGLE ---
@app.route("/login_google")
def login_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
    )
    flow.redirect_uri = url_for("callback", _external=True)
    authorization_url, state = flow.authorization_url()
    
    # Guardamos el state
    session["state"] = state
    # ¡LA LÍNEA MÁGICA QUE FALTABA! Guardamos el code_verifier de esta sesión
    session["code_verifier"] = flow.code_verifier
    
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
            state=session["state"]
        )
        flow.redirect_uri = url_for("callback", _external=True)

        # ¡LA OTRA LÍNEA MÁGICA! Le devolvemos el code_verifier a Google
        flow.fetch_token(
            authorization_response=request.url,
            code_verifier=session.get("code_verifier")
        )

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

        # --- FILTRO DE DOMINIO INSTITUCIONAL ---
        # Solo se permite el acceso con cuentas @ucm.es (coherente con la memoria).
        if not email or not email.lower().endswith("@ucm.es"):
            flash("Acceso restringido a cuentas institucionales (@ucm.es).", "error")
            return redirect(url_for("login"))

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

@app.route("/incidencias", methods=["GET", "POST"])
@login_required
def incidents():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        is_anonymous = request.form.get("anonymous")
        user_id_to_save = None if is_anonymous else current_user.id
        
        nueva_incidencia = Incident(title=title, description=description, user_id=user_id_to_save)
        db.session.add(nueva_incidencia)
        db.session.commit()
        
        flash("Tu incidencia ha sido enviada correctamente al equipo de moderación.", "success")
        return redirect(url_for("incidents"))
        
    mis_incidencias = Incident.query.filter_by(user_id=current_user.id).order_by(Incident.created_at.desc()).all()
    return render_template("incidents.html", incidencias=mis_incidencias)


@app.route("/accesible")
def accessible_mode():
    return render_template("accessible.html")

@app.route("/anuncios")
def ads():
    now = datetime.utcnow()
    anuncios = Announcement.query.filter(Announcement.expires_at >= now).order_by(Announcement.created_at.desc()).all()
    return render_template("ads/ads.html", anuncios=anuncios)

@app.route("/anuncios/nuevo", methods=["GET", "POST"])
@login_required
def ad_create():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        expires_at_str = request.form["expires_at"]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        
        nuevo_anuncio = Announcement(title=title, content=content, expires_at=expires_at, user_id=current_user.id)
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
    
    if current_user.role != 'admin' and current_user.id != anuncio.user_id:
        flash("No tienes permiso para eliminar este anuncio.", "error")
        return redirect(url_for("ads"))
        
    db.session.delete(anuncio)
    db.session.commit()
    flash("Anuncio eliminado.", "success")
    return redirect(url_for("ads"))

@app.route("/moderacion")
@login_required
def moderation_panel():
    if current_user.role != 'admin':
        abort(403)
        
    pendientes_actividades = Activity.query.filter_by(status='pendiente').order_by(Activity.created_at.desc()).all()
    pendientes_anuncios = Announcement.query.filter_by(status='pendiente').order_by(Announcement.created_at.desc()).all()
    pendientes_docs = Document.query.filter_by(status='pendiente').order_by(Document.uploaded_at.desc()).all()
    pendientes_reviews = Review.query.filter_by(status='pendiente').order_by(Review.created_at.desc()).all()
    incidencias_abiertas = Incident.query.filter(Incident.status != 'Cerrada').order_by(Incident.created_at.desc()).all()
    
    return render_template("moderation.html", 
                           actividades=pendientes_actividades, 
                           anuncios=pendientes_anuncios,
                           documentos=pendientes_docs,
                           resenas=pendientes_reviews,
                           incidencias=incidencias_abiertas)


# --- RUTAS DE ACCIÓN DEL PANEL DE MODERACIÓN ---

@app.route("/anuncios/<int:ad_id>/moderar", methods=["POST"])
@login_required
def ad_moderar(ad_id):
    if current_user.role != 'admin': abort(403)
    anuncio = Announcement.query.get_or_404(ad_id)
    accion = request.form.get('accion')
    if accion == 'aprobar':
        anuncio.status = 'aprobado'
        flash(f'Anuncio "{anuncio.title}" aprobado.', 'success')
    elif accion == 'rechazar':
        anuncio.status = 'rechazado'
        flash(f'Anuncio "{anuncio.title}" rechazado.', 'danger')
    db.session.commit()
    return redirect(url_for('moderation_panel'))

@app.route("/documentos/<int:doc_id>/moderar", methods=["POST"])
@login_required
def doc_moderar(doc_id):
    if current_user.role != 'admin': abort(403)
    doc = Document.query.get_or_404(doc_id)
    accion = request.form.get('accion')
    if accion == 'aprobar':
        doc.status = 'aprobado'
        flash(f'Apunte "{doc.title}" aprobado.', 'success')
    elif accion == 'rechazar':
        doc.status = 'rechazado'
        flash(f'Apunte "{doc.title}" rechazado.', 'danger')
    db.session.commit()
    return redirect(url_for('moderation_panel'))

@app.route("/resenas/<int:review_id>/moderar", methods=["POST"])
@login_required
def review_moderar(review_id):
    if current_user.role != 'admin': abort(403)
    review = Review.query.get_or_404(review_id)
    accion = request.form.get('accion')
    if accion == 'aprobar':
        review.status = 'aprobado'
        flash('Reseña aprobada.', 'success')
    elif accion == 'rechazar':
        review.status = 'rechazado'
        flash('Reseña rechazada.', 'danger')
    db.session.commit()
    return redirect(url_for('moderation_panel'))

@app.route("/incidencias/<int:inc_id>/moderar", methods=["POST"])
@login_required
def incident_moderar(inc_id):
    if current_user.role != 'admin': abort(403)
    inc = Incident.query.get_or_404(inc_id)
    accion = request.form.get('accion')
    if accion == 'proceso':
        inc.status = 'En proceso'
        flash('Incidencia marcada como "En proceso".', 'info')
    elif accion == 'cerrar':
        inc.status = 'Cerrada'
        flash('Incidencia cerrada y resuelta.', 'success')
    db.session.commit()
    return redirect(url_for('moderation_panel'))

# --- CONEXIÓN DEL BLUEPRINT DE ASIGNATURAS ---
from routes_subjects import subjects_bp
app.register_blueprint(subjects_bp)

# --- CONEXIÓN DEL BLUEPRINT DE ACTIVIDADES ---
from routes_activities import activities_bp
app.register_blueprint(activities_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)