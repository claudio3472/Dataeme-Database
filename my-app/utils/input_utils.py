import re

def get_input(prompt, pattern, error_msg, cast=str):

    while True:

        value = input(prompt).strip()

        if re.fullmatch(pattern, value):

            try:
                return cast(value)

            except ValueError:
                pass

        print(error_msg)