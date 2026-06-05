"""
Unified API response utilities for Flowly.

This module provides consistent response format across all API endpoints.
"""

from rest_framework.response import Response
from rest_framework import status


# ============== Success Response Builders ==============

def success_response(data=None, message="success", code=200):
    """
    Build a unified success response.
    
    Args:
        data: Response data (can be any JSON-serializable value)
        message: Human-readable message
        code: HTTP status code (default 200)
    
    Returns:
        Response object with unified format:
        {
            "code": 200,
            "message": "success",
            "data": {...}
        }
    """
    response_data = {
        "code": code,
        "message": message,
    }
    if data is not None:
        response_data["data"] = data
    return Response(response_data, status=code)


def created_response(data=None, message="Created successfully", code=201):
    """
    Build a unified 201 Created response.
    
    Args:
        data: Response data
        message: Human-readable message
        code: HTTP status code (default 201)
    
    Returns:
        Response object with 201 status
    """
    return success_response(data=data, message=message, code=code)


def updated_response(data=None, message="Updated successfully", code=200):
    """
    Build a unified 200 OK response for update operations.
    
    Args:
        data: Response data
        message: Human-readable message
        code: HTTP status code (default 200)
    
    Returns:
        Response object with 200 status
    """
    return success_response(data=data, message=message, code=code)


def deleted_response(message="Deleted successfully", code=204):
    """
    Build a unified 204 No Content response.
    
    Args:
        message: Human-readable message
        code: HTTP status code (default 204)
    
    Returns:
        Response object with 204 status
    """
    return success_response(data=None, message=message, code=code)


# ============== Error Response Builders ==============

def error_response(message="An error occurred", code=400, errors=None):
    """
    Build a unified error response.
    
    Args:
        message: Human-readable error message
        code: HTTP status code (default 400)
        errors: Optional dict of field-specific errors
    
    Returns:
        Response object with error format:
        {
            "code": 400,
            "message": "Validation error",
            "errors": {...}
        }
    """
    response_data = {
        "code": code,
        "message": message,
    }
    if errors is not None:
        response_data["errors"] = errors
    return Response(response_data, status=code)


def validation_error_response(errors, message="Validation error", code=400):
    """
    Build a unified 400 Bad Request response for validation errors.
    
    Args:
        errors: Dict of field-specific validation errors
        message: Human-readable message
        code: HTTP status code (default 400)
    
    Returns:
        Response object with 400 status
    """
    return error_response(message=message, code=code, errors=errors)


def not_found_response(message="Resource not found", code=404):
    """
    Build a unified 404 Not Found response.
    
    Args:
        message: Human-readable error message
        code: HTTP status code (default 404)
    
    Returns:
        Response object with 404 status
    """
    return error_response(message=message, code=code)


def unauthorized_response(message="Unauthorized", code=401):
    """
    Build a unified 401 Unauthorized response.
    
    Args:
        message: Human-readable error message
        code: HTTP status code (default 401)
    
    Returns:
        Response object with 401 status
    """
    return error_response(message=message, code=code)


def forbidden_response(message="Forbidden", code=403):
    """
    Build a unified 403 Forbidden response.
    
    Args:
        message: Human-readable error message
        code: HTTP status code (default 403)
    
    Returns:
        Response object with 403 status
    """
    return error_response(message=message, code=code)


def server_error_response(message="Internal server error", code=500):
    """
    Build a unified 500 Internal Server Error response.
    
    Args:
        message: Human-readable error message
        code: HTTP status code (default 500)
    
    Returns:
        Response object with 500 status
    """
    return error_response(message=message, code=code)


# ============== Pagination Response Builders ==============

def paginated_response(queryset, page=1, page_size=20, request=None):
    """
    Build a unified paginated response.
    
    Args:
        queryset: Django queryset to paginate
        page: Current page number (1-indexed)
        page_size: Number of items per page
        request: Optional DRF request object for building next/previous URLs
    
    Returns:
        Response object with paginated format:
        {
            "code": 200,
            "message": "success",
            "data": {
                "count": 100,
                "next": "http://...",
                "previous": "http://...",
                "results": [...]
            }
        }
    """
    try:
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()
        items = list(queryset[start:end])
        
        # Build next/previous URLs if request is provided
        next_url = None
        previous_url = None
        if request:
            from urllib.parse import urlencode
            base_url = request.build_absolute_uri().split('?')[0]
            
            if end < total:
                params = request.query_params.copy()
                params['page'] = page + 1
                next_url = f"{base_url}?{urlencode(params)}"
            
            if page > 1:
                params = request.query_params.copy()
                params['page'] = page - 1
                previous_url = f"{base_url}?{urlencode(params)}"
        
        data = {
            "count": total,
            "next": next_url,
            "previous": previous_url,
            "results": items
        }
        
        return success_response(data=data, message="success")
    except (ValueError, TypeError):
        return success_response(
            data={"count": 0, "next": None, "previous": None, "results": []},
            message="success"
        )


# ============== Stream Response Helpers ==============

def stream_success_response():
    """
    Build a stream success event for SSE responses.
    
    Returns:
        dict for SSE data format:
        {"type": "success", "data": {...}}
    """
    return {"type": "success"}


def stream_error_response(error):
    """
    Build a stream error event for SSE responses.
    
    Args:
        error: Error message string
    
    Returns:
        dict for SSE data format:
        {"type": "error", "error": "..."}
    """
    return {"type": "error", "error": error}


def stream_progress_response(progress, message=None):
    """
    Build a stream progress event for SSE responses.
    
    Args:
        progress: Progress percentage (0-100)
        message: Optional progress message
    
    Returns:
        dict for SSE data format:
        {"type": "progress", "progress": 50, "message": "..."}
    """
    data = {"type": "progress", "progress": progress}
    if message:
        data["message"] = message
    return data


# ============== Mixin for View Classes ==============

class UnifiedResponseMixin:
    """
    Mixin for DRF ViewSets to provide unified response methods.
    
    Usage:
        class MyViewSet(UnifiedResponseMixin, viewsets.ModelViewSet):
            def list(self, request):
                queryset = self.get_queryset()
                return paginated_response(
                    queryset=queryset,
                    page=request.query_params.get('page', 1),
                    page_size=request.query_params.get('page_size', 20),
                    request=request
                )
    
    Or use directly in any view:
        def my_view(request):
            return success_response(data={'key': 'value'})
    """
    
    def success(self, data=None, message="success", code=200):
        """Return unified success response."""
        return success_response(data=data, message=message, code=code)
    
    def created(self, data=None, message="Created successfully"):
        """Return unified 201 Created response."""
        return created_response(data=data, message=message)
    
    def updated(self, data=None, message="Updated successfully"):
        """Return unified 200 OK response for updates."""
        return updated_response(data=data, message=message)
    
    def deleted(self, message="Deleted successfully"):
        """Return unified 204 No Content response."""
        return deleted_response(message=message)
    
    def error(self, message="An error occurred", code=400, errors=None):
        """Return unified error response."""
        return error_response(message=message, code=code, errors=errors)
    
    def validation_error(self, errors, message="Validation error"):
        """Return unified 400 validation error response."""
        return validation_error_response(errors=errors, message=message)
    
    def not_found(self, message="Resource not found"):
        """Return unified 404 not found response."""
        return not_found_response(message=message)
    
    def paginated(self, queryset, page=1, page_size=20):
        """Return unified paginated response."""
        return paginated_response(
            queryset=queryset,
            page=page,
            page_size=page_size,
            request=getattr(self, 'request', None)
        )
