# stdlib
import io
import os

# third-party
from huggingface_hub import InferenceClient
import loguru
from openai import AsyncOpenAI, OpenAI

# local
DEEPSEEK_KEY = os.getenv('DSAPI')
WHISPER_KEY = os.getenv('WHISPER')

class LLMService:
    def __init__(self, api_key: str = None):
        self.deepseek_client = AsyncOpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")


logger = loguru.logger
whisper_client = AsyncOpenAI(api_key=WHISPER_KEY)

async def transcribe(audio: bytes) -> str:
    audio_file = io.BytesIO(audio)
    audio_file.name = "audio.ogg"  # Use the actual format

    response = await whisper_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )

    text = response.text
    logger.info("Transcribed text: {}", text)
    return text

def prompt_whisper(audio: bytes):

    if not audio:
        return False
    client = InferenceClient(
        provider="hf-inference",
        api_key=f"{DEEPSEEK_KEY}",
        headers={"Content-Type": "audio/ogg"},
    )
    response = client.automatic_speech_recognition(
        audio, model="openai/whisper-large-v3-turbo"
    )

    print("RECOGNIZED TEXT FROM VOICE:", response.text)
    return response.text


# def prompt_deepseek(sysprompt: str, usrprompt: str, model="deepseek-ai/DeepSeek-R1"%:
#     client = InferenceClient(api_key=DEEPSEEK_KEY, provider="novita")

#     messages = [
#         {"role": "system", "content": f"{sysprompt.strip()}"},
#         {"role": "user", "content": f"{usrprompt.strip()}"},
#     ]

#     completion = client.chat.completions.create(
#         model=model,
#         messages=messages,
#         max_tokens=0,  # change maybe
#         temperature=0.4,  # fosho change da thang
#     )

#     reply = completion.choices[0].message.content  # tf is choices #?
#     return reply


async def prompt_deepseek(sysprompt: str, usrprompt: str, model="deepseek-chat"):
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

# * PROMPTS:
async def generate_morning_message(user_context: str) -> str:
    prompt = f"""
You're a morning message generator. You will get user context in JSON format and return a morning message based on it.
Your task is to encrourage user to plan their day and to finish their long-term tasks (see CONTEXT). You should also remind user to do their unfinished yesterday's tasks.
"""

    response = await prompt_deepseek(prompt, user_context)
    return response[response.find("/think>") + 7 : :].strip()


def get_discipline_level_from_entry(entry) -> str: ...  # TODO


async def make_day_summary(
    entries, user_context=""
) -> str:  # TODO: should also renew user context! see TODO.md

    user_context = ""
    prompt = f"""
You are a **Daily Summary Report Generator**.  
Your task: from the user’s diary entries and existing context, produce  
1. A **one-page summary** (tone, productivity rating, achievements, shortcomings, unfinished tasks)  

INSTRUCTIONS

1. Inputs:
   - **DIARY_ENTRIES**: the full text of the user's diary (may include “Planned Tasks” and “Completed Tasks” sections).
   - **USER_CONTEXT**: structured text or JSON containing previously accumulated information about habits, goals, preferences, etc.

2. Analysis:
   a) **Emotional Tone**  
      - Analyze the tone and emotional markers in the entries (stress, motivation, fatigue, etc.).
   b) **Productivity (1–10)**  
      - Rate based on the number/importance of completed and uncompleted tasks and the emotional tone. Consider lowering it if the user did not complete all tasks.
   c) **ACHIEVEMENTS**  
      - List only the most significant accomplishments that demonstrate progress toward key goals or outstanding results (e.g. finished a major project, learned a new skill, helped a colleague), excluding routine or trivial tasks. No brackets.
   d) **SHORTCOMINGS**  
      - Errors, oversights, procrastination. Brief, one to two sentences. No brackets.
   e) **Unfinished Tasks**  
      - A list of planned but uncompleted tasks.

3. Report Format:
   - **Starting Tags**: on the first line, output one of the most relevant hashtags from 
     `["productivity","emotions","procrastination","goals","health","motivation","focus","rest"]` that reflects the main theme of the day; if no key theme applies, output only `#routine`.
   - **Отчет о продуктивности %dd.mm.yy**:
     1. Оценка продуктивности: X/10

     2. ДОСТИЖЕНИЯ:  
        - …

     3. НЕДОСТАТКИ:  
        - …

     4. Невыполненные задачи:  
        - …

4. Rules:
   - **Language consistency** — automatically detect the language of the DIARY_ENTRIES input and generate every part of the report (hashtags, section headings, and content) in that SAME language. 
   - **No advice or recommendations** — only what is specified.

"""
    usr_prompt = f"""INPUT:
DIARY_ENTRIES: {entries}
USER_CONTEXT: {user_context}
"""
    response = await prompt_deepseek(prompt, usr_prompt)
    # return response
    return response[response.find("/think>") + 7 : :].strip()


async def get_json_from_journal_entry(entry_text) -> str:
    prompt = f"""
Ты — генератор кратких дневниковых записей. Твоя задача:
1. Принять на вход:
— ТЕКСТ_ЗАПИСИ
2. Проанализировать текст и вернуть ровно один JSON-объект без каких-либо дополнительных символов, комментариев или пояснений, без цензуры.

Структура выходного JSON:
{{
"entry": "...",             // пересказ ТЕКСТ_ЗАПИСИ от первого лица: убрать слова-паразиты, паузы и вводные «э-э», «ну», «типа» и т.п., но сохранить все выражения эмоций (восклицания, междометия, интонационные маркеры) и ключевые эмоционально-окрашенные фразы
"plans": [...],             // список всех запланированных дел из текста (то, что будет сделано)
"done": [...],             // список уже выполненных дел из текста (то, что уже сделано)
"mood": integer              // уровень настроения пользователя (от 1 до 10) исходя из текста. Если у пользователя плохое настроение - ставь низкую оценку.
}}

RULES:
- ничего лишнего, только валидный JSON.
- ответ не должен включать символ `
- ничего не придумывай. только данные из ТЕКСТ_ЗАПИСИ.
"""

    prompt = f"""You are a diary-entry JSON generator. When given TEXT_ENTRY, output exactly one JSON object (in the same language), without code fences or extra formatting. The object must have:

{{
  "entry": "...",   // first-person paraphrase of TEXT_ENTRY without filler words but preserving emotional tone
  "plans": [...],   // list of all tasks the author plans to do
  "done": [...],    // list of all tasks already completed
  "mood": n         // integer 1–10 inferred from TEXT_ENTRY (1 = very bad, 10 = very good)
}}

Use only information explicitly stated in TEXT_ENTRY. Output valid JSON and nothing else.
    """

    response = await prompt_deepseek(prompt, entry_text)
    # todo check if the json is valid.
    return response.strip()


# !testing
if __name__ == "__main__":
    # ...
    # print(make_day_summary_from_json(
    #     'C:\\Users\\adm\\coding\\AiTelegramBotJournal\\users\\483273070\\06.05.25\\final.json'))
    ...
