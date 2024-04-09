import pandoc

"""
TODO
implement in setup.py a skript to install pandocs
https://pandoc.org/installing.html

!!!!!!!!!!!!!!!!!!IMPORTANT!!!!!!!!!!!!!!!!!!
"""


class FormattedText:
    """
    the self.html value should be saved to the database
    """
    
    doc = None

    def __init__(
            self,
            plaintext: str = None,
            markdown: str = None,
            html: str = None
    ) -> None:
        self.set_plaintext(plaintext)
        self.set_markdown(markdown)
        self.set_html(html)

    def set_plaintext(self, plaintext: str):
        if plaintext is None:
            return
        self.doc = pandoc.read(plaintext)

    def set_markdown(self, markdown: str):
        if markdown is None:
            return
        self.doc = pandoc.read(markdown, format="markdown")

    def set_html(self, html: str):
        if html is None:
            return
        self.doc = pandoc.read(html, format="html")

    def get_markdown(self) -> str:
        if self.doc is None:
            return ""
        return pandoc.write(self.doc, format="markdown").strip()

    def get_html(self) -> str:
        if self.doc is None:
            return ""
        return pandoc.write(self.doc, format="html").strip()

    def get_plaintext(self) -> str:
        if self.doc is None:
            return ""
        return pandoc.write(self.doc, format="plain").strip()

    @property
    def is_empty(self) -> bool:
        return self.doc is None

    def __eq__(self, other) -> False:
        if type(other) != type(self):
            return False
        if self.is_empty and other.is_empty:
            return True

        return self.doc == other.doc
    
    def __str__(self) -> str:
        return self.plaintext



    plaintext = property(fget=get_plaintext, fset=set_plaintext)
    markdown = property(fget=get_markdown, fset=set_markdown)
    html = property(fget=get_html, fset=set_html)
