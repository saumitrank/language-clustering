from multiprocessing import AuthenticationError
import os, requests, uuid, json
import unicodedata as ud
from typing import Union
import pandas as pd




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




def translate_text(input_text:str="hello world", target_languages:Union[str, list]="de", to_script:str="")->list:
    """Translate text from english to one or more. Can also transliterate

    Args:
        input_text (str, optional): Text to be translated. Defaults to "hello world".
        target_languages (Union[str, list], optional): Language(s) to translate to. Defaults to "de".
        to_script (str, optional): Script to transliterate to

    Raises:
        AuthenticationError: If environment variables are not set for authentication

    Returns:
        list: Translations and transliterations
    """

    if "azure-subscription-key" not in os.environ or "azure-subscription-region" not in os.environ:
        raise AuthenticationError("Authentication not completed correctly")

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

    if to_script:
        params['toScript'] = to_script

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


def list_languages()->dict:
    """Lists all languages available to the Azure translation service

    Returns:
        dict: Translations, transliterations and dictionaries available
    """
        
    url = "https://api.cognitive.microsofttranslator.com/languages?api-version=3.0"

    params = {
        'api-version': '3.0'
    }

    request = requests.get(url, params=params)

    response = request.json()

    return response



def transliterate_text(input_text:str, language:str, from_script:str, to_script:str="latn"):


    #Check authentication
    if "azure-subscription-key" not in os.environ or "azure-subscription-region" not in os.environ:
        raise AuthenticationError("Authentication not completed correctly")
    
    
    url = "https://api.cognitive.microsofttranslator.com/transliterate?api-version=3.0"

    subscription_key = os.environ["azure-subscription-key"]
    location = os.environ["azure-subscription-region"]

    params = {
        'api-version': '3.0',
        'language': language,
        'fromScript': from_script,
        'toScript': to_script
    }

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{
        'text': input_text
        }]

    request = requests.post(url=url, params=params, headers=headers, json=body)
    response = request.json()

    return response



def only_latin_chars(unistr:str)->bool:
    """A function to detect if string contains only latin characters (including accents etc)

    Args:
        unistr (str): Input string encoded in unicode

    Returns:
        bool: Whether there are only latin character
    """

    return all('LATIN' in ud.name(uchr)
    for uchr in unistr 
    if uchr.isalpha())


def final_languages()->pd.DataFrame:
    """Final languages suiltable for analysis

    Returns:
        pd.DataFrame: A dataframe whole columns are the language codes and rows describe the language name, 
                        nativeName, directionality, and, whether it is latin script
    """

    response = list_languages()

    translation_languages = pd.DataFrame(response['translation'])

    languages = set()

    # Add latin script languages
    for lang in translation_languages:
        if only_latin_chars(translation_languages.loc["nativeName", lang]):
            languages.add(lang)
            translation_languages.loc['latin', lang] = True

    # Add transliteration languages with latin output
    transliteration_languages = pd.DataFrame(response['transliteration'])
    
    transliteration_languages.loc['scripts'] = transliteration_languages.loc['scripts'].apply(lambda x: [lang['code'] for lang in x])

    for lang in transliteration_languages:
        if "Latn" in transliteration_languages.loc['scripts', lang] and lang in translation_languages:
            if lang not in languages:
                translation_languages.loc['latin', lang] = False
            languages.add(lang)

    # Remove languages with multiple scripts that also have latin
    # In this case only Klingon
    languages.remove("tlh-Piqd")

    return translation_languages[sorted(list(languages))]