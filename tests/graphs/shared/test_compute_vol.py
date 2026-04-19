def test_compute_vol_importable_from_shared():
    from graphs.shared.compute_vol import compute_vol_node

    assert callable(compute_vol_node)


def test_trader_node_still_importable_from_original_location():
    """Regression: anything that imports the node from its old location must still work."""
    from graphs.shared.compute_vol import compute_vol_node as shared_node
    from graphs.trader.nodes.vol_surface import vol_surface_node as original_node

    # After refactor, the original module re-exports the shared implementation.
    # Both names must resolve to the same callable.
    assert shared_node is original_node
