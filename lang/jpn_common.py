from functions import *

global hiragana_map
with open("./data/hiragana.json", "r", encoding="utf-8") as f:
    hiragana_map = json.load(f)

    for item in hiragana_map:
        item["phoneme"] = item["phoneme"].split(" ")


def get_hiragana_info(hiragana: str) -> Optional[JPhonemeMapItem]:
    global hiragana_map

    for item in hiragana_map:
        if item["kana"] == hiragana:
            return item

    return None


def get_romaji_info(romaji: str) -> Optional[JPhonemeMapItem]:
    global hiragana_map

    for item in hiragana_map:
        if item["romaji"] == romaji:
            return item

    return None


class JapaneseLanguageTool(BaseLanguageTool):
    def __init__(self) -> None:
        self.vowel_list = ["a", "i", "M", "e", "o"]
        self.syllabic_consonant_list = ["n", "N\\", "N", "N'", "J", "m", "m'"]
        self.consonant_list = [
            "n",
            "N",
            "N'",
            "J",
            "m",
            "m'",
            "p\\",
            "p\\'",
            "s",
            "S",
            "h",
            "C",
            "dZ",
            "dz",
            "ts",
            "tS",
            "4",
            "4'",
            "p",
            "p'",
            "t",
            "t'",
            "k",
            "k'",
            "b",
            "b'",
            "d",
            "d'",
            "g",
            "g'",
        ]

        self.alias_vowel_list = ["a", "i", "u", "e", "o"]
        self.alias_syllabic_consonant_list = ["n", "N"]
        self.alias_consonant_list = [
            "n",
            "ny",
            "m",
            "my",
            "f",
            "s",
            "sh",
            "h",
            "hy",
            "j",
            "z",
            "ts",
            "ch",
            "r",
            "ry",
            "p",
            "py",
            "t",
            "ty",
            "k",
            "ky",
            "b",
            "by",
            "d",
            "dy",
            "g",
            "gy",
        ]

        self.unvoiced_consonant_list = [
            "p\\",
            "p\\'",
            "s",
            "S",
            "h",
            "C",
            "tS",
            "p",
            "p'",
            "t",
            "t'",
            "k",
            "k'",
        ]
        self.plosive_consonant_list = [
            "p",
            "p'",
            "t",
            "t'",
            "k",
            "k'",
            "b",
            "b'",
            "d",
            "d'",
            "g",
            "g'",
        ]

        self.vowel_variant_list = [
            ["n", "N", "N\\", "N'", "J"],
            ["m", "m'", "n", "N", "N\\", "N'", "J"],
        ]

        self.consonant_variant_list = [
            ["k", "k'"],
            ["g", "g'"],
            ["t", "t'"],
            ["d", "d'"],
            ["n", "N", "N\\", "N'", "J"],
            ["m", "m'", "n"],
            ["h", "C"],
            ["p\\", "p\\'"],
            ["p", "p'"],
            ["b", "b'"],
            ["4", "4'"],
        ]

        self.cvvc_list = []
        for vowel in self.vowel_list + self.syllabic_consonant_list:
            self.cvvc_list.append(f"Sil {vowel}")
            self.cvvc_list.append(f"{vowel} Sil")
        for consonant in self.consonant_list:
            self.cvvc_list.append(f"Sil {consonant}")
        for consonant in self.consonant_list:
            for vowel in self.vowel_list:
                self.cvvc_list.append(f"{vowel} {consonant}")
                self.cvvc_list.append(f"{consonant} {vowel}")
            for vowel in self.syllabic_consonant_list:
                self.cvvc_list.append(f"{vowel} {consonant}")

        # Deduplicate
        self.cvvc_list = list(set(self.cvvc_list))

    def get_alternative_phoneme(
        self, articulation: str, phoneme_list: list[str]
    ) -> Optional[str]:
        phonemes = articulation.split(" ")
        if (
            self.is_vowel(phonemes[0], True)
            or self.is_syllabic_consonant(phonemes[0], True)
        ) and self.is_consonant(phonemes[1], True):
            vowel = phonemes[0]
            consonant = phonemes[1]
            art_type = "vc"
        elif self.is_consonant(phonemes[0], True) and self.is_vowel(phonemes[1], True):
            vowel = phonemes[1]
            consonant = phonemes[0]
            art_type = "cv"
        elif self.is_consonant(phonemes[0], True):
            vowel = phonemes[1]
            consonant = phonemes[0]
            art_type = "cv"
        elif self.is_consonant(phonemes[1], True):
            vowel = phonemes[0]
            consonant = phonemes[1]
            art_type = "vc"
        else:
            return None

        alt_consonant_list = [consonant]
        alt_vowel_list = [vowel]

        for consonant_list in self.consonant_variant_list:
            if consonant in consonant_list:
                for item in consonant_list:
                    if item not in alt_consonant_list:
                        alt_consonant_list.append(item)

        for vowel_list in self.vowel_variant_list:
            if vowel in vowel_list:
                for item in vowel_list:
                    if item not in alt_vowel_list:
                        alt_vowel_list.append(item)

        for alt_consonant in alt_consonant_list:
            for alt_vowel in alt_vowel_list:
                if art_type == "vc":
                    alt_articulation = f"{alt_vowel} {alt_consonant}"
                else:
                    alt_articulation = f"{alt_consonant} {alt_vowel}"

                if alt_articulation in phoneme_list:
                    return alt_articulation

        return None

    def get_phonemes_types(self, phonemes: list[str]) -> list[str]:
        phoneme_types: list[str] = []
        for i in range(len(phonemes), 0, -1):
            phoneme = phonemes[i]

            if phoneme == "-":
                phoneme_types.append("r")
            elif self.is_vowel(phoneme, True):
                phoneme_types.append("v")
            elif self.is_syllabic_consonant(phoneme, True):
                if (
                    phoneme_types[-1] == "c"
                ):  # If next phoneme is a consonant, this phoneme is same as a vowel
                    phoneme_types.append("v")
                else:
                    phoneme_types.append("c")
            elif self.is_consonant(phoneme, True):
                phoneme_types.append("c")
            else:
                phoneme_types.append("?")

        phoneme_types.reverse()

        return phoneme_types

    def get_oto_entry_phoneme_info(self, oto_entry: OtoInfo) -> OtoEntryPhonemeInfo:
        """Returns phoneme info from an OtoInfo object."""
        item_alias = oto_entry.alias

        ret = OtoEntryPhonemeInfo()

        if re.match(r"[0-9]+$", item_alias):  # Alternate phoneme
            ret.is_alternative = True
            item_alias = re.sub(r"[0-9]+$", "", item_alias)

        if item_alias[0] == "-":  # R-C-V?
            item_alias = item_alias[1:].strip()
            if re.match(r"^([ぁ-んァ-ン]+)$", item_alias):  # Hiragana R-C-V:
                hiragana = item_alias.replace(" ", "")

                phoneme_info = get_hiragana_info(hiragana)

                if phoneme_info is None:
                    raise WarningException(
                        f"[Hiragana R-C-V] Could not find phoneme info for {hiragana}"
                    )

                if len(phoneme_info["phoneme"]) == 1:  # R-C or R-V
                    if self.is_vowel(phoneme_info["phoneme"][0], True):
                        ret.type = "rv"
                    else:
                        ret.type = "rc"
                else:
                    ret.type = "rcv"

                ret.phoneme_group = [phoneme_info["phoneme"]]
                ret.phoneme_list = phoneme_info["phoneme"]
            else:  # Romaji R-C-V
                romaji = item_alias.replace(" ", "")

                phoneme_info = get_romaji_info(romaji)

                if phoneme_info is None:
                    raise WarningException(
                        f"[Romaji R-C-V] Could not find phoneme info for {romaji}"
                    )

                if len(phoneme_info["phoneme"]) == 1:  # R-C or R-V
                    if self.is_vowel(phoneme_info["phoneme"][0], True):
                        ret.type = "rv"
                    else:
                        ret.type = "rc"
                elif len(phoneme_info["phoneme"]) == 2:
                    ret.type = "rcv"
                else:
                    raise WarningException(f"[Romaji R-C] Invalid phoneme info for {romaji}")

                ret.phoneme_group = [phoneme_info["phoneme"]]
                ret.phoneme_list = phoneme_info["phoneme"]
        elif item_alias[-1] == "-":  # V-R
            item_alias = item_alias[:-1].strip()
            if re.match(r"^([aiueonN])$", item_alias):  # Romaji V-R
                romaji = item_alias.replace(" ", "")

                phoneme_info = get_romaji_info(romaji)

                if phoneme_info is None:
                    raise WarningException(
                        f"[Romaji VR] Could not find phoneme info for {romaji}"
                    )

                if len(phoneme_info["phoneme"]) == 1:
                    ret.type = "vr"

                    ret.phoneme_group = [phoneme_info["phoneme"]]
                    ret.phoneme_list = phoneme_info["phoneme"]
                else:
                    raise WarningException(f"[Romaji VR] Invalid phoneme info for {romaji}")
            else:
                raise WarningException(f"[Romaji VR] Invalid phoneme info for {item_alias}")
        elif re.match(r"^([aiueoN]) ([aiueoN]|[あいうえおんアイウエオン])$", item_alias):  # V-V
            matches = re.match(r"^([aiueoN]) ([aiueoN]|[あいうえおんアイウエオン])$", item_alias)
            first_vowel = matches.group(1)
            second_vowel = matches.group(2)

            first_vowel_info = get_romaji_info(first_vowel)

            if re.match(r"[aiueoN]", second_vowel):
                second_vowel_info = get_romaji_info(second_vowel)
            else:
                second_vowel_info = get_hiragana_info(second_vowel)

            if first_vowel_info is None or second_vowel_info is None:
                raise WarningException(
                    f"[Romaji VV] Could not find phoneme info for {item_alias}"
                )

            ret.type = "vv"
            ret.phoneme_group = [
                first_vowel_info["phoneme"],
                second_vowel_info["phoneme"],
            ]
            ret.phoneme_list = (
                first_vowel_info["phoneme"] + second_vowel_info["phoneme"]
            )
        elif re.match(r"^n ([あいうえおんアイウエオン])$", item_alias):  # N-V
            matches = re.match(r"^n ([あいうえおんアイウエオン])$", item_alias)

            vowel = matches.group(1)

            n_info = get_hiragana_info("ん")
            vowel_info = get_hiragana_info(vowel)

            if n_info is None or vowel_info is None:
                raise WarningException(
                    f"[Romaji NV] Could not find phoneme info for {item_alias}"
                )

            ret.type = "vv"  # N-V is the same as V-V
            ret.phoneme_group = [n_info["phoneme"], vowel_info["phoneme"]]
            ret.phoneme_list = n_info["phoneme"] + vowel_info["phoneme"]
        elif re.match(r"^([aiueonN]) ([a-zA-Z]+[aiueo]|[ぁ-んァ-ン]+)$", item_alias):  # V-C-V
            matches = re.match(r"^([aiueonN]) ([a-zA-Z]+[aiueo]|[ぁ-んァ-ン]+)$", item_alias)
            prev_vowel = matches.group(1)
            second_syllable = matches.group(2)

            prev_vowel = get_romaji_info(prev_vowel)
            if re.match(r"[aiueoN]", second_syllable):
                second_syllable_info = get_romaji_info(second_syllable)
            else:
                second_syllable_info = get_hiragana_info(second_syllable)

            if prev_vowel is None or second_syllable_info is None:
                raise WarningException(
                    f"[Romaji VCV] Could not find phoneme info for {item_alias}"
                )

            consonant_phoneme = second_syllable_info["phoneme"][0]
            vowel_phoneme = second_syllable_info["phoneme"][1]

            if prev_vowel == "N\\":
                # N variants
                if consonant_phoneme in [
                    "n",
                    "d",
                    "d'",
                    "t",
                    "t'",
                    "4",
                    "4'",
                    "dz",
                    "dZ",
                    "ts",
                    "tS",
                ]:
                    prev_vowel = "n"
                elif consonant_phoneme in ["m", "m'", "p", "p'", "b", "b'"]:
                    prev_vowel = "m"
                elif consonant_phoneme in ["g", "k"]:
                    prev_vowel = "N"
                elif consonant_phoneme == "J":
                    prev_vowel = "J"
                elif consonant_phoneme in ["g'", "k'"]:
                    prev_vowel = "N'"

            prev_vowel_info = prev_vowel.copy()
            prev_vowel_info["phoneme"] = [prev_vowel_info["phoneme"][0]]

            ret.type = "vcv"
            ret.phoneme_group = [
                prev_vowel_info["phoneme"],
                second_syllable_info["phoneme"],
            ]
            ret.phoneme_list = (
                prev_vowel_info["phoneme"] + second_syllable_info["phoneme"]
            )
        elif re.match(r"^([aiueonN]) ([a-zA-Z]+)$", item_alias) and not re.match(
            r"^n ([aiueo])$", item_alias
        ):  # V-C
            matches = re.match(r"^([aiueonN]) ([a-zA-Z]+)$", item_alias)
            vowel = matches.group(1)
            consonant = matches.group(2)

            vowel_info = get_romaji_info(vowel)
            consonant_info = get_romaji_info(consonant)

            if vowel_info is None or consonant_info is None:
                raise WarningException(
                    f"[Romaji VC] Could not find phoneme info for {item_alias}"
                )

            vowel_phoneme = vowel_info["phoneme"][0]
            consonant_phoneme = consonant_info["phoneme"][0]

            if vowel_phoneme == "N\\":
                # N variants
                if consonant_phoneme in [
                    "n",
                    "d",
                    "d'",
                    "t",
                    "t'",
                    "4",
                    "4'",
                    "dz",
                    "dZ",
                    "ts",
                    "tS",
                ]:
                    vowel_phoneme = "n"
                elif consonant_phoneme in ["m", "m'", "p", "p'", "b", "b'"]:
                    vowel_phoneme = "m"
                elif consonant_phoneme in ["g", "k"]:
                    vowel_phoneme = "N"
                elif consonant_phoneme == "J":
                    vowel_phoneme = "J"
                elif consonant_phoneme in ["g'", "k'"]:
                    vowel_phoneme = "N'"

            vowel_info = vowel_info.copy()
            vowel_info["phoneme"] = [vowel_phoneme]

            ret.type = "vc"
            ret.phoneme_group = [vowel_info["phoneme"], consonant_info["phoneme"]]
            ret.phoneme_list = vowel_info["phoneme"] + consonant_info["phoneme"]
        elif re.match(r"(^[a-zA-Z ]+ ?[aiueonN]|[ぁ-んァ-ン]+)$", item_alias):  # C-V
            if re.match(r"^[a-zA-Z ]+$", item_alias):
                romaji = item_alias.replace(" ", "")
                phoneme_info = get_romaji_info(romaji)
            else:
                hiragana = item_alias.replace(" ", "")
                phoneme_info = get_hiragana_info(hiragana)

            if phoneme_info is None:
                raise WarningException(
                    f"[Romaji CV] Could not find phoneme info for {item_alias}"
                )

            ret.type = "cv"
            ret.phoneme_group = [phoneme_info["phoneme"]]
            ret.phoneme_list = phoneme_info["phoneme"]
        else:
            raise WarningException(f"[Unknown Type] Invalid phoneme info for {item_alias}")

        return ret
    
    def get_consonant_center_pos(self, consonant: str, consonant_length: int):
        if consonant in ["ts", "tS", "dz", "dZ"]:
            return consonant_length / 3 * 2
        if consonant in self.plosive_consonant_list:
            return 20
        else:
            return consonant_length / 2

# Exported instance
lang_tool = JapaneseLanguageTool()