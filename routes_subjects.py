import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

# IMPORTAMOS DESDE EL NUEVO ARCHIVO models.py (¡Se acabaron los clones!)
from models import db, Subject, Review, Document

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route("/asignaturas")
@login_required
def list_subjects():
    subjects_by_year = {
        1: Subject.query.filter_by(year=1).all(),
        2: Subject.query.filter_by(year=2).all(),
        3: Subject.query.filter_by(year=3).all(),
        4: Subject.query.filter_by(year=4).all(),
    }
    return render_template("subjects/list.html", subjects_by_year=subjects_by_year)

@subjects_bp.route("/asignatura/<int:subject_id>")
@login_required
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    return render_template("subjects/detail.html", subject=subject)

@subjects_bp.route("/asignatura/<int:subject_id>/review", methods=["POST"])
@login_required
def add_review(subject_id):
    # AHORA ACEPTA QUE ESTÉ VACÍO, PONIENDO "" POR DEFECTO Y ELIMINANDO ESPACIOS
    content = request.form.get("content", "").strip()
    difficulty = int(request.form.get("difficulty"))
    
    nueva_resena = Review(content=content, difficulty=difficulty, user_id=current_user.id, subject_id=subject_id)
    db.session.add(nueva_resena)
    db.session.commit()
    flash("¡Valoración publicada correctamente!", "success")
    return redirect(url_for("subjects.subject_detail", subject_id=subject_id))

@subjects_bp.route("/asignatura/<int:subject_id>/upload", methods=["POST"])
@login_required
def upload_document(subject_id):
    if 'file' not in request.files:
        flash("No se seleccionó ningún archivo", "error")
        return redirect(url_for("subjects.subject_detail", subject_id=subject_id))
    
    file = request.files['file']
    title = request.form.get("title")
    
    if file.filename != '':
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        upload_path = os.path.join(current_app.root_path, 'uploads')
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            
        file.save(os.path.join(upload_path, unique_filename))
        
        nuevo_doc = Document(title=title, filename=unique_filename, user_id=current_user.id, subject_id=subject_id)
        db.session.add(nuevo_doc)
        db.session.commit()
        flash("Apunte subido correctamente. ¡Gracias por aportar a la comunidad!", "success")
        
    return redirect(url_for("subjects.subject_detail", subject_id=subject_id))

@subjects_bp.route("/descargar/<int:doc_id>")
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    doc.downloads += 1
    db.session.commit()
    
    upload_path = os.path.join(current_app.root_path, 'uploads')
    return send_from_directory(upload_path, doc.filename, as_attachment=True)