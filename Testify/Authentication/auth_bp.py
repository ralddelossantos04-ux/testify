from flask import Blueprint, render_template, request

auth = Blueprint('auth', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/auth/static')

@auth.route('/index')
def index():
    return render_template('index.html')

@auth.route("/login")
def login():
    role = request.args.get("role", default="STUDENT")
    return render_template("login.html", role=role)

@auth.route("/select-role")
def select_role():
    return render_template("index.html")