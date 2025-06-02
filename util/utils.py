# import json
# import os
# from datetime import UTC, datetime


# def format_date(dt: datetime, include_time: bool = True) -> str:
#     if include_time:
#         return dt.strftime("%d.%m.%y %H:%M")
#     else:
#         return dt.strftime("%d.%m.%y")


# def process_entry_json(json_entry: str, chat_id: str):
#     '''
#     Reads entry json and puts it in the right place.
#     '''

#     today = format_date(datetime.now(UTC), include_time=False)
#     dir = os.path.dirname(os.path.abspath(__file__))
#     # ensure the path exists. ie: /users/1242141/01.05.25/
#     if not os.path.exists(f'{dir}/users/'):
#         os.mkdir(f'{dir}/users/')

#     if not os.path.exists(f'{dir}/users/{chat_id}'):
#         os.mkdir(f'{dir}/users/{chat_id}/')

#     if not os.path.exists(f'{dir}/users/{chat_id}/{today}'):
#         os.mkdir(
#             f'{dir}/users/{chat_id}/{today}')

#     # json entry example:
#     # {
#     # "date_time": "01.05.25",
#     # "entry": "Привет! Я поел, проснулся, чувствую себя хорошо, настроение отличное. Думаю над планами на день.",
#     # "plans": ["умыться", "доделать мою нейросеть"],
#     # "done": ["поел", "проснулся"]
#     # }

#     # parse json entry
#     data = json.loads(json_entry)

#     final_json_path = f'{dir}/users/{chat_id}/{today}/final.json'

#     if not os.path.exists(final_json_path):
#         with open(final_json_path, 'x') as file:
#             file.write(json.dumps([data], ensure_ascii=False))

#     else:
#         with open(final_json_path, 'r') as r:
#             entries: list = json.loads(r.read())

#         with open(final_json_path, 'w') as w:
#             entries.append(data)
#             w.write(json.dumps(entries, ensure_ascii=False))
