from flask import Flask, jsonify
from flask_cors import CORS
import requests

# from flask_cors import CORS
from app.utils.socket_events import init_socketio
from app.utils.mongo_change_stream import start_change_stream


def create_app():
    # Initialize Flask app
    app = Flask(__name__)

    # Enable CORS for all domains on all routes
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Initialize SocketIO with the app
    init_socketio(app)

    # Start the change stream thread
    start_change_stream()

    # Register blueprints (controllers)
    from app.controllers.bot_controller import bot_controller

    app.register_blueprint(bot_controller, url_prefix="/api/bot")

    from app.controllers.question_controller import question_controller

    app.register_blueprint(question_controller, url_prefix="/api/questions")

    from app.controllers.s3_controller import s3_controller

    app.register_blueprint(s3_controller, url_prefix="/api/s3")

    from app.controllers.ml_controller import ml_controller

    app.register_blueprint(ml_controller, url_prefix="/api/ml")

    from app.controllers.opportunities_controller import opportunity_controller

    app.register_blueprint(opportunity_controller, url_prefix="/api/opportunity")


    from app.controllers.postcall_controller import postcall_bp

    app.register_blueprint(postcall_bp, url_prefix="/api/postcall")


    from app.controllers.on_call_controller import on_call_controller

    app.register_blueprint(on_call_controller, url_prefix="/api/on-call")

    from app.controllers.on_call_copilot import on_call_copilot

    app.register_blueprint(on_call_copilot, url_prefix="/api/on-call-copilot")


    @app.route("/")
    def root():
        return jsonify(message="Welcome to Pepsales Team!")
    

    @app.route('/check-ml-copilot', methods=['GET'])
    def check_ml_copilot():
        response = requests.get('http://ml_service_container:5000/')
        return jsonify({"status": response.text}), response.status_code

    return app
