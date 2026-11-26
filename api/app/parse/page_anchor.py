# LightRAG file_path 里的页锚点：制度.pdf#page=12。page 从 1 起。


def split_page_anchor(file_path: str) -> tuple[str, int | None]:
    name, sep, rest = file_path.partition("#page=")
    if not sep:
        return file_path, None
    try:
        page = int(rest)
    except ValueError:
        return name, None
    if page < 1:
        return name, None
    return name, page
