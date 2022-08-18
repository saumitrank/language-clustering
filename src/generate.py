import pandas as pd
import nltk, requests, os
from zipfile import ZipFile
from langcodes import Language, standardize_tag

nltk.download(['wordnet', 'omw-1.4', 'brown', 'stopwords', 'swadesh'])
from nltk.corpus import wordnet, brown, stopwords, swadesh

import translate

"""This module generates the relevant data files before they can be analyzed to obtain the language families"""



def final_languages()->pd.DataFrame:
    """Final languages suiltable for clustering analysis using Azure

    Returns:
        pd.DataFrame: A dataframe whole columns are the language codes and rows describe the language name, 
                        nativeName, directionality, and, whether it is latin script
    """

    response = translate.list_languages()

    translation_languages = pd.DataFrame(response['translation'])

    languages = set()

    # Add latin script languages

    N = 90
    test_translations = pd.DataFrame(translate.translate_text("hello world", translation_languages.columns[:N])[0]['translations']).set_index('to')
    test_translations_2 = pd.DataFrame(translate.translate_text("hello world", translation_languages.columns[N:])[0]['translations']).set_index('to')

    test_translations = pd.concat([test_translations, test_translations_2])

    for lang in translation_languages:
        if translate.only_latin_chars(test_translations.loc[lang, 'text']):
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



def count_word_freq(text:list, remove_stopwords:bool=True)->dict:
    """Returns number of occurrences every word in text that is in WordNet database

    Args:
        text (list): List of words
        remove_stopwords (bool): Whether stopwords should be included in the count

    Returns:
        dict: Word -> count. Sorted from highest to lowest
    """

    counts = {}
    word_set = set(word.lower() for word in wordnet.words('eng'))

    if remove_stopwords:
        stop_word_set = set(word.lower() for word in stopwords.words('english'))
        word_set = word_set - stop_word_set

    for word in text:
        if word in word_set:
            word = word.lower()
            counts[word] = counts.get(word, 0) + 1

    counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

    return counts



def add_words_to_data(text:list, path_to_native_data:str, path_to_transliterate_data:str):
    """Add words to data in both native script and transliterations

    Args:
        text (list): List of words
        path_to_native_data (str): path to DataFrame containing translations in native script
        path_to_transliterate_data (str): path to DataFrame containing translations in latin script
    """

    #Get list of languages
    languages = final_languages()

    is_latin = (languages.loc['latin']==True)
    latin_languages = languages.loc[:,is_latin]
    non_latin_languages = languages.loc[:, ~is_latin]

    #Read data
    native_data = pd.read_csv(path_to_native_data, index_col=0)
    transliterate_data = pd.read_csv(path_to_transliterate_data, index_col=0)

    #Filter out words already in data
    text = [word for word in text if word not in native_data.index]

    if not text:
        print('No new words were found')
        return


    print('Translating words')

    #Get latin language translations
    translations = pd.DataFrame(translate.translate_text(text, target_languages=latin_languages.columns), index=pd.Series(text, name="word"))

    latin_translations= translations['translations'].apply(lambda x: pd.Series({trans['to']:trans['text'].lower() for trans in x}))

    #Get non-latin language translations
    translations = pd.DataFrame(translate.translate_text(text, target_languages=non_latin_languages.columns, 
                to_script=["latn"]*len(non_latin_languages.columns)), index=pd.Series(text, name="word"))

    native_translations = translations['translations'].apply(lambda x: pd.Series({trans['to']:trans['text'] for trans in x}))
    transliterations = translations['translations'].apply(lambda x: pd.Series({trans['to']:trans['transliteration']['text'].lower() for trans in x}))

    #Merge the native and latin
    native_translations = native_translations.join(latin_translations)
    latin_translations = latin_translations.join(transliterations)

    #Merge with entire dataset
    print('Merging data')

    native_data = pd.concat([native_data, native_translations])
    transliterate_data = pd.concat([transliterate_data, latin_translations])

    #Write to file
    print('Writing data to files')
    native_data.to_csv(path_to_native_data)
    transliterate_data.to_csv(path_to_transliterate_data)

    return



def add_brown_words(path_to_native_data:str, path_to_transliterate_data:str, num_words:int=100):
    """Add words from brown corpus to data files

    Args:
        path_to_native_data (str): path to DataFrame containing translations in native script
        path_to_transliterate_data (str): path to DataFrame containing translations in latin script
        num_words (int, optional): Number of words to add, sorted by number of occurrences from high to low. Defaults to 100.
    """
    counts = count_word_freq(brown.words(), remove_stopwords=True)
    brown_words = list(pd.Series(counts).iloc[:100].index)

    add_words_to_data(brown_words, path_to_native_data, path_to_transliterate_data)

    return



