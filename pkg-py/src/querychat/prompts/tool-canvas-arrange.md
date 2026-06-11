Move and resize cards on the user's dashboard canvas.

Pass `placements`: a JSON array of `{"name", "x", "y", "w", "h"}` on a
12-column grid (x: 0-11, w: 1-12). Only the named cards move; others keep
their position (the grid auto-compacts upward). To bring an off-canvas card
back, include it here with a position. Unknown names fail the whole call.
