#controller for postcall
from flask import Blueprint, request, jsonify
from app.constants.enums import RequestField
from app.middlewares.validator_middleware import validate_fields
from app.services.postcall_service import PostCallService
from app.utils.response_util import api_response

postcall_bp = Blueprint('postcall', __name__)

@postcall_bp.route('/post-call-analysis', methods=['POST'])
@validate_fields([(["opportunity_id", "meeting_id"])])
def post_call_analysis(valid_data):
    return PostCallService.post_call_analysis(valid_data)

@postcall_bp.route('/update-lead-qualification',methods=['POST'])
@validate_fields([(["opportunity_id","is_lead_qualified"])])
def update_lead_qualification(valid_data):
    return PostCallService.update_lead_qualification(valid_data)