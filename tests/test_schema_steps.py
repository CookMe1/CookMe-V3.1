from schema_steps import extract_steps


def test_plain_and_list_shapes():
    assert extract_steps("Chop.\nFry.") == ["Chop.", "Fry."]
    assert extract_steps(["Chop.", " Fry. "]) == ["Chop.", "Fry."]
    assert extract_steps([{"@type": "HowToStep", "text": "Chop &amp; mix."}]) == ["Chop & mix."]


def test_nested_section_is_not_read_as_field_names():
    # NYT style: one object holding the steps (the bug that produced "@type", "itemListElement", "name")
    raw = {"@type": "ItemList", "name": "Method", "itemListElement": [
        {"@type": "HowToStep", "text": "Heat the pan."}, {"@type": "HowToStep", "text": "Char the beans."}]}
    assert extract_steps(raw) == ["Heat the pan.", "Char the beans."]


def test_sections_in_a_list_and_html():
    raw = [{"@type": "HowToSection", "name": "Relish", "itemListElement": [{"@type": "HowToStep", "text": "<p>Mix <b>olives</b>.</p>"}]},
           {"@type": "HowToSection", "name": "Beans", "itemListElement": [{"@type": "HowToStep", "name": "Char."}]}]
    assert extract_steps(raw) == ["Mix olives.", "Char."]


def test_empty():
    assert extract_steps(None) == [] and extract_steps([]) == [] and extract_steps({}) == []
