from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi import Response, Request
import traceback
import ujson

def exception_handler(_: Request, exc: Exception):
    traceback.print_exception(exc)
    return Response(content=ujson.dumps({"error": {"message": str(exc).replace("Value error, ", ""), "type": "error", "param": None, "code": None}}, escape_forward_slashes=False, indent=4), media_type="application/json", status_code=500)

async def validation_error_handler(request: Request, exc: RequestValidationError):
    message = list(exc.errors())[0]["msg"]
    return Response(content=ujson.dumps({"error": {"message": message.replace("Value error, ", ""), "type": "error", "param": None, "code": None}}, escape_forward_slashes=False, indent=4), media_type="application/json", status_code=400)

def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return Response(ujson.dumps(exc.detail, indent=4, escape_forward_slashes=False), media_type="application/json", status_code=exc.status_code)
    elif isinstance(exc.detail, list) and exc.detail:
       return Response(content=ujson.dumps({"error": {"message": exc.detail[0]['msg'].replace("Value error, 400: ", ""), "type": "error", "param": None, "code": None}}, indent=4, escape_forward_slashes=False), media_type="application/json", status_code=exc.status_code)
    else:
        return Response(content=ujson.dumps({"error": {"message": str(exc), "type": "error", "param": None, "code": None}}, indent=4, escape_forward_slashes=False), media_type="application/json", status_code=exc.status_code)



def method_not_allowed(request: Request, _):
    return Response(content=ujson.dumps({"error": {"message": f"Method Not Allowed ({request.method} {request.url.path})", "type": "error", "param": None, "code": None}}, indent=4,escape_forward_slashes=False), media_type="application/json", status_code=405)

def not_found(request: Request, _):
    message = f"Invalid URL ({request.method} {request.url.path})" if not request.url.path.startswith("/cdn/") else "The requested image was not found in our CDN."
    return Response(content=ujson.dumps({"error": {"message": message, "type": "error", "param": None, "code": None}}, indent=4, escape_forward_slashes=False), media_type="application/json", status_code=404)