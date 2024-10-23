# Convert2Anki

## Excel Conversion

Using OpenAI to generate decksets for learning english/spanish vocabulary based on tabular presentations as known on austrian school books like ( more1, more2, more3 ).
Uses a column spaces layout A, E, Q on the excel sheet:
* A .. Answer = answer, english/spanish vocabulary
* E .. Example = example usage, if missing then added by using OpenAI
* Q .. Question = question, german vocabulary

If an openai api key is passed, then 
* sound of the spoken vocabulary 
* sound of the spoken example usage
* image of the example sentence
* ipa of the vocabulary
is added by using openai api


## Image Conversion

Also an image of the tabular based representation can be passed and is converted to an text table. This file can be downloaded and imported to Excel by importing data from file and using fixdd width column separation.
