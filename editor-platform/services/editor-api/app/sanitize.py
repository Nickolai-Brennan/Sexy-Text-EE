import bleach

ALLOWED_TAGS = [
    "div","span","p","br","strong","em","ul","ol","li",
    "h1","h2","h3","h4","h5","h6","pre","code","a","img","iframe"
]

ALLOWED_ATTRS = {
    "*": ["class","id"],
    "a": ["href","target","rel"],
    "img": ["src","alt","width","height"],
    "iframe": ["src","width","height"]
}

def sanitize_html(html: str):
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )