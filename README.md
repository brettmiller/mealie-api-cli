# mealie-api-cli
### Mealie API cli script

Script to make interacting with the [Mealie](https://mealie.io/) api easier.

It tries to make smart choices about the HTTP methods to use.
Supports multipart content and file uploads when there is a file path in the content.

</br>
Environment Variables (required):

- MEALIE_URL    - Base URL of your Mealie instance
- MEALIE_TOKEN  - API token for authentication

</br>
Required python modules:

- beautifulsoup4
- requests

</br>

```text

  Usage: mealie-api.py <endpoint> [json_payload] [http_method]

  Examples:
    ./mealie-api.py recipes
    ./mealie-api.py recipes '{"name":"Test Recipe"}' POST
    ./mealie-api.py recipes/123 '{"name":"Updated Recipe"}' PUT
    ./mealie-api.py recipes/123 '' DELETE
  
```

The api is documented at: <https://docs.mealie.io/api/redoc>

</br>
Full disclosure: this was primarily written with the help of Claude Sonnet 4 (via GitHub Copilot)
