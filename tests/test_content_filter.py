import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import content_filter as c

BAD = ["call 07700 900123", "my number is +34 612 345 678", "612-345-678", "zero seven seven double nine one two three",
       "mail me bob@gmail.com", "bob (at) gmail (dot) com", "bob at gmail dot com", "visit www.x.com", "see foodblog.co.uk",
       "insta @chef_bob", "whatsapp me", "dm me", "this is shit", "what the f.u.c.k", "sh1t", "f*ck", "mierda", "madarchod",
       "ring me on 0 7 7 0 0 9 0 0 1 2 3"]
GOOD = ["Bake at 180 C for 25 minutes", "350g flour, 200ml milk", "A cocktail with class", "Scunthorpe cumin shiitake",
        "Serves 4-6, 12/05/2026", "Great recipe! Loved it :)", "Add 2 tsp salt. 3 cloves garlic. 10 min",
        "Mix well. Then bake at 200 for 30 mins at the end.", "Passata, assam tea, Dr. Oetker", "Used 1.5 kg of lamb & 2.5 litres stock"]

@pytest.mark.parametrize("t", BAD)
def test_blocked(t): assert c.problems(t), t

@pytest.mark.parametrize("t", GOOD)
def test_allowed(t): assert not c.problems(t), (t, c.problems(t))
