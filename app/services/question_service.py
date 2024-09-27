from bson.objectid import ObjectId
from app.constants.constants import (
    MASTER_QUESTIONS_COLLECTION,
    TRANSACT_QUESTIONS_COLLECTION,
)
from app.services.ml_service import MLService
from app.utils.response_util import api_response
from app.utils.mongo_util import mongo_util
from app.utils.logging import setup_logging
from flask import request
from app.constants.response_constants import (
    SUCCESSFUL_FETCH,
    NO_QUESTIONS,
    FETCH_ERROR,
    UPDATE_ERROR,
)

logger = setup_logging()


class BaseService:
    @staticmethod
    def convert_objectid_to_str(document):
        if isinstance(document, dict):
            for key, value in document.items():
                if isinstance(value, ObjectId):
                    document[key] = str(value)
        return document


class QuestionService(BaseService):
    @staticmethod
    def fetch_all_transact_questions(data):
        try:
            transaction_id = data.get("transaction_id")
            transaction_id = ObjectId(transaction_id)

            transaction_record = mongo_util.find_one(
                TRANSACT_QUESTIONS_COLLECTION,
                {"_id": transaction_id},
            )

            if transaction_record:
                transaction_record = QuestionService.convert_objectid_to_str(
                    transaction_record
                )
                return api_response(
                    status_code=200,
                    message=SUCCESSFUL_FETCH,
                    data=transaction_record,
                )
            return api_response(
                status_code=404,
                message=NO_QUESTIONS,
            )

        except Exception as e:
            logger.error(
                f"Error fetching questions for transaction ID {transaction_id}: {e}"
            )
            return api_response(
                status_code=500,
                message=f"{FETCH_ERROR}: {str(e)}",
            )

    @staticmethod
    def update_question_data(data):
        try:
            transaction_id = data.get("transaction_id")
            current_question_id = request.json.get("current_question_id")
            question_id = request.json.get("question_id")
            answer = request.json.get("answer")
            follow_up = request.json.get("follow_up")
            is_answered = request.json.get("is_answered")
            analysis = request.json.get("analysis")
            whom_to_ask = request.json.get("whom_to_ask")
            question = request.json.get("question")
            blockers = request.json.get("blockers")
            question_type = request.json.get("question_type")
            answer_verbatim = request.json.get("answer_verbatim")
            objection = request.json.get("objection")

            update_operations = {}

            if not current_question_id and not question_id:
                return api_response(
                    status_code=400,
                    message="current_question_id or question_id required",
                )

            # Case 1: if current_question_id is given
            if current_question_id:
                if "$set" not in update_operations:
                    update_operations["$set"] = {}
                update_operations["$set"]["current_question_id"] = current_question_id

            # If question_id is provided
            if question_id:
                if "$set" not in update_operations:
                    update_operations["$set"] = {}

                # Case 2: if answer is given
                if answer is not None:
                    update_operations["$set"]["questions.$.answer"] = answer

                # Case 3: if is_answered is given
                if is_answered is not None:
                    update_operations["$set"]["questions.$.is_answered"] = is_answered

                # Case 4: if analysis is given
                if analysis:
                    update_operations["$set"]["questions.$.analysis"] = analysis

                # Case 5: if whom_to_ask is given
                if whom_to_ask is not None:
                    update_operations["$set"]["questions.$.whom_to_ask"] = whom_to_ask

                # Case 6: if follow_up is given
                if follow_up is not None:
                    update_operations["$set"]["questions.$.follow_up"] = follow_up

                # Case 7: if question is given
                if question is not None:
                    update_operations["$set"]["questions.$.question"] = question

                # Case 8: if question_type is given
                if question_type is not None:
                    update_operations["$set"][
                        "questions.$.question_type"
                    ] = question_type
                if objection is not None:
                    update_operations["$set"]["questions.$.objection"] = objection

                # Case 9: if blockers is given
                if blockers is not None:
                    update_operations["$set"]["questions.$.blockers"] = blockers
                # Case 10: if verbatim is given

                if answer_verbatim is not None:
                    update_operations["$set"][
                        "questions.$.answer_verbatim"
                    ] = answer_verbatim

            if not update_operations:
                return api_response(status_code=400, message="No fields to update")

            if question_id:
                query = {
                    "_id": ObjectId(transaction_id),
                    "questions.question_id": question_id,
                }
            else:
                query = {"_id": ObjectId(transaction_id)}

            result = mongo_util.update_one(
                TRANSACT_QUESTIONS_COLLECTION,
                query,
                update_operations,
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200, message="Document updated", data=update_operations
                )
            else:
                return api_response(status_code=404, message="No document was updated")

        except Exception as e:
            logger.error(
                f"Error updating question data for transaction ID {transaction_id}: {e}"
            )
            return api_response(status_code=500, message=f"{UPDATE_ERROR}: {str(e)}")

    @staticmethod
    def shuffle_questions(data):
        try:
            transaction_id = data.get("transaction_id")
            initial_index = data.get("initial_index")
            final_index = data.get("final_index")

            if initial_index is None or final_index is None:
                return api_response(
                    status_code=400, message="initial_index and final_index required"
                )

            if initial_index == final_index:
                return api_response(
                    status_code=400,
                    message="initial_index and final_index should be different",
                )

            if initial_index < 0 or final_index < 0:
                return api_response(
                    status_code=400,
                    message="initial_index and final_index should be positive",
                )

            transactional_data = mongo_util.find_one(
                TRANSACT_QUESTIONS_COLLECTION, {"_id": ObjectId(transaction_id)}
            )

            if not transactional_data:
                return api_response(status_code=404, message="No transaction found")

            questions = transactional_data.get("questions")
            if not questions:
                return api_response(status_code=404, message="No questions found")

            if initial_index >= len(questions) or final_index >= len(questions):
                return api_response(
                    status_code=400,
                    message="initial_index and final_index should be within the range of questions",
                )

            #  insert the question at final_index from initial_index
            question_to_move = questions.pop(initial_index)
            questions.insert(final_index, question_to_move)

            result = mongo_util.update_one(
                TRANSACT_QUESTIONS_COLLECTION,
                {"_id": ObjectId(transaction_id)},
                {"$set": {"questions": questions}},
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200, message="Questions shuffled successfully"
                )
            else:
                return api_response(
                    status_code=404, message="No questions were shuffled"
                )

        except Exception as e:
            logger.error(
                f"Error shuffling questions for transaction ID {transaction_id}: {e}"
            )
            return api_response(status_code=500, message=f"An error occurred: {str(e)}")

    @staticmethod
    def add_question(data):
        try:
            transaction_id = data.get("transaction_id")
            question_data = data.get("question")

            if not question_data:
                return api_response(status_code=400, message="question required")

            question_id = str(ObjectId())
            question = question_data.get("question")
            whom_to_ask = question_data.get("whom_to_ask")
            time = question_data.get("time")
            question_type = question_data.get("question_type")

            new_question = {
                "question_id": question_id,
                "question": question,
                "is_answered": False,
                "is_deleted": False,
                "whom_to_ask": whom_to_ask,
                "time": time,
                "question_type": question_type,
            }

            result = mongo_util.update_one(
                TRANSACT_QUESTIONS_COLLECTION,
                {"_id": ObjectId(transaction_id)},
                {"$push": {"questions": new_question}},
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200,
                    message="Question added successfully",
                    data=QuestionService.convert_objectid_to_str(new_question),
                )
            else:
                return api_response(status_code=404, message="No question was added")

        except Exception as e:
            logger.error(
                f"Error adding question for transaction ID {transaction_id}: {e}"
            )
            return api_response(status_code=500, message=f"An error occurred: {str(e)}")

    @staticmethod
    def fetch_master_questions(data):
        try:
            company_id = data.get("company_id")
            question_data = mongo_util.find_one(
                MASTER_QUESTIONS_COLLECTION, {"company_id": company_id}
            )
            if question_data:
                question_data = QuestionService.convert_objectid_to_str(question_data)
                return api_response(
                    status_code=200, message=SUCCESSFUL_FETCH, data=question_data
                )

            return api_response(status_code=404, message=NO_QUESTIONS)

        except Exception as e:
            logger.error(f"Error fetching questions for company ID {company_id}: {e}")
            return api_response(
                status_code=500,
                message=f"{FETCH_ERROR}: {str(e)}",
            )

    @staticmethod
    def update_master_questions(data):
        try:
            company_id = data.get("company_id")
            questions = data.get("questions")
            last_processed_pdf_time = data.get("last_processed_pdf_time")

            if not questions:
                return api_response(status_code=400, message="Questions required")

            # master_data = mongo_util.find_one(
            # MASTER_QUESTIONS_COLLECTION, {"company_id": company_id})

            for question in questions:
                question["question_id"] = str(ObjectId())

            questions_to_add = questions

            # if master_data:
            #     master_data["top_questions"].extend(questions_to_add)
            #     master_data["last_processed_pdf_time"] = last_processed_pdf_time

            #     mongo_util.update_one(
            #         MASTER_QUESTIONS_COLLECTION,
            #         {"company_id": company_id},
            #         {"$set": {"top_questions": master_data["top_questions"],  "last_processed_pdf_time": last_processed_pdf_time}}
            #     )
            #     return api_response(status_code=200, message="Questions updated successfully.")

            new_master_data = {
                "company_id": company_id,
                "top_questions": questions_to_add,
                "last_processed_pdf_time": last_processed_pdf_time,
            }

            existing_data = mongo_util.find_one(
                MASTER_QUESTIONS_COLLECTION, {"company_id": company_id}
            )

            if existing_data:
                mongo_util.update_one(
                    MASTER_QUESTIONS_COLLECTION,
                    {"company_id": company_id},
                    {
                        "$set": {
                            "top_questions": new_master_data["top_questions"],
                            "last_processed_pdf_time": new_master_data[
                                "last_processed_pdf_time"
                            ],
                        }
                    },
                )
                return api_response(
                    status_code=200, message="Questions updated successfully."
                )
            else:
                mongo_util.insert_one(MASTER_QUESTIONS_COLLECTION, new_master_data)
                return api_response(
                    status_code=201,
                    message="New company and questions added successfully.",
                )

            # mongo_util.insert_one(MASTER_QUESTIONS_COLLECTION, new_master_data)

            # return api_response(status_code=201, message="New company and questions added successfully.")

        except Exception as e:
            logger.error(
                f"Error updating/adding questions for company ID {company_id}: {e}"
            )
            return api_response(status_code=500, message=f"An error occurred: {str(e)}")
