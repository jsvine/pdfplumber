from playa.structtree import StructElement
from typing import Dict, Any
from collections import deque
from dataclasses import asdict


def structure_dict(top: StructElement) -> Dict[str, Any]:
    """Return a compacted dict representation of PDF structure."""
    r = asdict(top)
    # Prune empty values (does not matter in which order)
    d = deque([r])
    while d:
        el = d.popleft()
        for k in list(el.keys()):
            if el[k] is None or el[k] == [] or el[k] == {}:
                del el[k]
        if "page_idx" in el:
            el["page_number"] = el["page_idx"] + 1
            del el["page_idx"]
        if "children" in el:
            d.extend(el["children"])
    return r
