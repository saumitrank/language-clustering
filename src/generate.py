import os, requests, uuid, json
from typing import Union




def authenticate(path_to_key:str):
    """Sets environment variables for authenticating Azure translation resource

    Args:
        path_to_key (str): Path to file with subsciption key and resource region/location
    """
    with open(path_to_key) as f:
        key = json.load(f)

    os.environ["azure-subscription-key"] = key["azure-subscription-key"]
    os.environ["azure-subscription-region"] = key["azure-subscription-region"]

    print("Environment variables set")




def translate_text(input_text:str="hello world", target_languages:Union[str, list]="de")->str:
    """Translate text from one language to one or more

    Args:
        input_text (str, optional): Text to be translated. Defaults to "hello world".
        target_languages (Union[str, list], optional): _description_. Defaults to "de".

    Raises:
        PermissionError: _description_

    Returns:
        str: _description_
    """

    if "azure-subscription-key" not in os.environ or "azure-subscription-region" not in os.environ:
        raise PermissionError("Authentication not completed correctly")

    subscription_key = os.environ["azure-subscription-key"]
    endpoint = "https://api.cognitive.microsofttranslator.com"

    location = os.environ["azure-subscription-region"]

    path = '/translate'
    constructed_url = endpoint + path

    params = {
        'api-version': '3.0',
        'from': 'en',
        'to': target_languages
    }
    constructed_url = endpoint + path

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    # You can pass more than one object in body.
    body = [{
        'text': input_text
    }]

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()

    return response


