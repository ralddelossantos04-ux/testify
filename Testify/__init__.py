from flask import Flask

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'delossantos_db',
    'auth_plugin': 'mysql_native_password'
}

def reg_app():
    app = Flask(__name__)

    from Testify.Admin.admin_bp import admin
    from Testify.Authentication.auth_bp import auth
    from Testify.Student.student_bp import student
    from Testify.Teacher.teacher_bp import teacher

    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(student)
    app.register_blueprint(teacher)

    return app  