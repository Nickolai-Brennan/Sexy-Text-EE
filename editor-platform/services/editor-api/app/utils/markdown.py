from markdown_it import MarkdownIt

md = MarkdownIt("commonmark")

def markdown_to_html(markdown: str) -> str:
    return md.render(markdown or "")
