from os.path import join as join_path, exists
from os import makedirs
from json import dumps as json_dumps
from pathlib import Path
import requests
from openai import OpenAI, BadRequestError
from PIL import Image
from helper import get_hashsum


class AI:
    client: OpenAI = None
    output_language: str = "english"
    
    def __init__(self, openapi_key: str, media_directory: str = "media", language: str = "english"):
        self.output_language = language        
        self.media_directory = media_directory
        if not Path(self.media_directory).exists():
            makedirs(self.media_directory)
        if openapi_key != "": 
            self.client = OpenAI(api_key=openapi_key)

    def set_language(self, language: str) -> None:
        self.output_language = language

    def create_tts(self, term: str):
        """Uses OpenAI API to convert input string into speech"""
        
        filename = f"{ get_hashsum(term) }.mp3"
        path = join_path(self.media_directory, filename)
        if exists(path):
            return path

        if self.client == None:
            return ""

        response = self.client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=term,
        )
        response.stream_to_file(path)
        return path

    def create_ipa(self, term: str) -> str:
        if self.client == None:
            return ""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"""In this chat, you will act as a writer for teenagers, 
                        providing example sentences using the {self.output_language} terms I give you. 
                        I will provide you with a term, and you will give an international Phonetic Alphabet representation 
                        of that term and nothing else.""",
                    },
                    {"role": "user", "content": json_dumps(term)},
                ],
            )
            return response.choices[0].message.content
        except BadRequestError as bre:
            print(f"{term} caused problem: {bre}")
            return ""
        
    def create_example_sentence(self, term: str) -> str:
        """Uses OpenAI API to generate an example sentence using input term"""

        if self.client == None:
            return ""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""In this chat, you will act as a writer for teenagers, 
                        providing example sentences using the {self.output_language} terms I give you. 
                        I will provide you with a term, and you will give an example sentence using that term and nothing else.""",
                    },
                    {"role": "user", "content": json_dumps(term)},
                ],
            )
            return response.choices[0].message.content
        except BadRequestError as bre:
            print(f"{term} caused problem: {bre}")
            return ""
        
    def create_example_image(self, term: str) -> str:
        filename = f"{ get_hashsum(term) }.png"
        path = join_path(self.media_directory, filename)
        if exists(path):
            return path

        if self.client == None:
            return ""

        image_url: str = None
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=f"Please create a picture for teenagers, which are learners of {self.output_language}, for the term of {term}",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
        except BadRequestError as bre:
            print(f"{term} caused problem: {bre}")
            image_url = None
            
        if image_url is None:
            return ""
        
        image_response = requests.get(image_url, timeout=120)
        if image_response.status_code != 200:
            return ""

        with open(path, "wb") as f:
            f.write(image_response.content)
            
        with Image.open(path) as im:
            (height, width) = im.size
            (width, height) = (im.width // 2, im.height // 2)
            im_resized = im.resize((width, height))
            im_resized.save(path)

        return path
