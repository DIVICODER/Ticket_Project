from django.http import Http404, JsonResponse
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler
 
 
def json_404(request, exception=None):
    return JsonResponse({"error": "NOT_FOUND"}, status=404)
 
 
def json_500(request):
    return JsonResponse({"error": "INTERNAL_ERROR"}, status=500)
 
 
def collect_errors(detail, field, details):
    """Flatten any DRF error structure (dict, list, nested, list-index keys)
    into [{"field": ..., "message": ...}, ...]."""
    if isinstance(detail, dict):
        for key, value in detail.items():
            # an int key is a list position (e.g. seat_numbers[2]); keep parent name
            name = field if isinstance(key, int) else key
            collect_errors(value, name, details)
    elif isinstance(detail, list):
        for item in detail:
            collect_errors(item, field, details)
    else:
        details.append({"field": field or "non_field_errors", "message": str(detail)})
 
 
def custom_exception_handler(exc, context):
    # Validation failure -> 400, list ALL failing fields
    if isinstance(exc, ValidationError):
        details = []
        collect_errors(exc.detail, "", details)
        return Response({"error": "VALIDATION_ERROR", "details": details}, status=400)
 
    # Bad or empty JSON -> 400
    if isinstance(exc, ParseError):
        return Response({"error": "INVALID_REQUEST"}, status=400)
 
    # Record not found -> 404
    if isinstance(exc, Http404):
        return Response({"error": "NOT_FOUND"}, status=404)
 
    # Everything DRF knows about (e.g. 405 wrong method)
    response = exception_handler(exc, context)
    if response is not None:
        return response
 
    # Unexpected failure -> 500, no stack trace
    return Response({"error": "INTERNAL_ERROR"}, status=500)
 



# from django.http import Http404
# from rest_framework.exceptions import ParseError, ValidationError
# from rest_framework.response import Response
# from rest_framework.views import exception_handler

# from django.http import JsonResponse


# def json_404(request, exception=None):
#     return JsonResponse({"error": "NOT_FOUND"}, status=404)


# def json_500(request):
#     return JsonResponse({"error": "INTERNAL_ERROR"}, status=500)
# def custom_exception_handler(exc, context):

#     # Rule: validation failure -> 400, list ALL failing fields
#     if isinstance(exc, ValidationError):
#         details = []
#         for field, messages in exc.detail.items():
#             for message in messages:
#                 details.append({"field": field, "message": str(message)})
#         return Response({"error": "VALIDATION_ERROR", "details": details}, status=400)

#     # Rule: bad or empty JSON -> 400
#     if isinstance(exc, ParseError):
#         return Response({"error": "INVALID_REQUEST"}, status=400)

#     # Rule: record not found -> 404
#     if isinstance(exc, Http404):
#         return Response({"error": "NOT_FOUND"}, status=404)

#     # Anything else: let DRF try first (e.g. wrong method gives 405)
#     response = exception_handler(exc, context)
#     if response is not None:
#         return response

#         # Rule: validation failure -> 400, list ALL failing fields
#     if isinstance(exc, ValidationError):
#         details = []
#         collect_errors(exc.detail, "", details)
#         return Response({"error": "VALIDATION_ERROR", "details": details}, status=400)
    
#     # Rule: unexpected failure -> 500, no stack trace
#     return Response({"error": "INTERNAL_ERROR"}, status=500)

# def collect_errors(detail, field, details):
#     if isinstance(detail, dict):
#         for key, value in detail.items():
#             # a number key is a list position, so keep the parent field name
#             name = field if isinstance(key, int) else key
#             collect_errors(value, name, details)
#     elif isinstance(detail, list):
#         for item in detail:
#             collect_errors(item, field, details)
#     else:
#         details.append({"field": field or "non_field_errors", "message": str(detail)})