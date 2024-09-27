from flask import Blueprint
from app.middlewares.validator_middleware import validate_fields
from app.constants.enums import RequestField
from app.constants.routes_constants import EDIT_OPPORTUNITY, EDIT_MEETING_DETAILS, DISCOVERY_DETAILS, FETCH_OPPORTUNITIES_BY_USER_ID, FETCH_OPPORTUNITY, FETCH_OPPORTUNITY_BY_MEETING_ID, SCHEDULE_MEETING, CREATE_OPPORTUNITY, SEARCH_OPPORTUNITIES, ADD_TRANSCRIPT_TO_MEETING
from app.services.opportunities_service import OpportunitiesService

opportunity_controller = Blueprint("opportunity_controller", __name__)


@opportunity_controller.route(FETCH_OPPORTUNITY_BY_MEETING_ID, methods=['GET'])
@validate_fields([(["opportunity_id", "meeting_id"], RequestField.PARAMS)])
def fetch_opportunity_by_meeting_id(valid_data):
    return OpportunitiesService.get_opportunity_by_meeting_id(valid_data)

@opportunity_controller.route(FETCH_OPPORTUNITY, methods=['GET'])
@validate_fields([(["opportunity_id"], RequestField.PARAMS)])
def fetch_opportunity(valid_data):
    return OpportunitiesService.get_opportunity_by_id(valid_data)


@opportunity_controller.route(SCHEDULE_MEETING, methods=["POST"])
@validate_fields([(["opportunity_id"], RequestField.PARAMS), (["meeting_details"])])
def add_meeting(valid_data):
    return OpportunitiesService.add_meeting_to_opportunity(valid_data)


@opportunity_controller.route(CREATE_OPPORTUNITY, methods=["POST"])
@validate_fields([(["name", "seller_company_id", "user_id"])])
def create_opportunity(valid_data):
    return OpportunitiesService.create_opportunity(valid_data)


@opportunity_controller.route(FETCH_OPPORTUNITIES_BY_USER_ID, methods=['GET'])
@validate_fields([(["user_id"], RequestField.PARAMS)])
def fetch_opportunities_by_user_id(valid_data):
    return OpportunitiesService.fetch_opportunity_by_user_id(valid_data)


@opportunity_controller.route(EDIT_MEETING_DETAILS, methods=["POST"])
@validate_fields([(["opportunity_id", "meeting_id"], RequestField.PARAMS)])
def edit_meeting_in_opportunity(valid_data):
    return OpportunitiesService.edit_meeting_in_opportunity(valid_data)


@opportunity_controller.route(SEARCH_OPPORTUNITIES, methods=['POST'])
@validate_fields([(["name_snippet"])])
def search_opportunities(valid_data):
    return OpportunitiesService.search_opportunities(valid_data)


@opportunity_controller.route(DISCOVERY_DETAILS, methods=['GET'])
@validate_fields([(["user_id"], RequestField.PARAMS)])
def discovery_details(valid_data):
    return OpportunitiesService.discovery_details(valid_data)


@opportunity_controller.route(EDIT_OPPORTUNITY, methods=["POST"])
@validate_fields([(["opportunity_id"], RequestField.PARAMS), (["opportunity_details"])])
def edit_opportunity(valid_data):
    return OpportunitiesService.edit_opportunity(valid_data)

@opportunity_controller.route(ADD_TRANSCRIPT_TO_MEETING, methods=["POST"])
@validate_fields([(["opportunity_id", "meeting_id", "transcript"])])
def add_transcript_to_meeting(valid_data):
    return OpportunitiesService.add_transcript_to_meeting(valid_data)