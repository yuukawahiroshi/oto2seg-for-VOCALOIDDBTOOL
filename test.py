from functions import *
from lang.jpn_common import JapaneseLanguageTool
from phoneme import *

oto_aliases = ["- u", "- う", "- da", "- d", "- だ", "a d", "a n", "n a", "n d", "i n", "a -", "u -", "n -", "にゃ"]

for alias in oto_aliases:
    oto_item = OtoInfo()
    oto_item.alias = alias

    lang_tool = JapaneseLanguageTool()
    phoneme_info = lang_tool.get_oto_entry_phoneme_info(oto_item)

    print("%s: %s" % (alias, phoneme_info.type))