from functions import *
from phoneme import *

oto_aliases = ["- u", "- う", "- da", "- d", "- だ", "a d", "a n", "n a", "n d", "i n", "a -", "u -", "n -", "にゃ"]

for alias in oto_aliases:
    oto_item = OtoInfo()
    oto_item.alias = alias

    phoneme_info = get_oto_entry_phoneme_info(oto_item)

    print("%s: %s" % (alias, phoneme_info.type))