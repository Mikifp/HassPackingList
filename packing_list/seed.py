"""Initial template, taken from the original OneNote lists.

Quantities were written as "Name (n)" or "Name x2"; parse_item() turns those
into a name and a quantity. Which trip types an item belongs to is decided per
category below and can be changed afterwards in the template editor.
"""
import re
import uuid

PRESETS = ["Sommerhus", "Badeferie", "Sommerlejr"]

_QTY = re.compile(r"^(.*?)\s*(?:\((\d+)\)|[x×](\d+))\s*$", re.IGNORECASE)


def parse_item(text):
    """'Shorts (7)' -> ('Shorts', 7); 'Viskestykker x2' -> ('Viskestykker', 2)."""
    text = text.strip()
    m = _QTY.match(text)
    if m and m.group(1):
        return m.group(1).strip(), int(m.group(2) or m.group(3))
    return text, 1


def uid():
    return uuid.uuid4().hex[:8]


# (category, trip types, items)
_ALL = PRESETS
_RAW = [
    ("Mad og drikke", ["Sommerhus", "Sommerlejr"], """
Popkorn kerner
Flavacol
Kokos olie
Gulerødder
Ost
Olie
Svinekød
Oksekød
Springroll wrapper
Drikkevare
Snacks
Allround krydderier
Æg
Shrimp paste
Tomat pasta
Kartofler
Shots
Vodka
Gin
Rom
Cola
Fanta
Andet sodavand
"""),
    ("Baby", _ALL, """
Bleer
Grød
Badetøj
Håndklæde
Babyalarm
Babyalarm oplader
Vandflaske
Sko
Badekar
Højstol
Rejseseng
Legetøj
Strand ting
Zinksalve
Stofbleer
Hagesmæk
Smoothies
Snacks
Mælkepulver
Sut
Skiftetøj
Klapvogn
"""),
    ("Medicin mm.", _ALL, """
Dermovat
Melatonin
Koncertra
Fugtighedscreme
Panodil
Panodil junior
Lactulose
"""),
    ("Praktiske ting", _ALL, """
Pas
Billetter
Kontanter
Solbriller
Negleklipper
Børste
Solcreme
Pude
Dyne
Lagen
Tandbørste
Tandbørste oplader
Tandpasta
Voks
Håndklæder x2
Dele håndklæder x2
Deo
Toiletpapir
Vådservietter
Viskestykker x2
Karklude x2
Termoflaske
Sæbe til vaskemaskine
Opvaskemiddel
Shampoo
Håndsæbe
Termometer
"""),
    ("Elektronik", _ALL, """
Højtaler
Højtaler ledning
Hovedtelefoner
SoundWear
Micro-USB ledning
Nvidia Shield
Shield remote
HDMI stik
Controller
Nacon controller
Popkorn maskine
Stikdåser
Powerbank
Isterningemaskine
Mobil
Mobil oplader
Smart watch
Smart watch oplader
iPad
iPad oplader
Adapter til stikkontakt
xReal
HDMI adapter
Bærbar skærm
"""),
    ("Dykker udstyr", ["Sommerhus", "Badeferie"], """
Sæbe
Finner
Vest
Sokker
Handsker
Maske
Harpun
Lygte
Lygte batterier
Batteri oplader
Bøje
Badebukser
Svømmebriller
"""),
    ("Tøj", _ALL, """
Langbukser (1)
Shorts (7)
Underbukser (6)
Strømper (5)
T-shirts (10)
Lang ærmet T-shirts
Jakke
Sko
Bælte
Regnjakke
Regnbukser
Trænings bukser
Træning trøje
Trænings sko
Overtrøje
Sandaler
Hat
"""),
    ("Spil", ["Sommerhus", "Sommerlejr"], """
Settlers
Settlers: Søfarere
Partners+
Partners
Partners Duo
Exploding Kittens
UNO
Secret Voltemord
Ego: Rød
HINT: Blå
Blokus
Ticket To Ride
Carcassonne
Fluxx
Ticket To Ride
Ticket To Ride: Northern Lights
The Mind
Betrayal at the house on the hill
Patchworks
"""),
    ("Håndbagage", ["Badeferie"], """
Sodavand
Vand
Madpakke
Slik
Chips
Vådservietter
Mundbind
Hovedtelefoner
iPad
Opladere
Xreal
Xreal adapter
"""),
]


def build_seed():
    template = []
    for cat, presets, text in _RAW:
        items, seen = [], set()
        for line in text.strip().splitlines():
            if not line.strip():
                continue
            name, qty = parse_item(line)
            if name.lower() in seen:  # e.g. "Ticket To Ride" was listed twice
                continue
            seen.add(name.lower())
            items.append({"id": uid(), "name": name, "qty": qty, "presets": list(presets)})
        template.append({"id": uid(), "name": cat, "items": items})
    return {"presets": list(PRESETS), "template": template, "trips": []}
