#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mealie API Wrapper Script
Usage: ./mealie-api.py <endpoint> [json_payload] [http_method]
Examples:
  ./mealie-api.py recipes
  ./mealie-api.py recipes '{"name":"Test Recipe"}' POST
  ./mealie-api.py recipes/123 '{"name":"Updated Recipe"}' PUT
  ./mealie-api.py recipes/123 '' DELETE

Environment Variables (required):
  MEALIE_URL    - Base URL of your Mealie instance
  MEALIE_TOKEN  - API token for authentication  

The api is documented at:
  https://docs.mealie.io/api/redoc/

 Created with the claude.ai prompt:
 "can you write a bash script that's acts kind of like a wrapper to make it easier to call the Mealie API.
 It should get the URL from a variable called MEALIE_URL and the API token from a variable called MEALIE_TOKEN.
 It should make calls the the api using something like curl and take as inputs the api endpoint to use and a
 json payload if it's a POST endpoint.". Then asked to convert to python and enhanced to support multipart 
 uploads and verbose output.
"""

import sys
import os
import json
import argparse
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_color(color: str, message: str) -> None:
    """Print colored output."""
    print(f"{color}{message}{Colors.NC}")


def show_usage() -> None:
    """Show usage information."""
    print("Usage: mealie-api.py <endpoint> [json_payload] [http_method] [-m|--multipart] [-r|--raw] [-v|--verbose]")
    print("")
    print("Arguments:")
    print("  endpoint      - API endpoint (e.g., recipes, users/self)")
    print("  json_payload  - JSON data for POST/PUT requests (optional)")
    print("  http_method   - HTTP method: GET, POST, PUT, DELETE (default: GET, or POST if payload provided)")
    print("")
    print("Options:")
    print("  -m, --multipart - Use multipart/form-data content type instead of JSON")
    print("  -r, --raw       - Output raw response without status codes or formatting")
    print("                    useful for piping to other tools or scripts")
    print("  -v, --verbose   - Show detailed HTTP request information for debugging")
    print("")
    print("Examples:")
    print("  mealie-api.py recipes")
    print("  mealie-api.py recipes --raw")
    print("  mealie-api.py recipes --verbose")
    print("  mealie-api.py recipes '{\"name\":\"My Recipe\"}' POST")
    print("  mealie-api.py recipes/123 '{\"name\":\"Updated Recipe\"}' PUT")
    print("  mealie-api.py recipes/123 '' DELETE")
    print("  mealie-api.py recipes/import-url '{\"url\":\"https://example.com\"}' POST --multipart")
    print("  mealie-api.py groups/migrations '{\"migration_type\":\"nextcloud\",\"archive\":\"~/path/to/file.zip\"}' POST --multipart")
    print("")
    print("See: https://docs.mealie.io/api/redoc/ for API documentation.")
    print("")

def validate_environment() -> tuple[str, str]:
    """Validate required environment variables."""
    mealie_url = os.getenv('MEALIE_URL')
    mealie_token = os.getenv('MEALIE_TOKEN')

    if not mealie_url:
        print_color(Colors.RED, "Error: MEALIE_URL environment variable is not set")
        print("Set it with: export MEALIE_URL='https://your-mealie-instance.com'")
        sys.exit(1)

    if not mealie_token:
        print_color(Colors.RED, "Error: MEALIE_TOKEN environment variable is not set")
        print("Set it with: export MEALIE_TOKEN='your-api-token'")
        sys.exit(1)

    return mealie_url.rstrip('/'), mealie_token


def build_url(base_url: str, endpoint: str) -> str:
    """Build the full API URL."""
    # Ensure endpoint is properly formatted
    if endpoint.startswith('/'):
        endpoint = f"/api{endpoint}"
    else:
        endpoint = f"/api/{endpoint}"

    return f"{base_url}{endpoint}"


def parse_json_payload(payload: str) -> Optional[Dict[Any, Any]]:
    """Parse JSON payload string."""
    if not payload or payload.strip() == '':
        return None

    try:
        # First attempt to parse as-is
        return json.loads(payload)
    except json.JSONDecodeError:
        try:
            # If that fails, try to fix common path escape issues
            # Replace escaped spaces and other common shell escapes
            fixed_payload = payload.replace('\\ ', ' ')  # Escaped spaces
            fixed_payload = fixed_payload.replace('\\(', '(')  # Escaped parentheses
            fixed_payload = fixed_payload.replace('\\)', ')')
            fixed_payload = fixed_payload.replace('\\&', '&')  # Escaped ampersands
            fixed_payload = fixed_payload.replace('\\[', '[')  # Escaped brackets
            fixed_payload = fixed_payload.replace('\\]', ']')
            fixed_payload = fixed_payload.replace('\\{', '{')  # Escaped braces
            fixed_payload = fixed_payload.replace('\\}', '}')
            fixed_payload = fixed_payload.replace('\\;', ';')  # Escaped semicolons
            fixed_payload = fixed_payload.replace('\\>', '>')  # Escaped redirects
            fixed_payload = fixed_payload.replace('\\<', '<')
            fixed_payload = fixed_payload.replace('\\|', '|')  # Escaped pipes
            fixed_payload = fixed_payload.replace('\\$', '$')  # Escaped dollar signs
            fixed_payload = fixed_payload.replace('\\`', '`')  # Escaped backticks
            fixed_payload = fixed_payload.replace('\\\'', '\'')  # Escaped single quotes
            fixed_payload = fixed_payload.replace('\\"', '"')  # Escaped double quotes (be careful with JSON)
            
            print_color(Colors.CYAN, f"Fixed shell escapes in JSON payload")
            return json.loads(fixed_payload)
        except json.JSONDecodeError as e:
            print_color(Colors.RED, f"Error: Invalid JSON payload - {e}")
            print_color(Colors.YELLOW, f"Original payload: {payload}")
            print_color(Colors.YELLOW, f"Attempted fix: {fixed_payload}")
            sys.exit(1)


def prepare_file_upload(payload: Dict[Any, Any]) -> Dict[Any, Any]:
    """Convert file paths in payload to actual file objects for upload."""
    files = {}
    data = {}
    
    for key, value in payload.items():
        if isinstance(value, str) and (
            key.lower() in ['archive', 'file', 'upload', 'attachment'] or 
            value.startswith('~/') or 
            value.startswith('/') or
            '.' in value.split('/')[-1]  # Has file extension
        ):
            # Expand user path
            file_path = os.path.expanduser(value)
            
            if os.path.isfile(file_path):
                print_color(Colors.CYAN, f"Adding file upload: {key} -> {file_path}")
                files[key] = open(file_path, 'rb')
            else:
                print_color(Colors.RED, f"Error: File not found: {file_path}")
                sys.exit(1)
        else:
            data[key] = value
    
    return {'files': files, 'data': data}


def determine_method(payload: Optional[Dict[Any, Any]], method: Optional[str]) -> str:
    """Determine HTTP method."""
    if method:
        return method.upper()
    elif payload is not None:
        return 'POST'
    else:
        return 'GET'


def print_verbose_request(url: str, method: str, headers: Dict[str, str], payload: Optional[Dict[Any, Any]], multipart: bool = False) -> None:
    """Print detailed request information for debugging."""
    print_color(Colors.BLUE, "=== HTTP REQUEST DEBUG INFO ===")
    print(f"URL: {url}")
    print(f"Method: {method}")
    print(f"Timeout: 30 seconds")
    print(f"Content Type: {'multipart/form-data' if multipart else 'application/json'}")
    print()
    
    print_color(Colors.YELLOW, "Headers:")
    for key, value in headers.items():
        # Mask the token for security but show its length
        if key.lower() == 'authorization' and value.startswith('Bearer '):
            token = value[7:]  # Remove 'Bearer '
            masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
            print(f"  {key}: Bearer {masked_token}")
        else:
            print(f"  {key}: {value}")
    print()
    
    if payload:
        if multipart:
            print_color(Colors.YELLOW, "Request Body (Multipart Form Data):")
            for key, value in payload.items():
                if isinstance(value, str) and (
                    key.lower() in ['archive', 'file', 'upload', 'attachment'] or 
                    value.startswith('~/') or 
                    value.startswith('/') or
                    '.' in value.split('/')[-1]
                ):
                    file_path = os.path.expanduser(value)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        size_str = f"{file_size / 1024:.2f} KB" if file_size > 1024 else f"{file_size} bytes"
                        print(f"  {key}: {file_path} ({size_str})")
                    else:
                        print(f"  {key}: {value} (FILE NOT FOUND)")
                else:
                    print(f"  {key}: {value}")
        else:
            print_color(Colors.YELLOW, "Request Body (JSON):")
            print(json.dumps(payload, indent=2))
        print()
    else:
        print_color(Colors.YELLOW, "Request Body: (empty)")
        print()


def print_verbose_response(response: requests.Response) -> None:
    """Print detailed response information for debugging."""
    print_color(Colors.BLUE, "=== HTTP RESPONSE DEBUG INFO ===")
    print(f"Status Code: {response.status_code}")
    print(f"Reason: {response.reason}")
    print(f"URL: {response.url}")
    
    # Calculate and display response time if available
    if hasattr(response, 'elapsed'):
        elapsed_ms = response.elapsed.total_seconds() * 1000
        print(f"Response Time: {elapsed_ms:.2f}ms")
    
    print()
    
    print_color(Colors.YELLOW, "Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print()
    
    # Show response size
    content_length = len(response.content)
    if content_length > 1024:
        size_str = f"{content_length / 1024:.2f} KB"
    else:
        size_str = f"{content_length} bytes"
    print(f"Response Size: {size_str}")
    print()


def make_request(url: str, method: str, headers: Dict[str, str], payload: Optional[Dict[Any, Any]], multipart: bool = False) -> requests.Response:
    """Make the HTTP request."""
    try:
        if method in ['POST', 'PUT', 'PATCH'] and payload is not None:
            if multipart:
                # Prepare files and data for multipart upload
                upload_data = prepare_file_upload(payload)
                files = upload_data['files']
                data = upload_data['data']
                
                # Remove Content-Type header to let requests set multipart boundary
                multipart_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
                
                try:
                    response = requests.request(method, url, headers=multipart_headers, files=files, data=data, timeout=30)
                finally:
                    # Close any opened files
                    for file_obj in files.values():
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
            else:
                response = requests.request(method, url, headers=headers, json=payload, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, timeout=30)
        return response
    except requests.exceptions.RequestException as e:
        print_color(Colors.RED, f"✗ Request failed: {e}")
        sys.exit(1)


def format_html_response(html_content: str) -> str:
    """Parse and format HTML response for better readability."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try to extract meaningful content
        title = soup.find('title')
        if title:
            result = f"Title: {title.get_text().strip()}\n\n"
        else:
            result = ""

        # Look for error messages or main content
        error_divs = soup.find_all(['div', 'p', 'span'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['error', 'message', 'alert', 'warning']
        ))

        if error_divs:
            result += "Error/Message content:\n"
            for div in error_divs[:3]:  # Limit to first 3 matches
                text = div.get_text().strip()
                if text:
                    result += f"- {text}\n"
        else:
            # Extract main body content if no specific error messages
            body = soup.find('body')
            if body:
                # Remove script and style elements
                for script in body(["script", "style"]):
                    script.decompose()

                text = body.get_text()
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = '\n'.join(chunk for chunk in chunks if chunk)

                # Limit length for readability
                if len(clean_text) > 500:
                    clean_text = clean_text[:500] + "...\n[Content truncated]"

                result += clean_text

        return result if result.strip() else html_content

    except Exception:
        # If parsing fails, return original content
        return html_content


