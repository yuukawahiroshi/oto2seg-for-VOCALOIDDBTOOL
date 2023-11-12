# oto to seg for VOCALOID DBTOOL
Generate the files required for the VOCALOID DB Tool from UTAU's oto.ini

This script will generate trans, seg, cropped wav and as0 files. The only thing you need to do is open dbtool, use File -> auto-alignment, select all entries (with the Shift key), and click 'Add Articulations to DB'

It is recommended to quantify before adding to the database. Method: Select the first item in the Auto Alignment window, click "View/Edit Segmentation", re-select the second item in the Auto Alignment window, and then hold down the "Down" key on the keyboard until the highlight moves to the last item.

# Usage
```
usage: oto2seg.py [-h] [--oto-encoding OTO_ENCODING] [--parser PARSER] [--ignore-vcv] oto_file output_dir

positional arguments:
  oto_file              oto.ini file
  output_dir            output articulation dir

options:
  -h, --help            show this help message and exit
  --oto-encoding OTO_ENCODING
                        oto.ini encoding. default: shift-jis (also ASCII)
  --parser PARSER       oto parser for different languages. default: jpn_common. available parsers:
                            jpn_common
  --ignore-vcv          do not generate VCV segments
```

Notice: The oto that needs to be converted can't contain prefixes, suffixes and substitution items. Please clean them before convert.

## Example
```
python oto2seg.py "E:\Projects\Hayato_CVVC\oto.ini" "E:\Projects\Hayato_V3"
```


# About VCV convertor
This script only accept VCV of moresampler-style. You need to alignment each syllable in oto. You can use moresampler to generate base oto (With 'Rename duplicate items: Yes') and review them.

The convertor only generate trans and seg files. You need to generate and modify articulation segments yourself.

Yamaha plz don't kill me