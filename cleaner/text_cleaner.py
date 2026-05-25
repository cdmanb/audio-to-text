"""中文转写文本清洗 —— 去除语气词、口头禅、重复内容"""

import re


FILLER_WORDS = [
    "啊", "嗯", "哦", "呃", "嘛", "呢", "吧", "呀", "哇", "哈",
    "呵", "诶", "唉", "哎", "噢", "哟", "咳咳", "哼", "唔",
]

FILLER_PHRASES = [
    "就是说", "那个", "这个", "然后", "反正", "对吧", "你知道",
    "怎么说呢", "怎么说", "就是说呢", "那个那个", "这个这个",
    "然后呢", "然后然后", "对不对", "是不是", "你知道吗",
    "说白了", "实话实说", "说白了就是", "其实吧",
    "这样子", "这一块", "这方面", "的话",
]


def clean_text(text: str, remove_fillers: bool = True, remove_repetitions: bool = True) -> str:
    """清洗转写文本"""
    text = _remove_asr_metadata(text)
    text = _remove_english_and_symbols(text)
    if remove_fillers:
        text = _remove_filler_phrases(text)
        text = _remove_filler_words(text)
    if remove_repetitions:
        text = _remove_repetitions(text)
        text = _remove_consecutive_duplicates(text)
    return _normalize_whitespace(text)


def _remove_english_and_symbols(text: str) -> str:
    """移除英文单词、特殊符号、乱码"""
    # 连续 ASCII 字母组成的单词
    text = re.sub(r"[a-zA-Z]{2,}", "", text)
    # 特殊符号（保留中文标点、换行）
    text = re.sub(r"[*#@$%^&(){}\[\]=+|\\/~`<>]", "", text)
    return text


def _remove_asr_metadata(text: str) -> str:
    """移除 ASR 标记：时间戳、Speaker 标签等"""
    # *Speaker1 00:00-00:02* 或 *Speaker2 02:35-02:39*
    text = re.sub(r"\*?Speaker\d+\s+\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?\*?", "", text)
    # 独立时间戳 00:00-00:02 或 00:00
    text = re.sub(r"\b\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?\b", "", text)
    return text


def _remove_filler_words(text: str) -> str:
    for w in FILLER_WORDS:
        text = text.replace(w, "")
    return text


def _remove_filler_phrases(text: str) -> str:
    for phrase in FILLER_PHRASES:
        text = text.replace(phrase, "")
    return text


def _remove_repetitions(text: str) -> str:
    """去除连续重复2次以上的短句（如'好的好的好的' -> '好的'）"""
    return re.sub(r"(.{2,6})\1{1,}", r"\1", text)


def _remove_consecutive_duplicates(text: str) -> str:
    """去除连续重复词语（如'我们我们明天' -> '我们明天'）"""
    return re.sub(r"(.{2,4})\1", r"\1", text)


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[，]{2,}", "，", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"[ \t]+", "", text)  # 压缩空格/制表符，保留换行
    text = re.sub(r"，+", "，", text)
    text = re.sub(r"。+", "。", text)
    return text.strip()
