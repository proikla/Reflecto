from collections import defaultdict


SUPPORTED_LANGUAGES = ['ru', 'en']
TIMEZONES = [('utc', 0), ('europe', 1),
             ('moscow', 3), ('yekaterinburg', 5)]

#! temporary!
messages_to_delete: defaultdict = defaultdict(list)
