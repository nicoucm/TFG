from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from models import db, Activity, ActivityRegistration, ActivityLike, ActivityComment
from datetime import datetime
import os
from werkzeug.utils import secure_filename

activities_bp = Blueprint('activities', __name__)

UPLOAD_FOLDER_ACTIVITIES = 'static/uploads/activities'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- LISTADO DE ACTIVIDADES ---
@activities_bp.route('/actividades')
@login_required
def activities_list():
    activities = Activity.query.filter_by(status='aprobada').order_by(Activity.date.asc()).all()
    return render_template('activities.html', activities=activities)


# --- DETALLE DE UNA ACTIVIDAD ---
@activities_bp.route('/actividades/<int:activity_id>')
@login_required
def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    ya_inscrito = ActivityRegistration.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()
    ya_like = ActivityLike.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()
    return render_template('activities/activity_detail.html', activity=activity, ya_inscrito=ya_inscrito, ya_like=ya_like)


# --- CREAR ACTIVIDAD ---
@activities_bp.route('/actividades/crear', methods=['GET', 'POST'])
@login_required
def activity_create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date_str = request.form['date']
        location = request.form['location']
        capacity = request.form.get('capacity', None)

        date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        capacity = int(capacity) if capacity else None

        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER_ACTIVITIES, exist_ok=True)
                filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(UPLOAD_FOLDER_ACTIVITIES, filename))
                image_filename = filename

        new_activity = Activity(
            title=title,
            description=description,
            date=date,
            location=location,
            capacity=capacity,
            image_filename=image_filename,
            status='aprobada',
            user_id=current_user.id
        )
        db.session.add(new_activity)
        db.session.commit()
        flash('Actividad enviada para aprobación. El administrador la revisará pronto.', 'success')
        return redirect(url_for('activities.activities_list'))

    return render_template('activities/activity_create.html')


# --- INSCRIBIRSE / DESINSCRIBIRSE ---
@activities_bp.route('/actividades/<int:activity_id>/inscribirse', methods=['POST'])
@login_required
def activity_register(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    ya_inscrito = ActivityRegistration.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()

    if ya_inscrito:
        db.session.delete(ya_inscrito)
        db.session.commit()
        flash('Te has desinscrito de la actividad.', 'info')
    else:
        if activity.is_full:
            flash('Lo sentimos, esta actividad ya no tiene plazas disponibles.', 'danger')
        else:
            db.session.add(ActivityRegistration(user_id=current_user.id, activity_id=activity_id))
            db.session.commit()
            flash('¡Te has inscrito correctamente!', 'success')

    return redirect(url_for('activities.activity_detail', activity_id=activity_id))


# --- LIKE / UNLIKE ---
@activities_bp.route('/actividades/<int:activity_id>/like', methods=['POST'])
@login_required
def activity_like(activity_id):
    ya_like = ActivityLike.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()

    if ya_like:
        db.session.delete(ya_like)
    else:
        db.session.add(ActivityLike(user_id=current_user.id, activity_id=activity_id))

    db.session.commit()
    return redirect(url_for('activities.activity_detail', activity_id=activity_id))


# --- COMENTAR ---
@activities_bp.route('/actividades/<int:activity_id>/comentar', methods=['POST'])
@login_required
def activity_comment(activity_id):
    content = request.form.get('content', '').strip()
    if content:
        db.session.add(ActivityComment(content=content, user_id=current_user.id, activity_id=activity_id))
        db.session.commit()
        flash('Comentario añadido.', 'success')
    return redirect(url_for('activities.activity_detail', activity_id=activity_id))


# --- PANEL ADMIN ---
@activities_bp.route('/actividades/admin')
@login_required
def activity_admin():
    if current_user.role != 'admin':
        flash('No tienes permiso para acceder aquí.', 'danger')
        return redirect(url_for('activities.activities_list'))
    pendientes = Activity.query.filter_by(status='pendiente').order_by(Activity.created_at.desc()).all()
    return render_template('activity_admin.html', pendientes=pendientes)


# --- APROBAR / RECHAZAR ---
@activities_bp.route('/actividades/<int:activity_id>/moderar', methods=['POST'])
@login_required
def activity_moderar(activity_id):
    if current_user.role != 'admin':
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('activities.activities_list'))

    activity = Activity.query.get_or_404(activity_id)
    accion = request.form.get('accion')

    if accion == 'aprobar':
        activity.status = 'aprobada'
        flash(f'Actividad "{activity.title}" aprobada.', 'success')
    elif accion == 'rechazar':
        activity.status = 'rechazada'
        flash(f'Actividad "{activity.title}" rechazada.', 'danger')

    db.session.commit()
    return redirect(url_for('activities.activity_admin'))

# --- EDITAR ACTIVIDAD ---
@activities_bp.route('/actividades/<int:activity_id>/editar', methods=['GET', 'POST'])
@login_required
def activity_edit(activity_id):
    activity = Activity.query.get_or_404(activity_id)

    if current_user.id != activity.user_id and current_user.role != 'admin':
        flash('No tienes permiso para editar esta actividad.', 'danger')
        return redirect(url_for('activities.activity_detail', activity_id=activity_id))

    if request.method == 'POST':
        activity.title = request.form['title']
        activity.description = request.form['description']
        activity.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        activity.location = request.form['location']
        capacity = request.form.get('capacity')
        activity.capacity = int(capacity) if capacity else None

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER_ACTIVITIES, exist_ok=True)
                filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(UPLOAD_FOLDER_ACTIVITIES, filename))
                activity.image_filename = filename

        db.session.commit()
        flash('Actividad actualizada correctamente.', 'success')
        return redirect(url_for('activities.activity_detail', activity_id=activity_id))

    return render_template('activities/activity_edit.html', activity=activity)
