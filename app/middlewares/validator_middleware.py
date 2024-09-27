from functools import wraps
from flask import request, jsonify
from app.constants.enums import RequestField

def validate_fields(fields_with_type=None):
    if fields_with_type is None:
        fields_with_type = []
    
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            errors = []

            for item in fields_with_type:
                if isinstance(item, tuple) and len(item) == 2:
                    field_group, expected_type = item
                else:
                    field_group, expected_type = item, RequestField.BODY  

                if expected_type == RequestField.BODY:
                    if not request.is_json:
                        return jsonify({"error": "Expected JSON body"}), 400
                    body_data = request.get_json()
                    for field in field_group:
                        if field not in body_data:
                            errors.append(f"{field} is required in the body")
                
                elif expected_type == RequestField.PARAMS:
                    for field in field_group:
                        if field not in request.args:
                            errors.append(f"{field} is required in query params")
                
                elif expected_type == RequestField.URL:
                    for field in field_group:
                        if field not in kwargs:
                            errors.append(f"{field} is required in URL path")

            if errors:
                return jsonify({"errors": errors}), 400

            valid_data = {}
            for item in fields_with_type:
                if isinstance(item, tuple) and len(item) == 2:
                    field_group, expected_type = item
                else:
                    field_group, expected_type = item, RequestField.BODY  

                if expected_type == RequestField.BODY:
                    body_data = request.get_json()
                    for field in field_group:
                        valid_data[field] = body_data.get(field)
                elif expected_type == RequestField.PARAMS:
                    for field in field_group:
                        valid_data[field] = request.args.get(field)
                elif expected_type == RequestField.URL:
                    for field in field_group:
                        valid_data[field] = kwargs.get(field)

            return f(valid_data, *args, **kwargs)
        
        return wrapper
    return decorator
