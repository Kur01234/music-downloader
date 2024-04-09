from datetime import date


def get_elem_from_obj(current_object, keys: list, after_process=lambda x: x, return_if_none=None):
    current_object = current_object
    for key in keys:
        if key in current_object or (type(key) == int and key < len(current_object)):
            current_object = current_object[key]
        else:
            return return_if_none
    return after_process(current_object)


def parse_music_brainz_date(mb_date: str) -> date:
    year = 1
    month = 1
    day = 1

    first_release_date = mb_date
    if first_release_date.count("-") == 2:
        year, month, day = [int(i) for i in first_release_date.split("-")]
    elif first_release_date.count("-") == 0 and first_release_date.isdigit():
        year = int(first_release_date)
    return date(year, month, day)
