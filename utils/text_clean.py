# utils/text_clean.py
import re
def clean_text(s: str):
    s = str(s).lower()
    s = re.sub(r'http\\S+', ' <URL> ', s)
    s = re.sub(r'@\\w+', ' <MENTION> ', s)
    s = re.sub(r'\\d+', ' <NUM> ', s)
    s = re.sub(r'\\s+', ' ', s).strip()
    return s