def format_response(response: requests.Response, raw_output: bool = False, verbose: bool = False) -> None:
    """Format and display the response."""
    if verbose:
        print_verbose_response(response)
    
    if raw_output:
        # Raw output - just print the response body
        print(response.text, end='')
        return

    # Print status
    if 200 <= response.status_code < 300:
        print_color(Colors.GREEN, f"✓ Success (HTTP {response.status_code})")
    elif 400 <= response.status_code < 500:
        print_color(Colors.RED, f"✗ Client Error (HTTP {response.status_code})")
    elif 500 <= response.status_code < 600:
        print_color(Colors.RED, f"✗ Server Error (HTTP {response.status_code})")
    else:
        print_color(Colors.YELLOW, f"! Unexpected Status (HTTP {response.status_code})")

    # Print response body
    content = response.text.strip()
    if not content:
        if 200 <= response.status_code < 300:
            print_color(Colors.YELLOW, "Success but no response body received")
        else:
            print_color(Colors.YELLOW, "No response body received")
        return

    print("\nResponse:")

    # Determine content type
    content_type = response.headers.get('content-type', '').lower()

    if 'application/json' in content_type:
        # Handle JSON response
        try:
            json_data = response.json()
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print_color(Colors.YELLOW, "Response claims to be JSON but is not valid JSON:")
            print(content)
    elif 'text/html' in content_type:
        # Handle HTML response
        print_color(Colors.YELLOW, "HTML Response (parsed):")
        formatted_html = format_html_response(content)
        print(formatted_html)
    else:
        # Handle other content types
        if content_type:
            print_color(Colors.YELLOW, f"Content-Type: {content_type}")
        print(content)


