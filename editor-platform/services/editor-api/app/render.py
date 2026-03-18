import re
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from app.sanitize import sanitize_html

md = MarkdownIt()

SNIP_RE = re.compile(r"\[\[html_snippet:(.*?)\]\]")

def html_to_text(html: str):
    return BeautifulSoup(html, "html.parser").get_text()

def render_markdown(content_md: str):
    html = md.render(content_md)
    html = sanitize_html(html)
    text = html_to_text(html)
    return html, text