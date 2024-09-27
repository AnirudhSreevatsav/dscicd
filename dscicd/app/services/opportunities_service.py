import datetime
import json
from venv import logger
from flask import request
import requests
from bson import ObjectId
from app.constants.routes_constants import LOCAL_BASE_URL, ML_SERVICE_BASE_URL
from app.schemas.opportunity_schema import (
    filter_valid_meeting_fields,
    validate_meeting_data,
)
from app.utils.mongo_util import mongo_util
from app.constants.constants import (
    OPPORTUNITIES_COLLECTION,
    TRANSACT_QUESTIONS_COLLECTION,
)
from app.utils.response_util import api_response
from app.constants.response_constants import (
    OPPORTUNITY_FETCH_SUCCESS,
    OPPORTUNITY_FETCH_ERROR,
)


class OpportunitiesService:

    @staticmethod
    def get_opportunity_by_meeting_id(data):
        try:
            opportunity_id = data.get("opportunity_id")
            meeting_id = data.get("meeting_id")
            opportunity_object_id = ObjectId(opportunity_id)
            meeting_object_id = ObjectId(meeting_id)

            pipeline = [
                {"$match": {"_id": opportunity_object_id}},
                {
                    "$lookup": {
                        "from": TRANSACT_QUESTIONS_COLLECTION,
                        "localField": "transactional_discovery_question_id",
                        "foreignField": "_id",
                        "as": "transactional_discovery_questions",
                    }
                },
                {
                    "$unwind": {
                        "path": "$transactional_discovery_questions",
                        "preserveNullAndEmptyArrays": False,
                    }
                },
            ]

            results = mongo_util.aggregate(OPPORTUNITIES_COLLECTION, pipeline)
            opportunity = results[0] if results else None

            if not opportunity:
                return api_response(
                    status_code=404,
                    message="Opportunity not found",
                )

            meetings = opportunity.get("meetings", [])

            meeting_details_with_meeting_id = next(
                (item for item in meetings if item.get("_id") == meeting_object_id),
                None,
            )

            opportunity["meeting"] = (
                meeting_details_with_meeting_id
                if meeting_details_with_meeting_id
                else {}
            )

            opportunity.pop("meetings")

            if (
                opportunity.get("transactional_discovery_questions")
                and "questions" in opportunity["transactional_discovery_questions"]
            ):
                opportunity["transactional_discovery_questions"]["questions"] = (
                    OpportunitiesService.sort_questions(
                        opportunity["transactional_discovery_questions"]["questions"]
                    )
                )

            opportunity = _convert_objectid_to_str(opportunity)

            return api_response(
                status_code=200, message=OPPORTUNITY_FETCH_SUCCESS, data=opportunity
            )

        except Exception as e:
            return api_response(
                status_code=500, message=OPPORTUNITY_FETCH_ERROR, data=str(e)
            )

    @staticmethod
    def get_opportunity_by_id(data):
        try:
            opportunity_id = data.get("opportunity_id")
            opportunity_object_id = ObjectId(opportunity_id)

            pipeline = [
                {"$match": {"_id": opportunity_object_id}},
                {
                    "$lookup": {
                        "from": TRANSACT_QUESTIONS_COLLECTION,
                        "localField": "transactional_discovery_question_id",
                        "foreignField": "_id",
                        "as": "transactional_discovery_questions",
                    }
                },
                {
                    "$unwind": {
                        "path": "$transactional_discovery_questions",
                        "preserveNullAndEmptyArrays": False,
                    }
                },
            ]

            results = mongo_util.aggregate(OPPORTUNITIES_COLLECTION, pipeline)
            opportunity = results[0] if results else None

            if not opportunity:
                return api_response(
                    status_code=404,
                    message="Opportunity not found",
                )

            opportunity = _convert_objectid_to_str(opportunity)

            return api_response(
                status_code=200, message=OPPORTUNITY_FETCH_SUCCESS, data=opportunity
            )

        except Exception as e:
            return api_response(
                status_code=500, message=OPPORTUNITY_FETCH_ERROR, data=str(e)
            )

    @staticmethod
    def add_meeting_to_opportunity(data):
        try:
            opportunity_id = data.get("opportunity_id")
            meeting_details = validate_meeting_data(data.get("meeting_details"))
            if not opportunity_id:
                return api_response(
                    status_code=400, message="Opportunity id is required"
                )

            if not meeting_details.get("meeting_link"):
                return api_response(status_code=400, message="Meeting link is required")

            opportunity_object_id = ObjectId(opportunity_id)
            meeting_id = ObjectId()

            participants = meeting_details.get("participants", [])
            parsed_participants = []
            for participant in participants:
                if isinstance(participant, str):
                    try:
                        parsed_participant = json.loads(participant.replace("'", '"'))
                        parsed_participants.append(parsed_participant)
                    except json.JSONDecodeError:
                        parsed_participants.append(participant)
                else:
                    parsed_participants.append(participant)

            if not meeting_details.get("agenda"):
                opportunity = mongo_util.find_one(
                    OPPORTUNITIES_COLLECTION,
                    {"_id": opportunity_object_id},
                    projection={
                        "questions": True,
                        "action_items": True,
                        "meetings": {"$slice": -1},
                    },
                )

                if opportunity:
                    questions = opportunity.get("questions", [])
                    action_items = opportunity.get("action_items", [])
                    last_meeting = opportunity.get("meetings", [])
                    latest_agenda = (
                        last_meeting[0].get("agenda", []) if last_meeting else []
                    )

                    agenda = OpportunitiesService.fetch_agenda(
                        questions, action_items, latest_agenda
                    )

                    meeting_details["agenda"] = agenda.get("agenda", [])
            else:
                agenda_text = meeting_details.get("agenda")
                meeting_details["agenda"] = [
                    sentence.strip() for sentence in agenda_text.split(".") if sentence
                ]

            meeting_data = {
                "_id": meeting_id,
                "title": meeting_details.get("title"),
                "agenda": meeting_details.get("agenda", []),
                "meeting_link": meeting_details.get("meeting_link"),
                "meeting_stage": meeting_details.get("meeting_stage"),
                "meeting_recap": meeting_details.get("meeting_recap"),
                "start_meet": meeting_details.get("start_meet"),
                "end_meet": meeting_details.get("end_meet"),
                "participants": parsed_participants,
            }

            meeting_data = {k: v for k, v in meeting_data.items() if v is not None}

            result = mongo_util.update_one(
                OPPORTUNITIES_COLLECTION,
                {"_id": opportunity_object_id},
                {"$push": {"meetings": meeting_data}},
                upsert=False,
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200,
                    message="Meeting added successfully",
                    data={"meeting_id": str(meeting_id)},
                )
            else:
                return api_response(status_code=400, message="Failed to add meeting")

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def fetch_master_questions(company_id):
        try:
            url = f"{LOCAL_BASE_URL}/api/questions/master/fetch-questions?company_id={company_id}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return api_response(
                status_code=500, message=f"Failed to fetch master questions: {str(e)}"
            )

    @staticmethod
    def create_opportunity(data):
        try:
            name = data.get("name")
            seller_company_id = data.get("seller_company_id")
            user_id = data.get("user_id")
            opportunity_id = ObjectId()
            opportunity_data = {
                "_id": opportunity_id,
                "name": name,
                "seller_company_id": ObjectId(seller_company_id),
                "user_id": ObjectId(user_id),
                "transactional_discovery_question_id": None,
            }

            master_document = OpportunitiesService.fetch_master_questions(
                company_id=seller_company_id
            )

            if (
                isinstance(master_document, dict)
                and master_document.get("status_code") == 200
            ):
                master_data = master_document.get("data", {})
                questions = master_data.get("top_questions", [])
                questions_list = []

                for question in questions:
                    question_id = str(ObjectId())
                    question_data = {
                        "question_id": question_id,
                        "question": question.get("question"),
                        "time": question.get("time"),
                        "is_answered": False,
                        "is_deleted": False,
                        "question_type": question.get("question_type"),
                        "category": question.get("category"),
                    }
                    questions_list.append(question_data)

                transactional_discovery_question_id = ObjectId()
                transactional_discovery_question_data = {
                    "_id": transactional_discovery_question_id,
                    "questions": questions_list,
                    "opportunity_id": opportunity_id,
                    "current_question_id": "",
                }

                mongo_util.insert_one(
                    TRANSACT_QUESTIONS_COLLECTION, transactional_discovery_question_data
                )
                opportunity_data["transactional_discovery_question_id"] = (
                    transactional_discovery_question_id
                )
                created_opportunity = mongo_util.insert_one(
                    OPPORTUNITIES_COLLECTION, opportunity_data
                )

                if created_opportunity:
                    return api_response(
                        status_code=200,
                        message="Opportunity created successfully",
                        data={
                            "opportunity_id": str(opportunity_id),
                        },
                    )
                else:
                    return api_response(
                        status_code=404, message="Failed to create opportunity"
                    )

            else:
                return api_response(
                    status_code=404, message="Failed to fetch master questions"
                )

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def fetch_opportunity_by_user_id(data):
        try:
            user_id = data.get("user_id")
            projection = {"_id": 1, "name": 1}
            opportunities = mongo_util.find(
                OPPORTUNITIES_COLLECTION, {"user_id": ObjectId(user_id)}, projection
            )

            opportunities = _convert_objectid_to_str(opportunities)
            if not opportunities:
                return api_response(status_code=404, message="No opportunities found")

            return api_response(
                status_code=200,
                message="Opportunities fetched successfully",
                data=opportunities,
            )
        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def edit_meeting_in_opportunity(data):
        try:
            opportunity_object_id = ObjectId(data.get("opportunity_id"))
            meeting_object_id = ObjectId(data.get("meeting_id"))
            meeting_details = request.json.get("meeting_details", {})
            start_meet = meeting_details.get("start_meet")
            end_meet = meeting_details.get("end_meet")
            if start_meet or end_meet:
                for time_field, time_value in [("start_meet", start_meet), ("end_meet", end_meet)]:
                    if time_value:
                        try:
                            datetime.datetime.fromisoformat(time_value)
                        except ValueError:
                            return api_response(status_code=400,message=f"Please provide meeting time in valid format.")

            if not opportunity_object_id or not meeting_object_id:
                return api_response(
                    status_code=400,
                    message="Opportunity id and meeting id are required",
                )

            meeting_details = request.json.get("meeting_details", {})

            if not meeting_details:
                return api_response(
                    status_code=400,
                    message="Meeting details are required in the request body",
                )

            update_operations = {}
            array_operations = {}

            for k, v in meeting_details.items():
                if k == "participants":
                    parsed_participants = []
                    for participant in v:
                        if isinstance(participant, str):
                            try:
                                parsed_participant = json.loads(participant.replace("'", '"'))
                                parsed_participants.append(parsed_participant)
                            except json.JSONDecodeError:
                                parsed_participants.append(participant)
                        else:
                            parsed_participants.append(participant)
                    array_operations[f"meetings.$.{k}"] = {"$each": parsed_participants}
                else:
                    update_operations[f"meetings.$.{k}"] = v

            update_query = {}
            if update_operations:
                update_query["$set"] = update_operations
            if array_operations:
                update_query["$addToSet"] = array_operations

            result = mongo_util.update_one(
                OPPORTUNITIES_COLLECTION,
                {"_id": opportunity_object_id, "meetings._id": meeting_object_id},
                update_query,
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200,
                    message="Meeting updated successfully",
                    data={"updated": True},
                )
            elif result.matched_count > 0:
                return api_response(
                    status_code=200,
                    message="No changes were made to the meeting",
                    data={"updated": False},
                )
            else:
                return api_response(
                    status_code=404,
                    message="Meeting not found",
                    data={"updated": False},
                )
        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def search_opportunities(data):
        try:
            name_snippet = data.get("name_snippet", "")
            query = {"name": {"$regex": name_snippet, "$options": "i"}}
            print(name_snippet)
            projection = {"name": 1, "_id": 1}

            opportunities = mongo_util.find(OPPORTUNITIES_COLLECTION, query, projection)

            if not opportunities:
                return api_response(status_code=404, message="No opportunities found")

            opportunity_data = [
                {"id": str(opportunity["_id"]), "name": opportunity["name"]}
                for opportunity in opportunities
            ]

            return api_response(
                status_code=200,
                message="Opportunities fetched successfully",
                data=opportunity_data,
            )

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def discovery_details(data):
        try:
            user_id = data.get("user_id")
            opportunities = mongo_util.find(
                OPPORTUNITIES_COLLECTION, {"user_id": ObjectId(user_id)}
            )

            if not opportunities:
                return api_response(status_code=404, message="No opportunities found")

            meetings_since_last_month = []
            all_opportunities = []

            current_time = datetime.datetime.now()

            for opportunity in opportunities:
                current_opportunity = {
                    "_id": opportunity.get("_id"),
                    "name": opportunity.get("name"),
                }
                meetings = opportunity.get("meetings", [])
                previous_meeting = None
                ended_meetings_count = 0
                for meeting in meetings:
                    if meeting.get("end_meet") is None or (
                        datetime.datetime.fromisoformat(str(meeting.get("end_meet")))
                        > current_time
                    ):
                        current_opportunity["upcoming_meeting"] = {
                            "_id": meeting.get("_id"),
                            "title": meeting.get("title"),
                            "meeting_link": meeting.get("meeting_link"),
                            "start_meet": meeting.get("start_meet"),
                            "end_meet": meeting.get("end_meet"),
                        }
                        break
                    else:
                        previous_meeting = meeting
                        ended_meetings_count += 1

                if previous_meeting:
                    current_opportunity["previous_meeting"] = {
                        "_id": previous_meeting.get("_id"),
                        "title": previous_meeting.get("title"),
                        "meeting_link": previous_meeting.get("meeting_link"),
                        "start_meet": previous_meeting.get("start_meet"),
                        "end_meet": previous_meeting.get("end_meet"),
                    }

                if ended_meetings_count > 0:
                    current_opportunity["ended_meetings_count"] = ended_meetings_count

                all_opportunities.append(current_opportunity)
                for meeting in meetings:
                    if meeting.get("end_meet") is None or (
                        datetime.datetime.fromisoformat(str(meeting.get("end_meet")))
                        > current_time - datetime.timedelta(days=30)
                    ):
                        meetings_since_last_month.append(
                            {
                                "_id": meeting.get("_id"),
                                "opportunity_id": opportunity.get("_id"),
                                "title": meeting.get("title"),
                                "meeting_link": meeting.get("meeting_link"),
                                "start_meet": meeting.get("start_meet"),
                                "end_meet": meeting.get("end_meet"),
                            }
                        )

            response = {
                "opportunities": list(reversed(all_opportunities)),
                "meetings": meetings_since_last_month,
            }

            return api_response(
                status_code=200,
                message="Meetings fetched successfully",
                data=_convert_objectid_to_str(response),
            )

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def edit_opportunity(data):
        try:
            opportunity_id = data.get("opportunity_id")
            opportunity_details = data.get("opportunity_details", {})

            allowed_fields = ["recap", "research", "opportunity_current_stage", "actionable_items","average_sales_score","recap","total_sales_score","is_lead_qualified"]
            invalid_fields = set(opportunity_details.keys()
                                 ) - set(allowed_fields)
            if invalid_fields:
                return api_response(
                    status_code=400,
                    message=f"Invalid fields provided: {', '.join(invalid_fields)}",
                )

            opportunity_details_body = {
                k: v for k, v in opportunity_details.items() if k in allowed_fields
            }

            if not opportunity_details_body:
                return api_response(
                    status_code=400, message="Please provide valid opportunity details"
                )

            opportunity_object_id = ObjectId(opportunity_id)

            result = mongo_util.update_one(
                OPPORTUNITIES_COLLECTION,
                {"_id": opportunity_object_id},
                {"$set": opportunity_details_body},
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200,
                    message="Opportunity updated successfully",
                    data={"updated": True},
                )
            else:
                return api_response(
                    status_code=404,
                    message="Opportunity not found or no changes made",
                    data={"updated": False},
                )

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def add_transcript_to_meeting(data):
        try:
            opportunity_id = data.get("opportunity_id")
            meeting_id = data.get("meeting_id")
            transcript = data.get("transcript")

            if not opportunity_id or not meeting_id or not transcript:
                return api_response(
                    status_code=400,
                    message="Opportunity id, meeting id, and transcript chunk are required",
                )

            opportunity_object_id = ObjectId(opportunity_id)
            meeting_object_id = ObjectId(meeting_id)

            data_to_update = {"text": transcript}

            # Update the transcript by appending the new chunk
            result = mongo_util.update_one(
                OPPORTUNITIES_COLLECTION,
                {"_id": opportunity_object_id, "meetings._id": meeting_object_id},
                {"$push": {"meetings.$.transcript": data_to_update}},
            )

            if result.modified_count > 0:
                return api_response(
                    status_code=200,
                    message="Transcript chunk added successfully",
                    data={"updated": True},
                )
            else:
                return api_response(
                    status_code=404,
                    message="Meeting not found or no changes made",
                    data={"updated": False},
                )

        except Exception as e:
            return api_response(status_code=500, message=str(e))

    @staticmethod
    def fetch_agenda(questions, action_items, agenda=""):
        data = {"questions": questions, "agenda": agenda, "action_items": action_items}

        try:
            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/resync/agenda",
                    json=data,
                )
                result = response.json()
                return result.get("data", None)
        except Exception as e:
            logger.error(f"Error analysing answer: {e}")
            return None

    def sort_questions(questions):
        return sorted(questions, key=lambda q: q.get("is_answered", False))


def _convert_objectid_to_str(data):
    if isinstance(data, dict):
        return {k: _convert_objectid_to_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_objectid_to_str(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data