def add_swadesh_words(path_to_native_data:str, path_to_transliterate_data):
    """Add words from Swadesh corpus to data files

    Args:
        path_to_native_data (str): path to DataFrame containing translations in native script
        path_to_transliterate_data (str): path to DataFrame containing translations in latin script
    """
    swadesh_words = swadesh.words('en')
    swadesh_words = set(pd.Series(swadesh_words).apply(lambda x: x.split()[0]))

    add_words_to_data(swadesh_words, path_to_native_data, path_to_transliterate_data)

    return



def get_asjp_data(path_to_folder:str):
    """Get list of languages, translations, and wordlist from the ASJP

    Args:
        path_to_folder (str): Location of data folder
    """

    print("Downloading data")
    response = requests.get('https://zenodo.org/api/files/e9bcce88-4c35-4c99-9033-0bbee53f5a43/lexibank/asjp-v19.1.zip', allow_redirects=True)

    path_to_zip = os.path.join(path_to_folder, 'asjp-data.zip')

    with open(path_to_zip, 'wb') as f:
        f.write(response.content)

    filemap = {
            'lexibank-asjp-0c18d44/cldf/forms.csv':'asjp-words.csv',
            'lexibank-asjp-0c18d44/cldf/languages.csv': 'asjp-languages.csv',
            'lexibank-asjp-0c18d44/cldf/parameters.csv':'asjp-wordlist.csv'
        }

    print("Extracting data")

    with ZipFile(path_to_zip, 'r') as zipObj:
        for file in filemap:
            with zipObj.open(file, 'r') as f1:
                path_to_data = os.path.join(path_to_folder, filemap[file])
                with open(path_to_data, 'wb') as f2:
                    f2.write(f1.read())

    os.remove(path_to_zip)

    print("Done")

    return



def add_language_families(path_to_folder:str):
    """Add language families from ASJP data to Azure languages

    Args:
        path_to_folder (str): Path to folder containing data
    """

    asjp_languages = pd.read_csv(os.path.join(path_to_folder, "asjp-languages.csv"))
    asjp_languages.dropna(subset=['ISO639P3code', 'Glottolog_Name'], inplace=True)

    languages = pd.read_csv(os.path.join(path_to_folder, "languages.csv"), index_col=0)

    languages.loc['family'] = pd.Series(dtype='object')

    for lang in languages:
        name = languages.loc['name', lang].lower()

        def add_matches(matches):
            if len(matches) and pd.isnull(languages.loc['family', lang]):
                fam = matches['Family'].value_counts().index[0]
                if fam=='Indo-European':
                    languages.loc['family', lang] = matches['classification_glottolog'].value_counts().index[0].split(',')[1]
                    return
                
                languages.loc['family', lang] = fam

        #Match language codes
        matches = asjp_languages[asjp_languages['ISO639P3code']==Language.get(standardize_tag(lang)).to_alpha3()]
        add_matches(matches)
        
        #Match names exactly
        matches = asjp_languages[asjp_languages['Glottolog_Name'].apply(lambda x: name==x.lower())]
        add_matches(matches)

        #Match first word
        matches = asjp_languages[asjp_languages['Glottolog_Name'].apply(lambda x: name.split(' ')[0] in x.lower())]
        add_matches(matches)

        #Add Filipino and Klingon manually
        languages.loc['family', 'fil'] = 'Austronesian'
        languages.loc['family', 'tlh-latn'] = 'Artificial'

    print('Adding language family data')

    languages.to_csv(os.path.join(path_to_folder, "languages.csv"))

    return





if __name__=="__main__":

    print('Generating data')

    path_to_key = input('Enter location of key to authenticate translation service: ')

    translate.authenticate(path_to_key)

    path_to_folder = input('Enter location data folder: ')

    if not os.path.exists(path_to_folder):
        os.mkdir(path_to_folder)

    print('Generating languages accessible to Azure')

    languages = final_languages()

    languages.to_csv(os.path.join(path_to_folder, 'languages.csv'))

    print('Generating ASJP data')

    get_asjp_data(path_to_folder)

    add_language_families(path_to_folder)

    print('Time to add translations in various languages')

    path_to_native_data = os.path.join(path_to_folder, 'data-native.csv')
    path_to_transliterate_data = os.path.join(path_to_folder, 'data-latin.csv')

    empty_data = pd.DataFrame(columns=languages.columns, index=pd.Series(dtype='object', name='word'), dtype='object')

    if not os.path.exists(path_to_native_data):
        empty_data.to_csv(path_to_native_data)

    if not os.path.exists(path_to_transliterate_data):
        empty_data.to_csv(path_to_transliterate_data)

    num_words = input('Number of most frequent words from the Brown corpus to add: ')

    print('Adding words from Brown corpus')

    add_brown_words(path_to_native_data, path_to_transliterate_data, num_words)

    print('Adding words from Swadesh list')

    add_swadesh_words(path_to_native_data, path_to_transliterate_data)

    print('Data generation successfully complete')