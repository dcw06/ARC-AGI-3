"""Review-only revision. A later approval/reservation revision is required."""
def require(root=None):
    raise PermissionError("transient v1 review is GPU-disabled; no source/compute approval or reservation")
