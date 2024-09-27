from flask import jsonify
from app.middlewares.socketio import socketio
from app.services.question_service import QuestionService


def init_socketio(app):
    socketio.init_app(app, cors_allowed_origins="*", transport='websocket', polling='true')

    @socketio.on('connect')
    def handle_connect():
        print('Client connected')

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')