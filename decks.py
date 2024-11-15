import asyncio
from threading import Lock
from html import escape as html_escape
from os import getenv
from pathlib import Path
import re
import warnings
import genanki
import pandas as pd
from ai import AI

from helper import create_uuid, read_template, extract_table_from_img, load_excel


class AnkiDeck:
    aiclient: AI

    lock = Lock()
    media_files = []
    question_column = getenv("COL_QUESTION", "Q")
    answer_column = getenv("COL_ANSWER", "A")
    example_column = getenv("COL_EXAMPLE", "E")
    pattern = re.compile(r"\{\{(.*)\}\}")

    frontside_template = read_template("frontside.html")

    backside_template = read_template("backside.html")
    style = read_template("cards_style.css")

    def __init__(self):
        self.aiclient = self.create_ai()

    def create_ai(self):
        openai_api_key = getenv("OPENAI_API_KEY", "")
        return AI(openai_api_key)

    def create_model(self, name: str) -> genanki.Model:
        model_id = create_uuid()
        model = genanki.Model(
            model_id,
            f"{name} (Model)",
            fields=[
                {"name": "input_term"},
                {"name": "input_example"},
                {"name": "output_term"},
                {"name": "output_audio"},
                {"name": "ipa"},
                {"name": "example_sentence"},
                {"name": "example_audio"},
                {"name": "output_image"},
            ],
            templates=[
                {
                    "name": f"{name} Cloze",
                    "qfmt": self.frontside_template,
                    "afmt": self.backside_template,
                }
            ],
            css=self.style,
        )
        return model

    def replace_quantifier(self, data: str, is_answer: bool) -> str:
        count = 0
        for m in re.finditer(self.pattern, data):
            count += 1
            if is_answer:
                data = data[: m.start()] + m.group(1) + data[m.end() :]
            else:
                data = (
                    data[: m.start()]
                    + "{{"
                    + f"c{count}::{m.group(1)}"
                    + "}}"
                    + data[m.end() :]
                )

        return data

    def enhance_field(self, data: str, is_answer: bool = False) -> str:
        if data == None or data == "":
            return data
        data = self.replace_quantifier(data, is_answer)
        data = html_escape(data)
        data = data.replace("\n", "<br/>")
        data = re.sub(r"[ ]{2,}", " ", data)
        return data

    async def _process_item(
        self, r: dict, custom_model: str, generate_example: bool
    ) -> genanki.Note:
        question = r[self.question_column]
        answer = r[self.answer_column]
        example = ""

        if generate_example:
            if self.example_column in r:
                example = r[self.example_column]
            if not isinstance(example, str):
                example = self.create_example_sentence(answer)

        answer_replace = re.compile(f"({answer})", flags=re.IGNORECASE)
        if generate_example and example != None:
            for m in answer_replace.finditer(example):
                example = (
                    example[: m.start()] + "{{" + m.group(1) + "}}" + example[m.end() :]
                )

        raw_example = self.enhance_field(example)
        question = self.enhance_field(question)
        answer = self.enhance_field(answer, is_answer=True)
        example = self.enhance_field(example, is_answer=True)

        note = genanki.Note(
            guid=create_uuid(question),
            sort_field=question,
            model=custom_model,
            fields=[
                question,
                raw_example,
                answer,
                self.create_tts(answer),
                self.create_ipa(answer),
                example,
                self.create_tts(example),
                self.create_image(example),
            ],
        )
        return note


    async def _data_to_anki(
        self, deck_name: str, data, generate_example: bool = True
    ) -> genanki.Deck:
        deck_id = create_uuid(deck_name)
        my_deck = genanki.Deck(deck_id, deck_name)
        custom_model = self.create_model(deck_name)

        tasks = [asyncio.create_task(self._process_item(r,  custom_model=custom_model, generate_example=generate_example)) for r in data]
        done,pending = await asyncio.wait(tasks)
        for i in range(len(done)):
            note = done.pop().result()
            my_deck.add_note(note)

        return my_deck        

    def data_to_anki(
        self, deck_name: str, data, generate_example: bool = True
    ) -> genanki.Deck:

        my_deck = asyncio.run(self._data_to_anki(deck_name, data, generate_example))

        return my_deck

    def create_ipa(self, term: str) -> str:
        return self.aiclient.create_ipa(term)

    def create_image(self, term: str) -> str:
        path = self.aiclient.create_example_image(term)
        if path == None or path == "":
            return path
        self.media_files.append(path)
        return f'<img src="{Path(path).name}">'

    def create_tts(self, term: str):
        path = self.aiclient.create_tts(term)
        if path == None or path == "":
            return path
        self.media_files.append(path)
        return f"[sound:{Path(path).name}]"

    def create_example_sentence(self, term: str) -> str:
        return self.aiclient.create_example_sentence(term)

    def process_image(self, filename: str, language: str) -> pd.DataFrame:
        data = ""
        with self.lock:
            self.aiclient.set_language(language)
            data = extract_table_from_img(filename, language)

        return data

    def process_excel(self, filename: str, language: str) -> str:
        current = Path(filename)
        anki_filename = current.with_suffix(".apkg")
        data = load_excel(current)
        with self.lock:
            self.aiclient.set_language(language)
            self.process_data(anki_filename, data)

        return anki_filename

    def process_data(self, anki_filename: str, data):
        deck = self.data_to_anki(anki_filename.with_suffix("").name, data)
        with warnings.catch_warnings(record=True) as warning_list:
            package = genanki.Package(deck)
            package.media_files = self.media_files
            package.write_to_file(anki_filename)

        return anki_filename
