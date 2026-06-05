"""
Credential verifier service for validating API credentials.
"""

import httpx
from typing import Tuple, Optional
from django.utils import timezone


def verify_credential(credential) -> Tuple[bool, str]:
    """
    Verify if a credential is valid.
    
    Args:
        credential: APICredential model instance
        
    Returns:
        Tuple of (is_valid, message)
    """
    if credential.credential_type == 'api_key':
        return verify_api_key(credential)
    elif credential.credential_type == 'oauth2':
        return verify_oauth2(credential)
    elif credential.credential_type == 'basic':
        return verify_basic_auth(credential)
    elif credential.credential_type == 'bearer':
        return verify_bearer_token(credential)
    else:
        return True, "Credential type does not require verification"


def verify_api_key(credential) -> Tuple[bool, str]:
    """Verify API key credential."""
    if not credential.service_type:
        return True, "No service type configured for verification"
    
    verification_endpoints = {
        'openai': ('https://api.openai.com/v1/models', 'Authorization', 'Bearer'),
        'anthropic': ('https://api.anthropic.com/v1/models', 'x-api-key', None),
        'google': ('https://generativelanguage.googleapis.com/', 'Authorization', 'Bearer'),
    }
    
    if credential.service_type not in verification_endpoints:
        return True, f"No verification endpoint for {credential.service_type}"
    
    endpoint, header_name, prefix = verification_endpoints[credential.service_type]
    
    try:
        headers = {}
        if prefix:
            headers[header_name] = f"{prefix} {credential.credential_data}"
        else:
            headers[header_name] = credential.credential_data
        
        with httpx.Client(timeout=10) as client:
            response = client.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                return True, "API key is valid"
            elif response.status_code == 401:
                return False, "API key is invalid or expired"
            else:
                return False, f"API returned status {response.status_code}"
    except httpx.RequestError as e:
        return False, f"Connection error: {e}"


def verify_oauth2(credential) -> Tuple[bool, str]:
    """Verify OAuth2 credential."""
    service_config = credential.service_config or {}
    token_url = service_config.get('token_url')
    
    if not token_url:
        return True, "No token URL configured for verification"
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                token_url,
                data={
                    'client_id': service_config.get('client_id'),
                    'client_secret': credential.credential_data,
                    'grant_type': 'client_credentials'
                }
            )
            
            if response.status_code == 200:
                return True, "OAuth2 token is valid"
            else:
                return False, f"OAuth2 verification failed: {response.status_code}"
    except httpx.RequestError as e:
        return False, f"Connection error: {e}"


def verify_basic_auth(credential) -> Tuple[bool, str]:
    """Verify basic auth credential."""
    service_config = credential.service_config or {}
    test_url = service_config.get('test_url')
    
    if not test_url:
        return True, "No test URL configured for basic auth verification"
    
    import base64
    
    try:
        credentials = f"{service_config.get('username')}:{credential.credential_data}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        with httpx.Client(timeout=10) as client:
            response = client.get(
                test_url,
                headers={'Authorization': f"Basic {encoded}"}
            )
            
            if response.status_code in (200, 401):
                # 401 with basic auth means creds were sent, but may be invalid
                # If it's 200, creds are definitely valid
                return True, "Basic auth credentials are configured"
            else:
                return False, f"Auth test returned status {response.status_code}"
    except httpx.RequestError as e:
        return False, f"Connection error: {e}"


def verify_bearer_token(credential) -> Tuple[bool, str]:
    """Verify bearer token credential."""
    if not credential.service_type:
        return True, "No service type configured for verification"
    
    service_config = credential.service_config or {}
    test_url = service_config.get('test_url')
    
    if not test_url:
        return True, "No test URL configured for bearer token verification"
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                test_url,
                headers={'Authorization': f"Bearer {credential.credential_data}"}
            )
            
            if response.status_code == 200:
                return True, "Bearer token is valid"
            elif response.status_code == 401:
                return False, "Bearer token is invalid or expired"
            else:
                return False, f"Token verification returned status {response.status_code}"
    except httpx.RequestError as e:
        return False, f"Connection error: {e}"


def get_credential_for_tool(tool) -> Optional[dict]:
    """
    Get the credential data for a tool.
    
    Args:
        tool: Tool model instance
        
    Returns:
        Dictionary with credential data or None
    """
    if not tool.credential:
        return None
    
    credential = tool.credential
    service_config = credential.service_config or {}
    
    result = {
        'credential_type': credential.credential_type,
        'credential_data': credential.credential_data,
    }
    
    # Add service-specific headers
    if credential.auth_type == 'api_key':
        header_name = service_config.get('header_name', 'X-API-Key')
        result['header_name'] = header_name
        result['header_value'] = f"{header_name}: {credential.credential_data}"
    elif credential.auth_type == 'bearer':
        result['header'] = f"Bearer {credential.credential_data}"
    elif credential.auth_type == 'basic':
        import base64
        credentials = f"{service_config.get('username', '')}:{credential.credential_data}"
        result['header'] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
    
    return result
