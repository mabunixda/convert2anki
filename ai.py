from os.path import join as join_path, exists
from os import makedirs
from json import dumps as json_dumps
from pathlib import Path
import shutil
import requests
from ollama import Client as OllamaClient
from PIL.PngImagePlugin import PngInfo
from helper import get_id, get_hashsum
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import torch
import soundfile as sf
import webuiapi as sd


speakers = {
    "awb": 0,  # Scottish male
    "bdl": 1138,  # US male
    "clb": 2271,  # US female
    "jmk": 3403,  # Canadian male
    "ksp": 4535,  # Indian male
    "rms": 5667,  # US male
    "slt": 6799,  # US female
}


class AI:
    ollama: OllamaClient = None
    output_language: str = "english"

    def __init__(
        self,
        openapi_key: str,
        media_directory: str = "media",
        language: str = "english",
    ):
        self.output_language = language
        self.media_directory = media_directory
        if not Path(self.media_directory).exists():
            makedirs(self.media_directory)
        self.ollama = OllamaClient(host="http://ollama.service.consul:11434")
        
        self.sd = sd.WebUIApi(host="stable-diffusion.service.consul", port=7860,steps = 10)
        options = {}
        options['sd_model_checkpoint'] = 'anything-v3-fp16-pruned.safetensors [d1facd9a2b]'
        self.sd.set_options(options)
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        self.model = SpeechT5ForTextToSpeech.from_pretrained(
            "microsoft/speecht5_tts"
        ).to(self.device)
        self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(
            self.device
        )
        self.embeddings_dataset = load_dataset(
            "Matthijs/cmu-arctic-xvectors", split="validation"
        )

    def set_language(self, language: str) -> None:
        self.output_language = language

    def create_tts(self, term: str, speaker: str = speakers["bdl"]):
        """Uses OpenAI API to convert input string into speech"""

        filename = join_path(self.media_directory, f"{ get_id(term) }.mp3")
        old_filename = join_path(self.media_directory, f"{ get_hashsum(term) }.mp3")
        if exists(old_filename):
            shutil.move(old_filename, filename)

        if exists(filename):
            return filename

        if self.ollama == None:
            return ""

        try:
            inputs = self.processor(text=term, return_tensors="pt").to(self.device)
            if speaker is not None:
                # load xvector containing speaker's voice characteristics from a dataset
                speaker_embeddings = (
                    torch.tensor(self.embeddings_dataset[speaker]["xvector"])
                    .unsqueeze(0)
                    .to(self.device)
                )
            else:
                # random vector, meaning a random voice
                speaker_embeddings = torch.randn((1, 512)).to(self.device)
            # generate speech with the models
            speech = self.model.generate_speech(
                inputs["input_ids"], speaker_embeddings, vocoder=self.vocoder
            )            
            sf.write(filename, speech.cpu().numpy(), samplerate=16000)
            return filename
        except BaseException as exc:
            print(f"{term} caused problem: {exc}")
            pass

        return ""

    def create_ipa(self, term: str) -> str:
        filename = join_path(self.media_directory, f"{ get_id(term) }.ipa")

        if exists(filename):
            with open(filename) as f:                  
                return f.readline()
        if self.ollama == None:
            return ""
        try:
            response = self.ollama.chat(
                model="llama3.2",
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
            ipa =  response["message"]["content"]
            with open(filename, "w") as f:
                f.write(ipa)
            return ipa
        except BaseException as exc:
            print(f"{term} caused problem: {exc}")
            pass
        return ""

    def create_example_sentence(self, term: str) -> str:
        """Uses OpenAI API to generate an example sentence using input term"""

        filename = join_path(self.media_directory, f"{ get_id(term) }.example")

        if exists(filename):
            with open(filename) as f:                  
                return f.readline()

        if self.ollama == None:
            return ""

        try:
            response = self.ollama.chat(
                model="llama3.2",
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
            sentence = response["message"]["content"]
            with open(filename, "w") as f:
                f.write(sentence)
            return sentence
        except BaseException as exc:
            print(f"{term} caused problem: {exc}")
            pass
        return ""

    def create_example_image(self, term: str) -> str:
        filename = join_path(self.media_directory, f"{ get_id(term) }.png")
        old_filename = join_path(self.media_directory, f"{ get_hashsum(term) }.png")

        if exists(old_filename):
            shutil.move(old_filename, filename)

        if exists(filename):
            return filename

        if self.ollama == None:
            return ""

        try:
            response = self.ollama.chat(
                model="llama3.2",
                messages=[
                    {
                        "role": "system",
                        "content": f"""In this chat, you will act as a writer of description for stable diffusion that illustrates 
                        sentences for teenagers using the {self.output_language} terms I give you. 
                        I will provide you with a term, and you will give an description for stable diffusion using that term and nothing else.""",
                    },
                    {"role": "user", "content": json_dumps(term)},
                ],
            )
            descriptive = response["message"]["content"]
            
            sd_result = self.sd.txt2img(
                    prompt=descriptive,
                    negative_prompt="nude, bad anatomy, bad hands, three hands, three legs, bad arms, missing legs, missing arms, poorly drawn face, bad face, fused face, cloned face, worst face, out of frame double, three crus, extra crus, fused crus, worst feet, three feet, fused feet, fused thigh, three thigh, extra thigh, worst thigh, missing fingers, extra fingers, ugly fingers, long fingers, horn, realistic photo, extra eyes, huge eyes, 2girl, 2boy, amputation, disconnected limbs",
                    seed=2912044817,
                    cfg_scale=7,
                    sampler_name="DPM++ 2M",
                    scheduler="Karras",
                    )
            metadata = PngInfo()
            metadata.add_text("Term", term)
            metadata.add_text("ollama", descriptive)
            sd_result.image.save(filename, pnginfo=metadata)

            return filename
            
        except BaseException as bre:
            print(f"{term} caused problem: {bre}")
        return ""


