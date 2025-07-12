"""Microsoft Graph Service for executing Graph API commands with dual authentication modes."""

import json
import logging
import os
import asyncio
import getpass
from typing import Any, Dict, Optional

from azure.identity import DeviceCodeCredential, ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError
import httpx

from graph_mcp.config import Settings


class GraphService:
    """Service for executing Microsoft Graph API commands with dual authentication modes."""

    def __init__(self, settings: Settings):
        """Initialize Microsoft Graph service."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        log_level = getattr(logging, settings.log_level.upper())
        
        # Set up logging
        handler = logging.FileHandler(settings.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(log_level)

        # Store device code info for user display
        self.device_code_info = None
        self.credential = None
        self.client_secret = settings.get_client_secret()  # Try to get from environment first
        self.auth_config = settings.get_auth_config()
        
        # Log the authentication mode
        if settings.is_read_only_mode:
            self.logger.info("GraphService initialized in READ-ONLY mode using Microsoft Graph PowerShell public client")
        else:
            secret_source = "environment variable" if self.client_secret else "parameter prompt"
            self.logger.info(f"GraphService initialized in READ/WRITE mode using custom app: {self.auth_config['client_id']}")
            self.logger.info(f"Client secret source: {secret_source}")

    def _device_code_callback(self, verification_uri: str, user_code: str, expires_in: int):
        """Callback to capture device code authentication details."""
        self.device_code_info = {
            "verification_uri": verification_uri,
            "user_code": user_code,
            "expires_in": expires_in
        }
        self.logger.info(f"Device code authentication required - URL: {verification_uri}, Code: {user_code}")

    async def _get_client_secret(self) -> Dict[str, Any]:
        """Return client secret prompt for MCP flow."""
        if not self.client_secret:
            return {
                "success": False,
                "error": "Client secret required for custom app registration",
                "auth_required": True,
                "auth_type": "client_secret",
                "client_id": self.auth_config["client_id"],
                "tenant_id": self.auth_config["tenant_id"],
                "instructions": f"""
CLIENT SECRET REQUIRED:

Your custom app registration requires a client secret for authentication.

App Registration Details:
• Client ID: {self.auth_config["client_id"]}
• Tenant ID: {self.auth_config["tenant_id"]}

To complete authentication, you can either:

OPTION 1 - Provide via parameter (temporary):
{{
  "command": "users",
  "method": "GET", 
  "client_secret": "your-app-secret-here"
}}

OPTION 2 - Set as environment variable (persistent):
Add to your MCP configuration:
  "env": {{
    "CLIENT_SECRET": "your-app-secret-here"
  }}

Or use Docker args:
  "-e", "CLIENT_SECRET=your-app-secret-here"

If you don't have a client secret:
- Go to Azure Portal > Azure Active Directory > App registrations
- Find your app registration (Client ID: {self.auth_config["client_id"]})
- Go to Certificates & secrets > New client secret
- Copy the secret VALUE (not the ID)

The client secret will be cached for subsequent requests in this session.
"""
            }
        return {"success": True}

    async def execute_command(self, command: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, client_secret: Optional[str] = None) -> Dict[str, Any]:
        """Execute a Microsoft Graph API command with support for all HTTP methods."""
        try:
            self.logger.info(f"Executing Microsoft Graph command: {method} {command}")
            
            # Store client secret if provided
            if client_secret:
                self.client_secret = client_secret
            
            # Create credential based on auth mode
            if self.credential is None:
                if self.auth_config["mode"] == "custom":
                    # Custom app registration mode - requires client secret
                    if not self.client_secret:
                        secret_result = await self._get_client_secret()
                        if isinstance(secret_result, dict) and not secret_result.get("success", True):
                            return secret_result
                    
                    self.credential = ClientSecretCredential(
                        tenant_id=self.auth_config["tenant_id"],
                        client_id=self.auth_config["client_id"],
                        client_secret=self.client_secret
                    )
                    self.logger.info("Using ClientSecretCredential for custom app registration")
                else:
                    # Default read-only mode
                    self.credential = DeviceCodeCredential(
                        client_id=self.auth_config["client_id"],
                        tenant_id=self.auth_config["tenant_id"],
                        prompt_callback=self._device_code_callback
                    )
                    self.logger.info("Using DeviceCodeCredential for read-only access")
            
            # Clear any previous device code info
            self.device_code_info = None
            
            # Try to get access token with a short timeout
            self.logger.info("Getting access token")
            
            # Use asyncio to run the sync get_token with a timeout
            try:
                access_token = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.credential.get_token(*self.auth_config["scopes"])
                    ),
                    timeout=3.0  # 3 second timeout
                )
                
            except asyncio.TimeoutError:
                # If we have device code info, return it
                if self.device_code_info:
                    return {
                        "success": False,
                        "error": "Device code authentication required",
                        "auth_required": True,
                        "verification_uri": self.device_code_info["verification_uri"],
                        "user_code": self.device_code_info["user_code"],
                        "expires_in": self.device_code_info["expires_in"],
                        "instructions": f"""
