vowel_variant_list = [
    ["n", "N", "N\\", "N'", "J"],
    ["m", "m'", "n", "N", "N\\", "N'", "J"],
]
    
consonant_variant_list = [
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

vowel_list = ["a", "i", "M", "e", "o", "N\\"]
consonant_list = ["n", "N", "N'", "J", "m", "m'", "p\\", "p\\'", "s", "S", "h", "C",
                  "dZ", "dz", "ts", "tS", "4", "4'", "p", "p'", "t", "t'", "k", "k'",
                  "b", "b'", "d", "d'", "g", "g'"]

unvoiced_consonant_list = ["p\\", "p\\'", "s", "S", "h", "C", "tS", "p", "p'", "t", "t'", "k", "k'"]
plosive_consonant_list = ["p", "p'", "t", "t'", "k", "k'", "b", "b'", "d", "d'", "g", "g'"]

vc_list = []
for vowel in vowel_list:
    for consonant in consonant_list:
        vc_list.append(vowel + " " + consonant)

vr_list = ["a", "i", "M", "e", "o", "N\\", "n", "N", "N'", "J", "m"]