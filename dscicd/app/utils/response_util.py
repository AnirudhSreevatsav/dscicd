from flask import jsonify
import datetime
from http import HTTPStatus
from typing import Any


def api_response(status_code: int, message: str = None, data: Any = None):
    status_phrase = HTTPStatus(status_code).phrase

    response = {
        "status": status_phrase,
        "status_code": status_code,
        "message": message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if data:
        response["data"] = data

    return jsonify(response), status_code
