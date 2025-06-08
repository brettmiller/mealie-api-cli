# mealie-api-cli
Mealie API wrapper cli script

Script to make interacting with Mealie api easier.

It tries to make smart choices about the HTTP methods to use.
Supports multipart content and file uploads when there is a file path in the content.

Environment Variables (required):
- MEALIE_URL    - Base URL of your Mealie instance
- MEALIE_TOKEN  - API token for authentication


Requires:
- beautifulsoup4
- requests


Full disclosure: this primarily written with the help of Claude Sonnet 4 (via GitHub Copilot)
