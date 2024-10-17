import argparse
from html import escape as html_escape
from os import getenv
import pandas as pd
from pathlib import Path
import re
from sys import argv
import warnings
import genanki
from ai import AI

from helper import *


class AnkiDeck:
    aiclient: AI

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
        aihub_api_key = getenv("AIHUB_API_KEY", "")
        return AI(openai_api_key, aihub_api_key)

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

    def replace_quantifier(self, data: str, isAnswer: bool) -> str:
        count = 0
        for m in re.finditer(self.pattern, data):
            count += 1
            if isAnswer:
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

    def enhance_field(self, data: str, isAnswer: bool = False) -> str:
        data = self.replace_quantifier(data, isAnswer)
        data = html_escape(data)
        data = data.replace("\n", "<br/>")
        data = re.sub(r"[ ]{2,}", " ", data)
        return data

    def data_to_anki(
        self, deck_name: str, data, generate_example: bool = True
    ) -> genanki.Deck:
        deck_id = create_uuid(deck_name)
        my_deck = genanki.Deck(deck_id, deck_name)
        custom_model = self.create_model(deck_name)

        for r in data:
            question = r[self.question_column]
            answer = r[self.answer_column]
            example = ""

            if generate_example:
                if self.example_column in r:
                    example = r[self.example_column]
                if type(example) != type(""):
                    example = self.create_example_sentence(answer)

            answer_replace = re.compile(f"({answer})", flags=re.IGNORECASE)
            if generate_example:
                for m in answer_replace.finditer(example):
                    example = (
                        example[: m.start()]
                        + "{{"
                        + m.group(1)
                        + "}}"
                        + example[m.end() :]
                    )

            raw_example = self.enhance_field(example)
            question = self.enhance_field(question)
            answer = self.enhance_field(answer, isAnswer=True)
            example = self.enhance_field(example, isAnswer=True)

            note = genanki.Note(
                guid = create_uuid(question),
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

            my_deck.add_note(note)

        print(f"Generated {len(data)} notes...")
        return my_deck

    def create_ipa(self, term: str) -> str:
        return self.aiclient.create_ipa(term)

    def create_image(self, term: str) -> str:
        path = self.aiclient.create_example_image(term)
        self.media_files.append(path)
        return f'<img src="{Path(path).name}">'

    def create_tts(self, term: str):
        path = self.aiclient.create_tts(term)
        self.media_files.append(path)
        return f"[sound:{Path(path).name}]"

    def create_example_sentence(self, term: str) -> str:
        return self.aiclient.create_example_sentence(term)

    def process_image(self, filename: str) -> str:
        # current = Path(filename)
        # data_filename = current.with_suffix(".xlsx")
        data = extract_table_from_img(filename)
        # data =  data.replace("\n", "<br/>")
        # data = data.replace(" ", "&nbsp;")
        return data
        # data.to_excel(data_filename)
        # return data_filename

    def processExcel(self, filename: str, output: str = None) -> str:
        current = Path(filename)
        anki_filename = current.with_suffix(".apkg")
        data = load_excel(current)
        self.process_data(anki_filename, data)
        return anki_filename

    def process_data(self, anki_filename: str, data):
        deck = self.data_to_anki(anki_filename.with_suffix("").name, data)
        with warnings.catch_warnings(record=True) as warning_list:
            package = genanki.Package(deck)
            package.media_files = self.media_files
            package.write_to_file(anki_filename)

        assert not warning_list

        print(f"Generated {anki_filename} successfully...")

        return anki_filename
