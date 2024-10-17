from os.path import join as join_path, exists
from os import getenv, makedirs
from time import sleep
import requests
from json import dumps as json_dumps
from openai import OpenAI
from PIL import Image
from helper import *


class AI:
    client: OpenAI
    output_language = getenv("OUTPUT_LANGUAGE", "english")

    def __init__(self, openapi_key: str, aihub_key: str, media_directory: str = "media"):
        self.client = OpenAI(api_key=openapi_key)
        
        self.media_directory = media_directory
        if not Path(self.media_directory).exists():
            makedirs(self.media_directory)

    def create_tts(self, term: str):
        """Uses OpenAI API to convert input string into speech"""
        filename = f"{ get_hashsum(term) }.mp3"
        path = join_path(self.media_directory, filename)
        if exists(path):
            return path

        response = self.client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=term,
        )
        response.stream_to_file(path)
        return path

    def create_ipa(self, term: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"In this chat, you will act as a writer for teenagers, providing example sentences using the {self.output_language} terms I give you. I will provide you with a term, and you will give an international Phonetic Alphabet representation of that term and nothing else.",
                },
                {"role": "user", "content": json_dumps(term)},
            ],
        )
        return response.choices[0].message.content
        

    def create_example_sentence(self, term: str) -> str:
        """Uses OpenAI API to generate an example sentence using input term"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"In this chat, you will act as a writer for teenagers, providing example sentences using the {self.output_language} terms I give you. I will provide you with a term, and you will give an example sentence using that term and nothing else.",
                },
                {"role": "user", "content": json_dumps(term)},
            ],
        )
        return response.choices[0].message.content

    def create_example_image(self, term: str) -> str:
        filename = f"{ get_hashsum(term) }.png"
        path = join_path(self.media_directory, filename)
        if exists(path):
            return path

        response = self.client.images.generate(
            model="dall-e-3",
            prompt=f"Please create a picture for teenagers, which are learners of {self.output_language}, for the term of {term}",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            return None

        with open(path, "wb") as f:
            f.write(image_response.content)
            
        with Image.open(path) as im:
            (height, width) = im.size
            (width, height) = (im.width // 2, im.height // 2)
            im_resized = im.resize((width, height))
            im_resized.save(path)

        return path
