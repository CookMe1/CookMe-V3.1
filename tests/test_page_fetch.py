from page_fetch import looks_usable


def test_rejects_blocks_and_empty():
    assert not looks_usable("")
    assert not looks_usable("<html>tiny</html>")
    assert not looks_usable("<html><title>Just a moment...</title>" + "x" * 4000)
    assert looks_usable("<html>" + "recipe " * 800 + "</html>")
