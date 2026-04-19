"""Re-exports compute_vol_node from graphs.shared for backward compatibility."""

from graphs.shared.compute_vol import compute_vol_node

# Preserve the original name used by the trader graph and existing tests
vol_surface_node = compute_vol_node
