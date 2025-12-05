from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secreto-tfg"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "tfg.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="estudiante")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
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
    return render_template("incidents.html")

@app.route("/actividades")
def activities():
    return render_template("activities.html")

@app.route("/accesible")
def accessible_mode():
    return render_template("accessible.html")

@app.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form.get("role", "estudiante")

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

def _cleanup_expired_announcements():
    now = datetime.utcnow()
    Announcement.query.filter(Announcement.expires_at < now).delete()
    db.session.commit()

@app.route("/anuncios")
def ads():
    _cleanup_expired_announcements()
    now = datetime.utcnow()
    anuncios = Announcement.query.filter(Announcement.expires_at >= now).order_by(Announcement.created_at.desc()).all()
    return render_template("ads/ads.html", anuncios=anuncios)

@app.route("/anuncios/nuevo", methods=["GET", "POST"])
@login_required
def ad_create():
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        expires_str = request.form["expires_at"]
        if not title or not content or not expires_str:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for("ad_create"))
        try:
            expires_date = datetime.strptime(expires_str, "%Y-%m-%d")
            expires_at = datetime(expires_date.year, expires_date.month, expires_date.day, 23, 59, 59)
        except ValueError:
            flash("Formato de fecha de caducidad no válido.", "error")
            return redirect(url_for("ad_create"))

        anuncio = Announcement(title=title, content=content, expires_at=expires_at, user_id=current_user.id)
        db.session.add(anuncio)
        db.session.commit()
        flash("Anuncio creado correctamente.", "success")
        return redirect(url_for("ads"))
    return render_template("ads/ad_form.html", mode="crear")

@app.route("/anuncios/<int:ad_id>")
def ad_detail(ad_id):
    _cleanup_expired_announcements()
    anuncio = Announcement.query.get_or_404(ad_id)
    if anuncio.expires_at < datetime.utcnow():
        db.session.delete(anuncio)
        db.session.commit()
        abort(404)
    return render_template("ads/ad_detail.html", anuncio=anuncio)

@app.route("/anuncios/<int:ad_id>/editar", methods=["GET", "POST"])
@login_required
def ad_edit(ad_id):
    anuncio = Announcement.query.get_or_404(ad_id)
    if current_user.role != "admin" and anuncio.user_id != current_user.id:
        flash("No puedes editar este anuncio.", "error")
        return redirect(url_for("ads"))

    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        expires_str = request.form["expires_at"]
        if not title or not content or not expires_str:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for("ad_edit", ad_id=ad_id))
        try:
            expires_date = datetime.strptime(expires_str, "%Y-%m-%d")
            anuncio.expires_at = datetime(expires_date.year, expires_date.month, expires_date.day, 23, 59, 59)
        except ValueError:
            flash("Formato de fecha de caducidad no válido.", "error")
            return redirect(url_for("ad_edit", ad_id=ad_id))

        anuncio.title = title
        anuncio.content = content
        db.session.commit()
        flash("Anuncio actualizado correctamente.", "success")
        return redirect(url_for("ads"))
    return render_template("ads/ad_form.html", mode="editar", anuncio=anuncio)

@app.route("/anuncios/<int:ad_id>/eliminar", methods=["POST"])
@login_required
def ad_delete(ad_id):
    anuncio = Announcement.query.get_or_404(ad_id)
    if current_user.role != "admin" and anuncio.user_id != current_user.id:
        flash("No puedes eliminar este anuncio.", "error")
        return redirect(url_for("ads"))
    db.session.delete(anuncio)
    db.session.commit()
    flash("Anuncio eliminado correctamente.", "info")
    return redirect(url_for("ads"))

@app.route("/admin/panel")
@login_required
def admin_panel():
    if current_user.role != "admin":
        flash("No tienes permiso para acceder a esta sección.", "error")
        return redirect(url_for("home"))
    return render_template("admin_panel.html")

if __name__ == "__main__":
    app.run(debug=True)