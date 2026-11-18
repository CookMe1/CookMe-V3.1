from routes.pantry_routes import _qty_of


def test_qty_parsing():
    assert _qty_of("0") == 0
    assert _qty_of("0 kg") == 0
    assert _qty_of("2 kg") == 2
    assert _qty_of("1.5 cups") == 1.5
    assert _qty_of("a pinch") is None
    assert _qty_of(None) is None
