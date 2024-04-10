import mistune
import html2markdown

class FormattedText:    
    html = ""

    def __init__(
            self,
            markdown: str = None,
            html: str = None
    ) -> None:
        if html is not None:
            self.html = html
        elif markdown is not None:
            self.html = mistune.markdown(markdown)

    @property
    def is_empty(self) -> bool:
        return self.html == ""

    def __eq__(self, other) -> False:
        if type(other) != type(self):
            return False
        if self.is_empty and other.is_empty:
            return True

        return self.doc == other.doc

    @property
    def markdown(self) -> str:
        return html2markdown.convert(self.html)

    def __str__(self) -> str:
        return self.markdown

    plaintext = markdown
    
