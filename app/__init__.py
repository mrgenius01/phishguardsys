from flask import Flask, render_template
from flask_mysqldb import MySQL
from flask_cors import CORS

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app)
    mysql.init_app(app)

    from .routes.main_routes import main
    app.register_blueprint(main)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app
