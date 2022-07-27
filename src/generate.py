import os, requests, uuid, json


def authenticate(path_to_key:str):
    """Sets environment variables for authenticating Azure translation resource

    Args:
        path_to_key (str): Path to file with subsciption key and resource region/location
    """
    with open(path_to_key) as f:
        key = json.load(f)

    print(key)

authenticate('./azure-translation-key.json')