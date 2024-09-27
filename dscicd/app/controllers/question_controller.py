from flask import Blueprint, request
from app.middlewares.validator_middleware import validate_fields
from app.services.question_service import QuestionService
from app.utils.logging import setup_logging
from app.constants.routes_constants import (
    FETCH_QUESTIONS,
    UPDATE_QUESTIONS,
    SHUFFLE_QUESTIONS,
    ADD_QUESTION,
    MASTER_FETCH_QUESTIONS,
    MASTER_UPDATE_QUESTIONS,

)
from app.constants.enums import RequestField

logger = setup_logging()

question_controller = Blueprint("question_controller", __name__)


@question_controller.route(FETCH_QUESTIONS, methods=["GET"])
@validate_fields([(["transaction_id"], RequestField.PARAMS)])
def fetch_questions(valid_data):
    return QuestionService.fetch_all_transact_questions(valid_data)


@question_controller.route(UPDATE_QUESTIONS, methods=["POST"])
@validate_fields([(["transaction_id"], RequestField.PARAMS)])
def update_question_data(valid_data):
    return QuestionService.update_question_data(valid_data)


@question_controller.route(SHUFFLE_QUESTIONS, methods=["POST"])
@validate_fields([(["transaction_id"], RequestField.PARAMS), (["initial_index", "final_index"])])
def shuffle_questions(valid_data):
    return QuestionService.shuffle_questions(valid_data)


@question_controller.route(ADD_QUESTION, methods=["POST"])
@validate_fields([(["transaction_id"], RequestField.PARAMS), (["question"])])
def add_question(valid_data):
    return QuestionService.add_question(valid_data)


@question_controller.route(MASTER_FETCH_QUESTIONS, methods=["GET"])
@validate_fields([(["company_id"], RequestField.PARAMS)])
def fetch_master_questions(valid_data):
    return QuestionService.fetch_master_questions(valid_data)


@question_controller.route(MASTER_UPDATE_QUESTIONS, methods=["POST"])
@validate_fields([(["company_id"], RequestField.PARAMS), (["questions", "last_processed_pdf_time"])])
def update_master_questions(valid_data):
    return QuestionService.update_master_questions(valid_data)
