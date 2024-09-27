from app import create_app
from app.middlewares.socketio import socketio

if __name__ == '__main__':
    app = create_app()
    # app.run(host='0.0.0.0', port=8000)
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)

