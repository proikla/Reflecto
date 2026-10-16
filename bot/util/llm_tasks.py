# stdlib
import io
import os

# third-party
from openai import AsyncOpenAI
import loguru

#
from util import prompts

logger = loguru.logger


# local
DEEPSEEK_KEY = os.getenv('DSAPI')
WHISPER_KEY = os.getenv('WHISPER')

class LLMService:
    def __init__(self):
        self.deepseek_client = AsyncOpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        self.whisper_client = AsyncOpenAI(api_key=WHISPER_KEY)

    async def transcribe(self, audio: bytes) -> str:
        audio_file = io.BytesIO(audio)
        audio_file.name = "audio.ogg"  # Use the actual format

        response = await self.whisper_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

        text = response.text
        logger.info("Transcribed text: {}", text)
        return text

    async def prompt_deepseek(self,sysprompt: str, usrprompt: str, model="deepseek-chat"):
        async with AsyncOpenAI(
            api_key=DEEPSEEK_KEY,
            base_url="https://api.deepseek.com"
        ) as client:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sysprompt.strip()},
                    {"role": "user", "content": usrprompt.strip()}
                ]
            )

        return response.choices[0].message.content

    async def generate_morning_message(self,user_context: str) -> str:
        response = await self.prompt_deepseek(prompts.morning_message_prompt, user_context)
        return response[response.find("/think>") + 7 : :].strip() #? may fuck up the response.


    def get_discipline_level_from_entry(entry) -> str: ...  # TODO


    async def make_day_summary(self,
        entries, user_context=""
    ) -> str:  # TODO: should also renew user context! see TODO.md

        user_context = ""
        usr_prompt = f"""
    INPUT:
    DIARY_ENTRIES: {entries}
    USER_CONTEXT: {user_context}
    """
        response = await self.prompt_deepseek(prompts.day_summary_prompt, usr_prompt)
        return response[response.find("/think>") + 7 : :].strip() #? probably fucks up the response.


    async def get_json_from_journal_entry(self,entry_text) -> str:
        response = await self.prompt_deepseek(prompts.get_json_from_entry_prompt, entry_text)
        # todo check if the json is valid.
        return response.strip()
