from venv import logger
import requests
from app.constants.routes_constants import LOCAL_BASE_URL
from app.utils.response_util import api_response


class OnCallCopilotService:

    @staticmethod
    def on_call_copilot(data):
        #  this will send the all the non-answered questions, meeting details to the on call screen

        opportunity_id = data.get("opportunity_id")
        meeting_id = data.get("meeting_id")

        #  get the opportunity details
        opportunity_details = OnCallCopilotService.get_opportunity_details(
            opportunity_id, meeting_id)

        # if none, return
        if not opportunity_details:
            return api_response(status_code=404, message="Opportunity details not found")

        opportunity_details = opportunity_details.get("data")

        if not opportunity_details:
            return api_response(status_code=404, message="Opportunity details not found")

        meeting_details = opportunity_details.get("meeting")

        if not meeting_details:
            return api_response(status_code=404, message="Meeting details not found")
        
        current_question_id = opportunity_details.get("transactional_discovery_questions").get("current_question_id")

        non_answered_questions = [question for question in opportunity_details.get("transactional_discovery_questions").get("questions") if not question.get("is_answered") ]

        on_call_data = {
            "opportunity_id": opportunity_id,
            "meeting_id": meeting_id,
            "opportunity_name": opportunity_details.get("name"),
            "current_question_id": current_question_id,
            "meeting_details": {
                "agenda": meeting_details.get("agenda"),
                "participants": meeting_details.get("participants"),
                "start_meet" : meeting_details.get("start_meet"),
                "end_meet" : meeting_details.get("end_meet")
            },
            "questions": non_answered_questions
        }

        return api_response(status_code=200, message="On call copilot data fetched successfully", data=on_call_data)
    @staticmethod
    def get_opportunity_details(opportunity_id, meeting_id):
        try:
            url = f"{LOCAL_BASE_URL}/api/opportunity/fetch-opportunity-by-meeting-id?opportunity_id={opportunity_id}&meeting_id={meeting_id}"

            with requests.Session() as session:
                response = session.get(url)

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching opportunity details: {e}")
            return None
