def comment(uncommented_string: str) -> str:
    _fragments = uncommented_string.split("\n")
    _fragments = ["# " + frag for frag in _fragments]
    return "\n".join(_fragments)