def main():
    """Main function."""
    # Parse arguments to check for flags
    raw_output = False
    verbose = False
    multipart = False
    args = sys.argv[1:]

    # Remove flags from args
    if '-r' in args:
        raw_output = True
        args.remove('-r')
    if '--raw' in args:
        raw_output = True
        args.remove('--raw')
    if '-v' in args:
        verbose = True
        args.remove('-v')
    if '--verbose' in args:
        verbose = True
        args.remove('--verbose')
    if '-m' in args:
        multipart = True
        args.remove('-m')
    if '--multipart' in args:
        multipart = True
        args.remove('--multipart')

    # Check for help
    if len(args) == 0 or args[0] in ['-h', '--help']:
        show_usage()
        sys.exit(0)

    # Parse remaining arguments
    if len(args) < 1:
        print_color(Colors.RED, "Error: Missing endpoint argument")
        show_usage()
        sys.exit(1)

    endpoint = args[0]
    json_payload_str = args[1] if len(args) > 1 else ''
    http_method = args[2] if len(args) > 2 else None

    # Validate environment
    base_url, token = validate_environment()

    # Build request parameters
    url = build_url(base_url, endpoint)
    payload = parse_json_payload(json_payload_str)
    method = determine_method(payload, http_method)

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    # Set content type based on multipart flag
    if not multipart:
        headers['Content-Type'] = 'application/json'

    # Print request info
    if verbose:
        print_verbose_request(url, method, headers, payload, multipart)
    elif not raw_output:
        print_color(Colors.BLUE, f"Making {method} request to: {url}")
        if multipart:
            print_color(Colors.CYAN, f"Content-Type: multipart/form-data")
        if payload:
            print_color(Colors.YELLOW, f"Payload: {json.dumps(payload)}")
        print()

    # Make request
    response = make_request(url, method, headers, payload, multipart)

    # Format and display response
    format_response(response, raw_output, verbose)

    # Exit with appropriate code
    sys.exit(0 if 200 <= response.status_code < 300 else 1)


if __name__ == '__main__':
    main()

