import os
from app import app
from models import db, Subject, User

def initialize_database():
    # MAGIA: Esto soluciona tu error RuntimeError, le dice a SQLAlchemy qué app usar
    with app.app_context():
        # Crea las tablas si no existen
        db.create_all()

        # --- Asegurar administradores (crea o actualiza contrasena) ---
        admins = {
            "alvago29@ucm.es": "Alvaro",
            "nilope03@ucm.es": "Nicolas",
            "guilgo08@ucm.es": "Guillermo",
        }
        for email, name in admins.items():
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(email=email, name=name, role="admin")
                db.session.add(u)
            u.role = "admin"
            u.set_password("admin1234")
            print("Admin asegurado:", email)
        db.session.commit()
        
        # Comprobamos si ya hay asignaturas
        if Subject.query.count() == 0:
            print("Inyectando el plan de estudios oficial del PDF de la UCM...")
            
            asignaturas_ucm = [
                # --- PRIMER CURSO ---
                Subject(name="Álgebra Lineal", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Cálculo", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de Computadores I", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de Computadores II", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de Electricidad y Electrónica", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de la Programación I", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de la Programación II", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Gestión Empresarial", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Matemática Discreta y Lógica Matemática I", year=1, evaluation_criteria="Pendiente de definir"),
                Subject(name="Matemática Discreta y Lógica Matemática II", year=1, evaluation_criteria="Pendiente de definir"),

                # --- SEGUNDO CURSO ---
                Subject(name="Ampliación de Matemáticas", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Bases de Datos", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Estructura de Computadores", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Estructuras de Datos", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de Algoritmia", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Ingeniería del Software I", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Ingeniería del Software II", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Probabilidad y Estadística", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Tecnología y Organización de Computadores", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Tecnología de la Programación I", year=2, evaluation_criteria="Pendiente de definir"),
                Subject(name="Tecnología de la Programación II", year=2, evaluation_criteria="Pendiente de definir"),

                # --- TERCER CURSO ---
                Subject(name="Redes", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Sistemas Operativos", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Ampliación de Bases de Datos", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Aplicaciones Web", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Auditoría Informática I y II", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Redes y Seguridad I y II", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Software Corporativo", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Fundamentos de los Lenguajes Informáticos", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Inteligencia Artificial I y II", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Programación Concurrente", year=3, evaluation_criteria="Pendiente de definir"),
                Subject(name="Programación Declarativa", year=3, evaluation_criteria="Pendiente de definir"),

                # --- CUARTO CURSO (Obligatorias y Optativas principales) ---
                Subject(name="Ampliación de Sistemas Operativos y Redes", year=4, evaluation_criteria="Pendiente de definir"),
                Subject(name="Arquitectura de Computadores", year=4, evaluation_criteria="Pendiente de definir"),
                Subject(name="Ética, Legislación y Profesión", year=4, evaluation_criteria="Pendiente de definir"),
                Subject(name="Desarrollo de Sistemas Interactivos", year=4, evaluation_criteria="Pendiente de definir"),
                Subject(name="Procesadores de Lenguajes", year=4, evaluation_criteria="Pendiente de definir"),
                Subject(name="Análisis de Redes Sociales", year=4, evaluation_criteria="Optativa"),
                Subject(name="Aprendizaje Automático y Big Data", year=4, evaluation_criteria="Optativa"),
                Subject(name="Arquitectura Interna de Linux y Android", year=4, evaluation_criteria="Optativa"),
                Subject(name="Cloud y Big Data", year=4, evaluation_criteria="Optativa"),
                Subject(name="Creación de Empresas", year=4, evaluation_criteria="Optativa"),
                Subject(name="Criptografía y Teoría de Códigos", year=4, evaluation_criteria="Optativa"),
                Subject(name="Desarrollo de Videojuegos Mediante Tecnologías Web", year=4, evaluation_criteria="Optativa"),
                Subject(name="Ingeniería Web", year=4, evaluation_criteria="Optativa"),
                Subject(name="Robótica", year=4, evaluation_criteria="Optativa"),
                Subject(name="Seguridad en Redes", year=4, evaluation_criteria="Optativa"),
                Subject(name="Testing de Software", year=4, evaluation_criteria="Optativa")
            ]
            
            db.session.bulk_save_objects(asignaturas_ucm)
            db.session.commit()
            print("¡Todas las asignaturas del PDF han sido inyectadas con éxito!")
        else:
            print("Las asignaturas ya estaban en la base de datos.")

if __name__ == "__main__":
    initialize_database()