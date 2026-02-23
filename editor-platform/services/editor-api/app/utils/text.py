from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator="\n")
    # collapse excessive blank lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = []
    for ln in lines:
        if ln == "" and (out and out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip()
