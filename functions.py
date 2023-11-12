from __future__ import annotations
from abc import ABC, abstractmethod
import argparse
import json
import re
from os import path
from typing import Optional, TypedDict
from wave import open as open_wave

from phoneme import *


class OtoInfo:
    wav_file: str
    alias: str
    offset: float
    consonant: float
    cutoff: float
    preutterance: float
    overlap: float


class JPhonemeMapItem(TypedDict):
    kana: str
    romaji: str
    phoneme: list[str]
    type: str


class OtoEntryPhonemeInfo:
    type: str
    phoneme_group: list[list[str]]
    phoneme_list: list[str]
    is_alternative: bool


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()  
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def read_oto(oto_file: str, encoding: str = "shift-jis") -> dict[str, list[OtoInfo]]:
    """Reads an oto.ini file and returns a dictionary of lists of OtoInfo objects."""
    oto_dict: dict[str, list[OtoInfo]] = {}
    oto_path = path.dirname(oto_file)
    with open(oto_file, "r", encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#") or line.startswith(";"):
                continue

            wav_file, oto_params = line.split("=")

            if wav_file not in oto_dict:
                oto_dict[wav_file] = []

            wav_file_resolved = path.join(oto_path, wav_file)
            if not path.isfile(wav_file_resolved):
                print(
                    f"Warning: Could not find wav file {wav_file_resolved}, skip this line."
                )
                continue

            with open_wave(wav_file_resolved, "rb") as wav:
                wav_params = wav.getparams()
                wav_length = wav_params.nframes / wav_params.framerate * 1000

            alias, offset, consonant, cutoff, preutterance, overlap = oto_params.split(
                ","
            )

            offset = float(offset)
            consonant = float(consonant)
            cutoff = float(cutoff)
            preutterance = float(preutterance)
            overlap = float(overlap)
            # Make all of the values absolute
            consonant = max(offset + consonant, 0)
            preutterance = max(offset + preutterance, 0)
            overlap = max(offset + overlap, 0)

            if cutoff > 0:
                cutoff = max(consonant + 0.1, wav_length - offset)
            else:
                cutoff = min(wav_length, offset + (-1 * cutoff))

            oto_info = OtoInfo()
            oto_info.wav_file = wav_file_resolved
            oto_info.alias = alias
            oto_info.offset = offset
            oto_info.consonant = consonant
            oto_info.cutoff = cutoff
            oto_info.preutterance = preutterance
            oto_info.overlap = overlap

            oto_dict[wav_file].append(oto_info)

    # Sort the oto list by preutterance
    for oto_list in oto_dict.values():
        oto_list.sort(key=lambda x: x.preutterance)

    return oto_dict


def escape_xsampa(xsampa: str) -> str:
    """Escapes xsampa to file name."""
    xsampa = xsampa.replace("Sil", "sil")  # Sil is a special case
    xsampa = (
        xsampa.replace("\\", "-")
        .replace("/", "~")
        .replace("?", "!")
        .replace(":", ";")
        .replace("<", "(")
        .replace(">", ")")
    )
    xsampa = re.sub(r"([A-Z])", lambda x: x.group(1).lower() + "#", xsampa)
    return xsampa


def unescape_xsampa(xsampa: str) -> str:
    """Unescapes xsampa from file name."""
    xsampa = re.sub(r"([a-z])#", lambda x: x.group(1).upper(), xsampa)
    xsampa = (
        xsampa.replace("-", "\\")
        .replace("~", "/")
        .replace("!", "?")
        .replace(";", ":")
        .replace("(", "<")
        .replace(")", ">")
    )
    return xsampa


class ArticulationSegmentInfo(TypedDict):
    type: str
    phonemes: list[str, str]
    boundaries: list[list[str, float, float]]


class SegmentInfo:
    wav_offset: float
    wav_cutoff: float
    auto_item: bool
    phoneme_list: list[list[str, float]]
    art_seg: ArticulationSegmentInfo

    def copy(self):
        new_seg_info = SegmentInfo()
        new_seg_info.wav_offset = self.wav_offset
        new_seg_info.wav_cutoff = self.wav_cutoff
        new_seg_info.auto_item = self.auto_item
        new_seg_info.phoneme_list = [phoneme.copy() for phoneme in self.phoneme_list]
        new_seg_info.art_seg = {
            "type": self.art_seg["type"],
            "phonemes": self.art_seg["phonemes"].copy(),
            "boundaries": self.art_seg["boundaries"].copy(),
        }

        return new_seg_info

    def set_phonemes(self, new_phonemes: list[str]):
        if len(new_phonemes) != len(self.phoneme_list):
            raise ValueError("Phoneme list length mismatch.")

        new_seg_info = self.copy()

        new_seg_info.art_seg["phonemes"] = new_phonemes.copy()

        for i in range(0, len(new_seg_info.phoneme_list)):
            new_seg_info.phoneme_list[i][0] = new_phonemes[i]

        return new_seg_info


def generate_articulation_seg_file(
    phoneme_list: list[list], cutoff_pos: int, wav_length: int
) -> str:
    content = [
        "nPhonemes %d" % (len(phoneme_list) + 2,),  # Add 2 Sil
        "articulationsAreStationaries = 0",
        "phoneme		BeginTime		EndTime",
        "===================================================",
    ]

    content.append("%s\t\t%.6f\t\t%.6f" % ("Sil", 0, phoneme_list[0][1] / 1000))

    for i in range(0, len(phoneme_list)):
        phoneme_info = phoneme_list[i]
        phoneme_name = phoneme_info[0]
        begin_time = phoneme_info[1] / 1000
        if i == len(phoneme_list) - 1:
            end_time = cutoff_pos / 1000
        else:
            end_time = phoneme_list[i + 1][1] / 1000

        content.append("%s\t\t%.6f\t\t%.6f" % (phoneme_name, begin_time, end_time))

    content.append("%s\t\t%.6f\t\t%.6f" % ("Sil", cutoff_pos / 1000, wav_length / 1000))

    return "\n".join(content) + "\n"


def generate_articulation_trans_file(seg_info: list[list]) -> str:
    content = []

    phoneme_list = []
    for i in range(0, len(seg_info)):
        phoneme_list.append(seg_info[i][0])

    content.append(" ".join(phoneme_list))

    trans_group = [item[0] for item in seg_info]
    content.append("[" + " ".join(trans_group) + "]")

    return "\n".join(content)


def generate_articulation_as_files(
    art_seg_list: list[ArticulationSegmentInfo], wav_samples: int
) -> str:
    as_content_list = []
    for art_seg_info in art_seg_list:
        content = [
            "nphone art segmentation",
            "{",
            '\tphns: ["' + ('", "'.join(art_seg_info["phonemes"])) + '"];',
            "\tcut offset: 0;",
            "\tcut length: %d;" % wav_samples,
        ]

        boundaries_str = [
            ("%.9f" % (item / 1000)) for item in art_seg_info["boundaries"]
        ]
        content.append("\tboundaries: [" + ", ".join(boundaries_str) + "];")

        content.append("\trevised: false;")

        voiced_str = []
        is_triphoneme = len(art_seg_info["phonemes"]) == 3
        for i in range(0, len(art_seg_info["phonemes"])):
            phoneme = art_seg_info["phonemes"][i]
            is_unvoiced = phoneme in unvoiced_consonant_list or phoneme in [
                "Sil",
                "Asp",
                "?",
            ]
            voiced_str.append(str(not is_unvoiced).lower())
            if is_triphoneme and i == 1:  # Triphoneme needs 2 flags for center phoneme
                voiced_str.append(str(not is_unvoiced).lower())

        content.append("\tvoiced: [" + ", ".join(voiced_str) + "];")

        content.append("};")
        content.append("")

        as_content_list.append("\n".join(content))

    return as_content_list


class BaseLanguageTool(ABC):
    def __init__(self) -> None:
        self.vowel_list: list[str] = []
        self.syllabic_consonant_list: list[str] = []
        self.consonant_list: list[str] = []

        self.alias_vowel_list: list[str] = []
        self.alias_syllabic_consonant_list: list[str] = []
        self.alias_consonant_list: list[str] = []

        self.unvoiced_consonant_list: list[str] = []
        self.plosive_consonant_list: list[str] = []

        self.vowel_variant_list: list[list[str]] = []
        self.consonant_variant_list: list[list[str]] = []

        self.cvvc_list: list[str] = []

    def is_vowel(self, phoneme: str, use_xsampa: bool) -> bool:
        if use_xsampa:
            return phoneme in self.vowel_list
        else:
            return phoneme in self.alias_vowel_list

    def is_syllabic_consonant(self, phoneme: str, use_xsampa: bool) -> bool:
        if use_xsampa:
            return phoneme in self.syllabic_consonant_list
        else:
            return phoneme in self.alias_syllabic_consonant_list

    def is_consonant(self, phoneme: str, use_xsampa: bool) -> bool:
        if use_xsampa:
            return phoneme in self.consonant_list
        else:
            return False  # TODO: Implement this

    def is_plosive_consonant(self, phoneme: str) -> bool:
        return phoneme in self.plosive_consonant_list

    def get_missing_list(self, phoneme_list: list[str]) -> list[str]:
        missing_list = []

        for phoneme in self.cvvc_list:
            if phoneme not in phoneme_list:
                missing_list.append(phoneme)

        return missing_list
    
    def get_consonant_center_pos(self, consonant: str, consonant_length: int):
        if consonant in self.plosive_consonant_list:
            return 20
        else:
            return consonant_length / 2

    @abstractmethod
    def get_alternative_phoneme(
        self, articulation: str, phoneme_list: list[str]
    ) -> Optional[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_phonemes_types(self, phonemes: list[str]) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_oto_entry_phoneme_info(self, oto_entry: OtoInfo) -> OtoEntryPhonemeInfo:
        raise NotImplementedError()
    