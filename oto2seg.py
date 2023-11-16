from __future__ import annotations
from argparse import ArgumentParser
import math
import os
import re
from os import path
from typing import TypedDict
from wave import open as open_wave
from pydub import AudioSegment

from functions import *
from phoneme import *

def get_segment_file_name(seg_info: SegmentInfo):
    prefix = seg_info.art_seg["type"] + "_"

    phonemes = [escape_xsampa(item[0]) for item in seg_info.phoneme_list]
    return prefix + "_".join(phonemes)

def quantize_boundary(boundaries: list[float]) -> list[float]:
    sample_rate = 44100
    n_boundary = len(boundaries)
    for i in range(0, n_boundary):
        if i == 0:
            boundaries[i] = math.floor(boundaries[i] / 1000 * sample_rate) * 1000 / sample_rate
        elif i == n_boundary - 1:
            boundaries[i] = math.ceil(boundaries[i] / 1000 * sample_rate) * 1000 / sample_rate
        else:
            boundaries[i] = math.floor(boundaries[i] / 1000 * sample_rate) * 1000 / sample_rate

    min_length = 10
    for i in range(1, n_boundary):
        if boundaries[i] - boundaries[i - 1] < min_length:
            boundaries[i - 1] = boundaries[i] - min_length

    return boundaries

def get_lang_list() -> list[str]:
    lang_list = []
    for file_name in os.listdir(path.join(path.dirname(__file__), "lang")):
        if file_name.endswith(".py"):
            lang_list.append(file_name[:-3])
    return lang_list

def get_lang_tool(language_name: str) -> BaseLanguageTool:
    script_file = path.join(path.dirname(__file__), "lang", language_name + ".py")
    if path.exists(script_file):
        instance = __import__("lang." + language_name, fromlist=["lang"])
        if hasattr(instance, "lang_tool"):
            return instance.lang_tool
    
    script_file = path.join(path.dirname(__file__), "lang", language_name + "_common.py")
    if path.exists(script_file):
        instance = __import__("lang." + language_name + "_common", fromlist=["lang"])
        if hasattr(instance, "lang_tool"):
            return instance.lang_tool
    
    raise WarningException("Language %s not found." % language_name)

