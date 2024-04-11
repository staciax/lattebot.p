from typing import Literal

# Markdown Text 101 (Chat Formatting: Bold, Italic, Underline)
# https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-

# text formatting


def bold(text: str) -> str:
    """Returns a bolded string"""
    return f'**{text}**'


def bold_italics(text: str) -> str:
    """Returns a bolded italicized string"""
    return f'***{text}***'


def strikethrough(text: str) -> str:
    """Returns a strikethrough string"""
    return f'~~{text}~~'


def spoiler(text: str) -> str:
    """Returns a spoiler string"""
    return f'||{text}||'


def italics(text: str) -> str:
    """Returns an italicized string"""
    return f'*{text}*'


def italics2(text: str) -> str:
    """Returns an italicized string"""
    return f'_{text}_'


def underline(text: str) -> str:
    """Returns an underlined string"""
    return f'__{text}__'


def underline_bold(text: str) -> str:
    """Returns an underlined bolded string"""
    return f'__**{text}**__'


def underline_italics(text: str) -> str:
    """Returns an underlined italicized string"""
    return f'__*{text}*__'


def underline_bold_italics(text: str) -> str:
    """Returns an underlined bolded italicized string"""
    return f'__***{text}***__'


def inline(text: str) -> str:
    """Returns an inline string"""
    if '`' in text:
        return f'``{text}``'
    else:
        return f'`{text}`'


# organizational text formatting


def headers(text: str, level: Literal[1, 2, 3] = 1) -> str:
    """Returns a header string"""
    if level == 1:
        return f'# {text}'
    elif level == 2:
        return f'## {text}'
    elif level == 3:
        return f'### {text}'
    else:
        raise ValueError('level must be 1, 2, or 3')


def masked_links(text: str, link: str) -> str:
    """Returns a masked link string"""
    return f'[{text}]({link})'


def lists(text: str, level: int = 1) -> str:
    """Returns a list string"""
    return ' ' * level + f'- {text}'


def code_block(text: str, lang: str = '') -> str:
    """Returns a codeblock string"""
    return f'```{lang}\n{text}```'


def block_quotes(text: str, multi: bool = False) -> str:
    """Returns a block quote string"""
    if multi:
        return f'> {text}'
    else:
        return f'>>> {text}'
