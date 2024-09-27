from flask import Blueprint, request, jsonify
from app.constants.enums import RequestField
from app.middlewares.validator_middleware import validate_fields
from app.services.on_call_copilot_service import OnCallCopilotService

on_call_copilot = Blueprint("on_call_copilot", __name__)

@on_call_copilot.route("/fetch-details", methods=["GET"])
@validate_fields([(["opportunity_id", "meeting_id"], RequestField.PARAMS)])
def on_call_copilot_route(valid_data):
    return OnCallCopilotService.on_call_copilot(valid_data)