AUTHENTICATION REQUIRED:

1. Open this URL in your browser: {self.device_code_info["verification_uri"]}
2. Enter this code: {self.device_code_info["user_code"]}
3. Complete the sign-in process with your Microsoft account
4. This code expires in {self.device_code_info["expires_in"]} seconds
5. After successful authentication, try your request again

The authentication will be cached for future requests.
"""
                    }
                else:
                    return {
                        "success": False,
                        "error": "Authentication timeout",
                        "auth_required": True,
                        "instructions": "Authentication timed out. Please try again."
                    }
            
            except Exception as auth_error:
                self.logger.error(f"Authentication failed: {auth_error}")
                
                # Clear the credential so next attempt can try fresh
                self.credential = None
                
                # If we have device code info, return it
                if self.device_code_info:
                    return {
                        "success": False,
                        "error": "Device code authentication required",
                        "auth_required": True,
                        "verification_uri": self.device_code_info["verification_uri"],
                        "user_code": self.device_code_info["user_code"],
                        "expires_in": self.device_code_info["expires_in"],
                        "instructions": f"""
AUTHENTICATION REQUIRED:

1. Open this URL in your browser: {self.device_code_info["verification_uri"]}
2. Enter this code: {self.device_code_info["user_code"]}
3. Complete the sign-in process with your Microsoft account
4. This code expires in {self.device_code_info["expires_in"]} seconds
5. After successful authentication, try your request again

The authentication will be cached for future requests.
"""
                    }
                else:
                    # Show the actual authentication error
                    error_msg = str(auth_error)
                    
                    # Check for specific client secret errors
                    if "AADSTS7000215" in error_msg or "Invalid client secret" in error_msg:
                        return {
                            "success": False,
                            "error": "Invalid client secret provided",
                            "auth_required": True,
                            "error_details": error_msg,
                            "instructions": f"""
CLIENT SECRET ERROR:

The client secret you provided is invalid. This could be because:

1. You copied the Secret ID instead of the Secret Value
   - In Azure Portal, use the VALUE column, not the Secret ID
   - The value should look like: 0pz8Q~~xfcUDmn0...
   - NOT the ID like: 74edbec7-9b02-44d6-b091-3df29daa1a2c

2. The client secret has expired
   - Check the expiration date in Azure Portal
   - Create a new client secret if needed

3. The client secret was incorrectly copied
   - Make sure you copied the complete value
   - Avoid extra spaces or characters

App Registration Details:
• Client ID: {self.auth_config["client_id"]}
• Tenant ID: {self.auth_config["tenant_id"]}

Please verify your client secret and try again.
"""
                        }
                    else:
                        # Generic auth error without device code info
                        return {
                            "success": False,
                            "error": f"Authentication failed: {error_msg}",
                            "auth_required": True,
                            "instructions": "Please try again. If the issue persists, you may need to clear cached credentials."
                        }

            # Prepare the API request
            url = f"https://graph.microsoft.com/v1.0/{command.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {access_token.token}",
                "Content-Type": "application/json"
            }

            self.logger.info(f"Making {method} request to: {url}")
            if data:
                self.logger.info(f"Request body: {json.dumps(data, indent=2)}")
            
            async with httpx.AsyncClient() as client:
                # Choose the appropriate HTTP method
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == "PATCH":
                    response = await client.patch(url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported HTTP method: {method}"
                    }
                
                self.logger.info(f"Response status: {response.status_code}")
                
                if response.status_code in [200, 201, 202, 204]:
                    # Handle successful responses
                    if response.status_code == 204:  # No content
                        return {
                            "success": True,
                            "data": {"message": "Operation completed successfully (no content returned)"},
                            "status_code": response.status_code
                        }
                    else:
                        try:
                            data = response.json()
                            return {
                                "success": True,
                                "data": data,
                                "status_code": response.status_code
                            }
                        except json.JSONDecodeError:
                            # Some responses might not be JSON
                            return {
                                "success": True,
                                "data": {"message": "Operation completed successfully", "response_text": response.text},
                                "status_code": response.status_code
                            }
                else:
                    # Handle error responses
                    try:
                        error_data = response.json()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}: {error_data.get('error', {}).get('message', response.text)}",
                            "status_code": response.status_code,
                            "error_details": error_data
                        }
                    except json.JSONDecodeError:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}: {response.text}",
                            "status_code": response.status_code
                        }
                    
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return {
                "success": False,
                "error": str(e)
            }