def generate_articulation_segment_info(oto_list: list[OtoInfo], lang_tool: BaseLanguageTool, ignore_vcv: bool, wav_length: float) -> list[SegmentInfo]:
    seg_info_list: list[SegmentInfo] = []
    dist_seg_list: list[SegmentInfo] = []
    
    for oto_item in oto_list:
        try:
            entry_phoneme_info = lang_tool.get_oto_entry_phoneme_info(oto_item)
            
            seg_info = SegmentInfo()
            seg_info.wav_offset = oto_item.offset
            seg_info.wav_cutoff = oto_item.cutoff
            seg_info.auto_item = False
            if entry_phoneme_info.type == "rcv":
                consonant_center = oto_item.offset + lang_tool.get_consonant_center_pos(entry_phoneme_info.phoneme_list[0],
                                                                                        oto_item.preutterance - oto_item.offset)
                # Add R-C segment
                seg_info.auto_item = True
                seg_info.wav_offset = oto_item.offset
                seg_info.wav_cutoff = oto_item.preutterance

                seg_info.phoneme_list = [
                    ["Sil", oto_item.offset - 20, oto_item.offset],
                    [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.preutterance],
                ]
                seg_info.art_seg = {
                    "type": "rc",
                    "phonemes": ["Sil", entry_phoneme_info.phoneme_list[0]],
                    "boundaries": quantize_boundary([oto_item.offset - 20, oto_item.offset, consonant_center]),
                }
                seg_info_list.append(seg_info)

                # Add R-C-V segment
                if not ignore_vcv:
                    seg_info = seg_info.copy()
                    seg_info.auto_item = False
                    seg_info.wav_cutoff = oto_item.preutterance

                    if oto_item.offset > oto_item.overlap:
                        oto_item.offset = oto_item.overlap - 20

                    seg_info.phoneme_list = [
                        ["Sil", oto_item.offset - 20, oto_item.offset],
                        [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.preutterance],
                        [entry_phoneme_info.phoneme_list[1], oto_item.preutterance, oto_item.cutoff],
                    ]
                    seg_info.art_seg = {
                        "type": "rcv",
                        "phonemes": ["Sil", entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                        "boundaries": quantize_boundary([oto_item.offset - 20, oto_item.offset, consonant_center, oto_item.preutterance, oto_item.consonant]),
                    }
                    seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "vcv":
                consonant_center = oto_item.overlap + lang_tool.get_consonant_center_pos(entry_phoneme_info.phoneme_list[1],
                                                                                        oto_item.preutterance - oto_item.overlap)
                # Add V-C segment
                seg_info.auto_item = True
                seg_info.wav_offset = oto_item.offset
                seg_info.wav_cutoff = oto_item.preutterance

                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.overlap],
                    [entry_phoneme_info.phoneme_list[1], oto_item.overlap, oto_item.preutterance],
                ]
                seg_info.art_seg = {
                    "type": "vc",
                    "phonemes": [entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                    "boundaries": quantize_boundary([oto_item.offset, oto_item.overlap, consonant_center]),
                }
                seg_info_list.append(seg_info)

                # Add C-V segment
                # For most languages, get C-V from V-C-V sounds more natural
                seg_info = seg_info.copy()
                seg_info.auto_item = True
                seg_info.wav_offset = oto_item.offset
                seg_info.wav_cutoff = oto_item.cutoff

                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[1], oto_item.overlap, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[2], oto_item.preutterance, oto_item.cutoff],
                ]
                seg_info.art_seg = {
                    "type": "cv",
                    "phonemes": [entry_phoneme_info.phoneme_list[1], entry_phoneme_info.phoneme_list[2]],
                    "boundaries": quantize_boundary([consonant_center, oto_item.preutterance, oto_item.consonant]),
                }
                seg_info_list.append(seg_info)

                # Add V-C-V segment
                if not ignore_vcv:
                    seg_info = seg_info.copy()
                    seg_info.auto_item = False
                    seg_info.wav_offset = oto_item.offset
                    seg_info.wav_cutoff = oto_item.consonant
                    seg_info.phoneme_list = [
                        [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.overlap], # Vowel
                        [entry_phoneme_info.phoneme_list[1], oto_item.overlap, oto_item.preutterance], # Consonant
                        [entry_phoneme_info.phoneme_list[2], oto_item.preutterance, oto_item.consonant], # Vowel
                    ]

                    seg_info.art_seg = {
                        "type": "vcv",
                        "phonemes": entry_phoneme_info.phoneme_list,
                        "boundaries": quantize_boundary([oto_item.offset, oto_item.overlap, consonant_center, oto_item.preutterance, oto_item.consonant]),
                    }
                    seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "rv":
                seg_info.wav_cutoff = oto_item.consonant
                seg_info.phoneme_list = [
                    ["Sil", oto_item.preutterance - 20, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[0], oto_item.preutterance, oto_item.consonant],
                ]
                seg_info.art_seg ={
                    "type": "rv",
                    "phonemes": ["Sil", entry_phoneme_info.phoneme_list[0]],
                    "boundaries": quantize_boundary([oto_item.preutterance - 20, oto_item.preutterance, oto_item.consonant]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "rc":
                if entry_phoneme_info.phoneme_list[0] in plosive_consonant_list:
                    consonant_start = oto_item.consonant
                else:
                    consonant_start = oto_item.offset

                seg_info.phoneme_list = [
                    ["Sil", consonant_start - 20, consonant_start],
                    [entry_phoneme_info.phoneme_list[0], consonant_start, oto_item.cutoff],
                ]
                seg_info.art_seg = {
                    "type": "rc",
                    "phonemes": ["Sil", entry_phoneme_info.phoneme_list[0]],
                    "boundaries": quantize_boundary([consonant_start - 20, consonant_start, oto_item.cutoff]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "vv":
                seg_info.wav_cutoff = oto_item.consonant
                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[1], oto_item.preutterance, oto_item.consonant],
                ]

                seg_info.art_seg = {
                    "type": "vv",
                    "phonemes": [entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                    "boundaries": quantize_boundary([oto_item.offset, oto_item.preutterance, oto_item.consonant]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "cc":
                consonant1 = entry_phoneme_info.phoneme_list[0]
                if consonant1 in plosive_consonant_list:
                    consonant1_start = oto_item.overlap
                elif oto_item.overlap > oto_item.offset:
                    consonant1_start = oto_item.offset + ((oto_item.overlap - oto_item.offset) / 2)
                else:
                    consonant1_start = oto_item.offset

                consonant2_end = oto_item.consonant + ((oto_item.cutoff - oto_item.consonant) / 2)

                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], consonant1_start, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[1], oto_item.preutterance, consonant2_end],
                ]

                seg_info.art_seg = {
                    "type": "cc",
                    "phonemes": [entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                    "boundaries": quantize_boundary([consonant1_start, oto_item.preutterance, consonant2_end]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "cv":
                seg_info.wav_cutoff = oto_item.consonant
                
                consonant = entry_phoneme_info.phoneme_list[0]
                if consonant in plosive_consonant_list:
                    consonant_start = oto_item.overlap
                elif oto_item.overlap > oto_item.offset:
                    consonant_start = oto_item.offset + ((oto_item.overlap - oto_item.offset) / 2)
                else:
                    consonant_start = oto_item.offset

                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], consonant_start, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[1], oto_item.preutterance, oto_item.consonant],
                ]

                seg_info.art_seg = {
                    "type": "cv",
                    "phonemes": [entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                    "boundaries": quantize_boundary([consonant_start, oto_item.preutterance, oto_item.consonant]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "vc":
                consonant = entry_phoneme_info.phoneme_list[1]
                consonant_end = oto_item.consonant + ((oto_item.cutoff - oto_item.consonant) / 2)
                
                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.preutterance],
                    [entry_phoneme_info.phoneme_list[1], oto_item.preutterance, consonant_end],
                ]

                seg_info.art_seg = {
                    "type": "vc",
                    "phonemes": [entry_phoneme_info.phoneme_list[0], entry_phoneme_info.phoneme_list[1]],
                    "boundaries": quantize_boundary([oto_item.offset, oto_item.preutterance, consonant_end]),
                }
                seg_info_list.append(seg_info)
            elif entry_phoneme_info.type == "vr" or entry_phoneme_info.type == "cr":
                seg_info.phoneme_list = [
                    [entry_phoneme_info.phoneme_list[0], oto_item.offset, oto_item.preutterance],
                    ["Sil", oto_item.preutterance, oto_item.preutterance + 20],
                ]

                seg_info.art_seg = {
                    "type":  entry_phoneme_info.type,
                    "phonemes": [entry_phoneme_info.phoneme_list[0], "Sil"],
                    "boundaries": quantize_boundary([oto_item.overlap, oto_item.preutterance, oto_item.preutterance + 20]),
                }
                seg_info_list.append(seg_info)
            else:
                raise WarningException(f"Unknown phoneme type: {entry_phoneme_info.type}")
        except WarningException as e:
            logger.warning(f"Failed to parse {oto_item.alias}: {e}")
        except Exception as e:
            logger.error(f"Failed to parse {oto_item.alias}: {e}")
            traceback.print_exc()

        # Remove duplicate auto items
        seg_info_map: dict[str, list[SegmentInfo]] = {}
        for seg_info in seg_info_list:
            phonemes_str = " ".join(seg_info.art_seg["phonemes"])
            if phonemes_str not in seg_info_map:
                seg_info_map[phonemes_str] = []

            seg_info_map[phonemes_str].append(seg_info)

        for key, seg_list in seg_info_map.items():
            if len(seg_list) > 1:
                dist_seg_info = None
                for seg_info in seg_list:
                    if not seg_info.auto_item:
                        dist_seg_info = seg_info
                        break
                if dist_seg_info is None: # Use the first one
                    dist_seg_info = seg_list[0]

                dist_seg_list.append(dist_seg_info)
            elif len(seg_list) == 1:
                dist_seg_list.append(seg_list[0])
    
    return dist_seg_list


def generate_articulation_files(wav_file: str, seg_info: SegmentInfo, output_dir: str) -> str:
    bleed_time = 100

    file_name = get_segment_file_name(seg_info)
    logger.info(f"Generating {file_name}...")

    append_silent_start = 0
    append_silent_end = 0
    seg_wav_length = seg_info.wav_cutoff - seg_info.wav_offset + bleed_time * 2

    time_delta = 0

    if seg_info.wav_offset < bleed_time:
        append_silent_start = bleed_time - seg_info.wav_offset
        time_delta += append_silent_start
    else:
        time_delta = -1 * (seg_info.wav_offset - bleed_time)


    # Relative data
    relative_wav_offset = seg_info.wav_offset + time_delta
    relative_wav_cutoff = seg_info.wav_cutoff + time_delta

    phoneme_list = []
    for phoneme in seg_info.phoneme_list:
        phoneme_list.append([
            phoneme[0],
            phoneme[1] + time_delta,
            phoneme[2] + time_delta,
        ])
    
    art_seg_list = [
        {
            "type": seg_info.art_seg["type"],
            "phonemes": seg_info.art_seg["phonemes"],
            "boundaries": [boundary + time_delta for boundary in seg_info.art_seg["boundaries"]],
        }
    ]

    with open_wave(wav_file, 'rb') as wav:
        wav_length = wav.getnframes() / wav.getframerate() * 1000

    if seg_info.wav_cutoff + bleed_time > wav_length:
        append_silent_end = seg_info.wav_cutoff + bleed_time - wav_length

    # Generate trans file
    trans_content = generate_articulation_trans_file(phoneme_list)
    output_trans_file = path.join(output_dir, file_name + ".trans")
    with open(output_trans_file, "w", encoding="utf-8") as f:
        f.write(trans_content)
        
    # Generate wav file
    input_sound = AudioSegment.from_wav(wav_file)
    wav_start_time = max(0, seg_info.wav_offset - bleed_time)
    wav_end_time = min(wav_length, seg_info.wav_cutoff + bleed_time)
    output_sound: AudioSegment = input_sound[wav_start_time:wav_end_time]

    if append_silent_start > 0:
        output_sound = AudioSegment.silent(duration=append_silent_start) + output_sound
    if append_silent_end > 0:
        output_sound = output_sound + AudioSegment.silent(duration=append_silent_end)

    output_wav_file = path.join(output_dir, file_name + ".wav")
    output_sound.export(output_wav_file, format="wav")

    output_wav_length = output_sound.duration_seconds * 1000
    output_wav_frames = output_sound.frame_count()

    # Generate seg file
    seg_content = generate_articulation_seg_file(phoneme_list, relative_wav_cutoff, output_wav_length)
    output_seg_file = path.join(output_dir, file_name + ".seg")
    with open(output_seg_file, "w", encoding="utf-8") as f:
        f.write(seg_content)
        
    # Generate as file
    as_content_list = generate_articulation_as_files(art_seg_list, output_wav_frames)
    for i in range(0, len(as_content_list)):
        output_as_file = path.join(output_dir, file_name + ".as%d" % i)
        with open(output_as_file, "w", encoding="utf-8") as f:
            f.write(as_content_list[i])

class ArticulationMapItem(TypedDict):
    seg_info: SegmentInfo
    wav_file: str

def generate_articulation_from_oto(oto_dict: dict[str, list[OtoInfo]], lang_tool: BaseLanguageTool, ignore_vcv: bool, output_dir: str) -> str:
    """Converts an oto.ini dictionary to a .seg file."""
    art_map: dict[str, ArticulationMapItem] = {}
    
    for wav_file, oto_list in oto_dict.items():
        if len(oto_list) == 0:
            continue

        base_name = path.splitext(path.basename(wav_file))[0]
        wav_file_resolved = oto_list[0].wav_file
        with open_wave(wav_file_resolved, 'rb') as wav:
            wav_params = wav.getparams()
            wav_length = wav_params.nframes / wav_params.framerate * 1000

        seg_info_list: list[SegmentInfo] = generate_articulation_segment_info(oto_list, lang_tool, ignore_vcv, wav_length)
        
        for seg_info in seg_info_list:
            generate_articulation_files(wav_file_resolved, seg_info, output_dir)

            art_map[" ".join(seg_info.art_seg["phonemes"])] = {
                "seg_info": seg_info,
                "wav_file": wav_file_resolved
            }

    missing_phoneme_list = lang_tool.get_missing_list(art_map.keys())
    
    logger.info("Missing Articulations: " + ", ".join(missing_phoneme_list))

    # Generate missing phoneme files
    for missing_phoneme in missing_phoneme_list:
        alt_phoneme = lang_tool.get_alternative_phoneme(missing_phoneme, art_map.keys())
        if alt_phoneme:
            logger.info("Alternative Articulations for %s: %s" % (missing_phoneme, alt_phoneme))

            alt_phoneme_list = alt_phoneme.split(" ")
            
            alternative_info = art_map[alt_phoneme]
            new_seg_info: SegmentInfo = alternative_info["seg_info"].set_phonemes(alt_phoneme_list)
            
            generate_articulation_files(alternative_info["wav_file"], new_seg_info, output_dir)
        else:
            logger.info("Warning: Could not find alternative phoneme for %s, skip this line." % missing_phoneme)

if __name__ == "__main__":
    arg_parser = ArgumentParser(formatter_class=SmartFormatter)

    arg_parser.add_argument("oto_file", help="oto.ini file")
    arg_parser.add_argument("output_dir", help="output articulation dir")

    arg_parser.add_argument("--oto-encoding", help="oto.ini encoding. default: shift-jis (also ASCII)", default="shift-jis")
    arg_parser.add_argument("--parser", help="R|oto parser for different languages. default: jpn_common. available parsers:\n"
                            "    " + "\n    ".join(get_lang_list()), default="jpn_common")
    
    arg_parser.add_argument("--ignore-vcv", help="do not generate VCV segments", default=False, action="store_true")

    args = arg_parser.parse_args()

    oto_file: str = args.oto_file
    output_dir: str = args.output_dir

    parser_id = args.parser
    oto_encoding: str = args.oto_encoding

    ignore_vcv: bool = args.ignore_vcv
    
    lang_tool = get_lang_tool(parser_id)
    oto_dict = read_oto(oto_file, encoding=oto_encoding)

    if not path.exists(output_dir):
        os.makedirs(output_dir)

    generate_articulation_from_oto(oto_dict, lang_tool, ignore_vcv, output_dir)