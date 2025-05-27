"""Shared state for the bot."""

# Dictionary to store active fractal groups
# Key: thread_id, Value: FractalGroup object
active_fractal_groups = {}

# Dictionary to track members in fractal groups
# Key: member_id, Value: thread_id
member_groups = {}
