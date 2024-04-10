class DownloadException(Exception):
    pass


class UrlNotFoundException(DownloadException):
    def __init__(self, url: str, *args: object) -> None:
        self.url = url
        super().__init__(*args)
        
    def __str__(self) -> str:
        return f"Couldn't find the page of {self.url}"
