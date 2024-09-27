import os
from bson import ObjectId
import requests
from app.constants.config import RECALL_API_KEY
from app.constants.constants import OPPORTUNITIES_COLLECTION
from app.services.s3_service import S3Service
from app.utils.file_utils import convert_transcript_to_pdf
from app.utils.logging import setup_logging
from app.utils.transcript_utils import group_transcript_by_speaker
from app.constants.recall_constants import RECALL_AI_BASE_URL, TRANSCRIPT, LEAVE_CALL
from app.utils.response_util import api_response
from flask import request
from app.utils.mongo_util import mongo_util
from app.constants.response_constants import (
    BOT_REMOVED,
    BOT_STARTED,
    BOT_STATUS_ERROR,
    BOT_STATUS_RETRIEVED,
    BOT_USAGE_ERROR,
    BOT_USAGE_RETRIEVED,
    PDF_CONVERSION_ERROR,
    PDF_UPLOAD_ERROR,
    REMOVE_BOT_ERROR,
    TRANSCRIPT_RETRIEVED,
    START_BOT_ERROR,
    TRANSCRIPT_ERROR,
    TRANSCRIPT_UPLOADED,
)

logger = setup_logging()


class BaseService:
    @staticmethod
    def get_headers(content_type="application/json"):
        return {
            "Authorization": RECALL_API_KEY,
            "accept": "application/json",
            "content-type": content_type,
        }


class BotService(BaseService):

    @staticmethod
    def start_bot_service(meeting_url, bot_name):
        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "transcription_options": {"provider": "meeting_captions"},
        }
        try:
            response = requests.post(
                RECALL_AI_BASE_URL, headers=BotService.get_headers(), json=payload
            )
            response.raise_for_status()
            response_data = response.json()
            return api_response(
                status_code=response.status_code,
                message=BOT_STARTED,
                data=response_data,
            )
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            return api_response(
                status_code=response.status_code, message=f"{START_BOT_ERROR}: {str(e)}"
            )

    @staticmethod
    def remove_bot_service(data):
        bot_id = data.get("bot_id")
        remove_bot_url = f"{RECALL_AI_BASE_URL}{bot_id}{LEAVE_CALL}"
        try:
            response = requests.post(
                remove_bot_url, headers=BotService.get_headers())
            response.raise_for_status()
            return api_response(
                status_code=response.status_code,
                message=BOT_REMOVED,
                data={"bot_id": bot_id},
            )
        except Exception as e:
            logger.error(f"Failed to remove bot: {str(e)}")
            return api_response(
                status_code=response.status_code,
                message=f"{REMOVE_BOT_ERROR}: {str(e)}",
            )

    @staticmethod
    def get_transcript_service(data):

        if request.get_json().get("is_dev"):

            opportunity_id = request.get_json().get("opportunity_id")
            meeting_id = request.get_json().get("meeting_id")

            if not opportunity_id or not meeting_id:
                return api_response(status_code=400, message="Opportunity id and meeting id are required")

            opportunity_object_id = ObjectId(opportunity_id)
            meeting_object_id = ObjectId(meeting_id)

            result = mongo_util.find_one(
                OPPORTUNITIES_COLLECTION,
                {
                    "_id": opportunity_object_id,
                    "meetings": {
                        "$elemMatch": {
                            "_id": meeting_object_id
                        }
                    }
                },
                {"meetings.$": 1}
            )

            if not result:
                return api_response(status_code=404, message="Opportunity or meeting not found")

            meeting = result.get("meetings")[0] if result.get(
                "meetings") else None
            if not meeting:
                return api_response(status_code=404, message="Meeting not found")

            transcript = meeting.get("transcript")
            return api_response(status_code=200, message=TRANSCRIPT_RETRIEVED, data={"transcript": transcript})

        bot_id = data.get("bot_id")
        transcript_url = f"{RECALL_AI_BASE_URL}{bot_id}{TRANSCRIPT}"
        try:
            response = requests.get(
                transcript_url, headers=BotService.get_headers())
            response.raise_for_status()
            transcript_data = response.json()
            grouped_transcript = group_transcript_by_speaker(transcript_data)
            return api_response(
                status_code=200,
                message=TRANSCRIPT_RETRIEVED,
                data={"transcript": grouped_transcript},
            )
        except Exception as e:
            logger.error(f"Failed to retrieve the transcript: {str(e)}")
            return api_response(
                status_code=500,
                message=f"{TRANSCRIPT_ERROR}: {str(e)}",
            )

    @staticmethod
    def upload_transcript_service(data):

        bot_id = data.get("bot_id")
        company_id = data.get("company_id")
        try:
            response, status_code = BotService.get_transcript_service(data)
            if status_code != 200:
                return response
            transcript = response["data"]["transcript"]
            pdf_path = convert_transcript_to_pdf(
                transcript, bot_id, company_id)
            if not os.path.exists(pdf_path):
                return api_response(status_code=404, message=PDF_CONVERSION_ERROR)
            s3_url = S3Service.upload_pdf_to_s3(pdf_path, company_id)

            os.remove(pdf_path)

            return api_response(
                status_code=200,
                message=TRANSCRIPT_UPLOADED,
                data={"s3_url": s3_url},
            )

        except Exception as e:
            logger.error(f"Error in upload_transcript_to_s3_service: {str(e)}")
            return api_response(
                status_code=500,
                message=f"{PDF_UPLOAD_ERROR}: {str(e)}",
            )

    @staticmethod
    def get_bot_usage_service():
        bot_usage_url = RECALL_AI_BASE_URL
        try:
            response = requests.get(
                bot_usage_url, headers=BotService.get_headers())
            response.raise_for_status()
            return api_response(
                status_code=response.status_code,
                message=BOT_USAGE_RETRIEVED,
                data=response.json(),
            )
        except Exception as e:
            logger.error(f"Failed to retrieve bot usage: {str(e)}")
            return api_response(
                status_code=response.status_code,
                message=f"{BOT_USAGE_ERROR}: {str(e)}",
            )

    @staticmethod
    def get_bot_status_service(data):
        bot_id = data.get("bot_id")
        bot_status_url = f"{RECALL_AI_BASE_URL}{bot_id}"
        try:
            response = requests.get(
                bot_status_url, headers=BotService.get_headers())
            response.raise_for_status()
            status_data = response.json().get("status_changes", [])
            last_code = status_data[-1]["code"] if status_data else None
            all_codes = [change["code"] for change in status_data]

            return api_response(
                status_code=response.status_code,
                message=BOT_STATUS_RETRIEVED,
                data={
                    "bot_id": bot_id,
                    "current_status": last_code,
                    "status_codes": all_codes,
                },
            )
        except Exception as e:
            logger.error(f"Failed to retrieve bot status: {str(e)}")
            return api_response(
                status_code=response.status_code,
                message=f"{BOT_STATUS_ERROR}: {str(e)}",
            )
