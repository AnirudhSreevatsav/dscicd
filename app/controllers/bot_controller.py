from flask import Blueprint, request, jsonify, send_file
import os
from app.middlewares.validator_middleware import validate_fields
from app.services.bot_service import BotService
from app.constants.routes_constants import (
    BOT_STATUS,
    START_BOT,
    REMOVE_BOT,
    GET_TRANSCRIPT,
    UPLOAD_TRANSCRIPT,
)
from app.services.threading_service import start_analysis_thread
from app.utils.file_utils import convert_transcript_to_pdf
from app.services.s3_service import S3Service
from app.constants.enums import RequestField


bot_controller = Blueprint("bot_controller", __name__)


@bot_controller.route(START_BOT, methods=["POST"])
def start_bot():
    data = request.get_json()
    meeting_url = data.get("meeting_url")
    bot_name = data.get("bot_name")
    # company_id = data.get("company_id")
    # user_id = data.get("user_id")

    response = BotService.start_bot_service(meeting_url, bot_name)

    # bot_id = "588f5c6a-8ef3-4877-bc9b-d844f2526380"
    # start_analysis_thread(company_id, bot_id, user_id)
    return jsonify(response)


@bot_controller.route(REMOVE_BOT, methods=["POST"])
@validate_fields([(["bot_id"])])
def remove_bot(valid_data):
    return BotService.remove_bot_service(valid_data)


@bot_controller.route(GET_TRANSCRIPT, methods=["POST"])
@validate_fields([(["bot_id"])])
def get_transcript(valid_data):
    return BotService.get_transcript_service(valid_data)


@bot_controller.route(UPLOAD_TRANSCRIPT, methods=["POST"])
@validate_fields([(["bot_id", "company_id"])])
def upload_transcript_to_s3(valid_data):
    return BotService.upload_transcript_service(valid_data)


@bot_controller.route("", methods=["GET"])
def bot_usage():
    return BotService.get_bot_usage_service()


@bot_controller.route(BOT_STATUS, methods=["GET"])
@validate_fields([(["bot_id"], RequestField.PARAMS)])
def bot_status(valid_data):
    return BotService.get_bot_status_service(valid_data)

