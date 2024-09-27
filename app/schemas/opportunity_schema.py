from marshmallow import Schema, fields, ValidationError, pre_load

class SalesFrameworkParameterSchema(Schema):
    parameter = fields.Str(required=True)
    score = fields.Float(required=True)  
    explanation = fields.Str(required=True)

class SalesFrameworkAnalysisSchema(Schema):
    total_score = fields.Float(required=False)
    max_score = fields.Float(required=False)
    parameters = fields.List(fields.Nested(SalesFrameworkParameterSchema), required=False)  # List of objects

class MeetingSchema(Schema):
    title = fields.Str(required=False)
    agenda = fields.Str(required=False)
    meeting_link = fields.Str(required=True, error_messages={"required": "Meeting link is required."})
    meeting_stage = fields.Str(required=False)
    meeting_recap = fields.Str(required=False)
    start_meet = fields.DateTime(required=False)
    end_meet = fields.DateTime(required=False)
    participants = fields.List(fields.Str(), required=False, default=[])
    sales_framework_analysis = fields.Nested(SalesFrameworkAnalysisSchema, required=False)

    @pre_load
    def convert_participants_to_str(self, data, **kwargs):
        if 'participants' in data and isinstance(data['participants'], list):
            data['participants'] = [str(p) for p in data['participants']]
        return data


class MeetingSchemaSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = MeetingSchema()
        return cls._instance

def validate_meeting_data(data):
    schema = MeetingSchemaSingleton()
    errors = schema.validate(data)
    if errors:
        print(errors)
        raise ValidationError(errors)
    return schema.load(data)

def filter_valid_meeting_fields(data):
    """
    Filters the input dictionary, returning only the values that are part of the schema and
    converting the values to their desired format (e.g., string, DateTime) based on the schema.
    """
    schema = MeetingSchemaSingleton()
    valid_keys = schema.fields.keys()
    
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
    
    try:
        loaded_data = schema.dump(filtered_data)
    except ValidationError as e:
        print(f"Validation error during filtering: {e}")
        raise
    
    return loaded_data