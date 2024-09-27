from marshmallow import Schema, fields, validates, ValidationError


class QuestionSchema(Schema):
    company_id = fields.Str(required=True, error_messages={
                            "required": "Company ID is required."})
    question = fields.Str(required=True, error_messages={
                          "required": "Question is required."})
    answer = fields.Str(required=False)

    @validates('company_id')
    def validate_company_id(self, value):
        if not value.strip():
            raise ValidationError(
                "Please provide company ID as it is mandatory.")

    @validates('question')
    def validate_question(self, value):
        if not value.strip():
            raise ValidationError("Question cannot be blank.")
