"""Machine-independent numbers for generated pages.

Aggregates summed in a different file order differ in the last float digits (0.1 + 0.2 + 0.3 is not 0.3 + 0.2 + 0.1),
so the same records built on two machines produced different page bytes and the results collector rewrote hundreds of
pages on every push. Generated payloads round floats to 9 decimal places before they are written; displayed values
use far fewer, so nothing a reader sees changes.
"""


def stable(value, places=9):
    if isinstance(value, float):
        out = round(value, places)
        return 0.0 if out == 0 else out
    if isinstance(value, dict):
        return {k: stable(v, places) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stable(v, places) for v in value]
    return value
