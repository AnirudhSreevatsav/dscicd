from app.utils.logging import setup_logging
from app.middlewares.socketio import socketio
from app.utils.mongo_util import MongoDB
from app.constants.constants import TRANSACT_QUESTIONS_COLLECTION
import threading

mongo = MongoDB()


logger = setup_logging()


def watch_collection():
    change_stream = mongo.get_collection(TRANSACT_QUESTIONS_COLLECTION).watch()

    for change in change_stream:


        operation_type = change['operationType']

        if operation_type == 'update':
            # Extract the updated fields
            updated_fields = change['updateDescription']['updatedFields']
            object_id = change['documentKey']['_id']

            question_index = None
            for field, value in updated_fields.items():
                if field.startswith('questions.'):
                    question_index = int(field.split('.')[1])

            projection = {'current_question_id': 1, 'user_id': 1}

            if question_index is not None:
                projection['questions'] = {'$slice': [question_index, 1]}

            document = mongo.get_collection(TRANSACT_QUESTIONS_COLLECTION).find_one(
                {'_id': object_id},
                projection
            )

            emit_data = {
                "current_question_id": document.get('current_question_id'),
                "updated_question": document.get('questions')[0] if isinstance(document.get('questions'), list) and document.get('questions') else None
            }           

            socketio.emit('transact_document_updated', emit_data)
            # socketio.emit('transact_document_updated', emit_data, room = object_id)


def start_change_stream():
    thread = threading.Thread(target=watch_collection)
    thread.start()


# if change['operationType'] in ['insert', 'update', 'replace']:
# {'_id': {'_data': '8266D74A48000000062B042C0100296E5A1004172C7CC086A64D23AAAC789A9FAAF814463C6F7065726174696F6E54797065003C7570646174650046646F63756D656E744B65790046645F6964006466D705B247432FE0EAFA6C9F000004'},
#  'operationType': 'update', 'clusterTime': Timestamp(1725385288, 6),
#  'wallTime': datetime.datetime(2024, 9, 3, 17, 41, 28, 299000),
#  'ns': {'db': 'pepsales', 'coll': 'TransactDiscoveryQuestions'},
#  'documentKey': {'_id': ObjectId('66d705b247432fe0eafa6c9f')},
#  'updateDescription': {'updatedFields': {'questions.1.question': '49  What is your as-is process?'},
#  'removedFields': [], 'truncatedArrays': []}}
