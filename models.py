from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Creamos la instancia de la base de datos de forma independiente
db = SQLAlchemy()

# --- TUS MODELOS ORIGINALES ---
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
    
    # --- NUEVA COLUMNA DE MODERACIÓN ---
    status = db.Column(db.String(20), nullable=False, default="pendiente") # pendiente / aprobado / rechazado
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="announcements")
class Incident(db.Model):
    __tablename__ = "incidents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Abierta")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="incidents")

# --- MODELOS DE ASIGNATURAS ---
class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    evaluation_criteria = db.Column(db.Text, nullable=True)
    reviews = db.relationship("Review", backref="subject", lazy=True, cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="subject", lazy=True, cascade="all, delete-orphan")

    @property
    def average_difficulty(self):
        # ¡NUEVO! Solo calculamos la media con las reseñas aprobadas
        aprobadas = [r for r in self.reviews if r.status == 'aprobado']
        if not aprobadas: return 0.0
        total = sum([r.difficulty for r in aprobadas])
        return round(total / len(aprobadas), 1)

class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- COLUMNA DE MODERACIÓN ---
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    user = db.relationship("User", backref="reviews_user")

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    downloads = db.Column(db.Integer, default=0)
    
    # --- COLUMNA DE MODERACIÓN ---
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    user = db.relationship("User", backref="documents_user")

# --- MODELOS DE ACTIVIDADES ---
class Activity(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    capacity = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendiente")  # pendiente / aprobada / rechazada
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="activities")
    registrations = db.relationship("ActivityRegistration", backref="activity", lazy=True, cascade="all, delete-orphan")
    likes = db.relationship("ActivityLike", backref="activity", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("ActivityComment", backref="activity", lazy=True, cascade="all, delete-orphan")

    @property
    def registration_count(self):
        return len(self.registrations)

    @property
    def likes_count(self):
        return len(self.likes)

    @property
    def is_full(self):
        if self.capacity is None:
            return False
        return len(self.registrations) >= self.capacity


class ActivityRegistration(db.Model):
    __tablename__ = "activity_registrations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="activity_registrations")


class ActivityLike(db.Model):
    __tablename__ = "activity_likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    user = db.relationship("User", backref="activity_likes")


class ActivityComment(db.Model):
    __tablename__ = "activity_comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    user = db.relationship("User", backref="activity_comments")
