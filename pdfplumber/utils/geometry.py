import itertools
from operator import itemgetter
from typing import Dict, List, Optional

from .._typing import T_bbox, T_num, T_obj, T_obj_list
from .clustering import cluster_objects
from .generic import to_list


def objects_to_rect(objects: T_obj_list) -> Dict[str, T_num]:
    return {
        "x0": min(map(itemgetter("x0"), objects)),
        "x1": max(map(itemgetter("x1"), objects)),
        "top": min(map(itemgetter("top"), objects)),
        "bottom": max(map(itemgetter("bottom"), objects)),
    }


def objects_to_bbox(objects: T_obj_list) -> T_bbox:
    return (
        min(map(itemgetter("x0"), objects)),
        min(map(itemgetter("top"), objects)),
        max(map(itemgetter("x1"), objects)),
        max(map(itemgetter("bottom"), objects)),
    )


bbox_getter = itemgetter("x0", "top", "x1", "bottom")


def obj_to_bbox(obj: T_obj) -> T_bbox:
    return bbox_getter(obj)


def bbox_to_rect(bbox: T_bbox) -> Dict[str, T_num]:
    return {"x0": bbox[0], "top": bbox[1], "x1": bbox[2], "bottom": bbox[3]}


def merge_bboxes(bboxes: List[T_bbox]) -> T_bbox:
    """
    Given a set of bounding boxes, return the smallest bounding box that
    contains them all.
    """
    return (
        min(map(itemgetter(0), bboxes)),
        min(map(itemgetter(1), bboxes)),
        max(map(itemgetter(2), bboxes)),
        max(map(itemgetter(3), bboxes)),
    )


def get_bbox_overlap(a: T_bbox, b: T_bbox) -> Optional[T_bbox]:
    a_left, a_top, a_right, a_bottom = a
    b_left, b_top, b_right, b_bottom = b
    o_left = max(a_left, b_left)
    o_right = min(a_right, b_right)
    o_bottom = min(a_bottom, b_bottom)
    o_top = max(a_top, b_top)
    o_width = o_right - o_left
    o_height = o_bottom - o_top
    if o_height >= 0 and o_width >= 0 and o_height + o_width > 0:
        return (o_left, o_top, o_right, o_bottom)
    else:
        return None


def calculate_area(bbox: T_bbox) -> T_num:
    left, top, right, bottom = bbox
    if left > right or top > bottom:
        raise ValueError(f"{bbox} has a negative width or height.")
    return (right - left) * (bottom - top)


def clip_obj(obj: T_obj, bbox: T_bbox) -> Optional[T_obj]:

    overlap = get_bbox_overlap(obj_to_bbox(obj), bbox)
    if overlap is None:
        return None

    dims = bbox_to_rect(overlap)
    copy = dict(obj)

    for attr in ["x0", "top", "x1", "bottom"]:
        copy[attr] = dims[attr]

    diff = dims["top"] - obj["top"]
    copy["doctop"] = obj["doctop"] + diff
    copy["width"] = copy["x1"] - copy["x0"]
    copy["height"] = copy["bottom"] - copy["top"]

    return copy


def intersects_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those intersecting the bbox
    """
    initial_type = type(objs)
    objs = to_list(objs)
    matching = [
        obj for obj in objs if get_bbox_overlap(obj_to_bbox(obj), bbox) is not None
    ]
    return initial_type(matching)


def within_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those fully within the bbox
    """
    return [
        obj
        for obj in objs
        if get_bbox_overlap(obj_to_bbox(obj), bbox) == obj_to_bbox(obj)
    ]


def outside_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those fully outside the bbox
    """
    return [obj for obj in objs if get_bbox_overlap(obj_to_bbox(obj), bbox) is None]


def crop_to_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those intersecting the bbox,
    and crops the extent of the objects to the bbox.
    """
    return list(filter(None, (clip_obj(obj, bbox) for obj in objs)))


def move_object(obj: T_obj, axis: str, value: T_num) -> T_obj:
    assert axis in ("h", "v")
    if axis == "h":
        new_items = [
            ("x0", obj["x0"] + value),
            ("x1", obj["x1"] + value),
        ]
    if axis == "v":
        new_items = [
            ("top", obj["top"] + value),
            ("bottom", obj["bottom"] + value),
        ]
        if "doctop" in obj:
            new_items += [("doctop", obj["doctop"] + value)]
        if "y0" in obj:
            new_items += [
                ("y0", obj["y0"] - value),
                ("y1", obj["y1"] - value),
            ]
    return obj.__class__(tuple(obj.items()) + tuple(new_items))


def snap_objects(objs: T_obj_list, attr: str, tolerance: T_num) -> T_obj_list:
    axis = {"x0": "h", "x1": "h", "top": "v", "bottom": "v"}[attr]
    clusters = cluster_objects(objs, itemgetter(attr), tolerance)
    avgs = [sum(map(itemgetter(attr), objs)) / len(objs) for objs in clusters]
    snapped_clusters = [
        [move_object(obj, axis, avg - obj[attr]) for obj in cluster]
        for cluster, avg in zip(clusters, avgs)
    ]
    return list(itertools.chain(*snapped_clusters))


def resize_object(obj: T_obj, key: str, value: T_num) -> T_obj:
    assert key in ("x0", "x1", "top", "bottom")
    old_value = obj[key]
    diff = value - old_value
    new_items = [
        (key, value),
    ]
    if key == "x0":
        assert value <= obj["x1"]
        new_items.append(("width", obj["x1"] - value))
    elif key == "x1":
        assert value >= obj["x0"]
        new_items.append(("width", value - obj["x0"]))
    elif key == "top":
        assert value <= obj["bottom"]
        new_items.append(("doctop", obj["doctop"] + diff))
        new_items.append(("height", obj["height"] - diff))
        if "y1" in obj:
            new_items.append(("y1", obj["y1"] - diff))
    elif key == "bottom":
        assert value >= obj["top"]
        new_items.append(("height", obj["height"] + diff))
        if "y0" in obj:
            new_items.append(("y0", obj["y0"] - diff))
    return obj.__class__(tuple(obj.items()) + tuple(new_items))


def curve_to_edges(curve: T_obj) -> T_obj_list:
    point_pairs = zip(curve["pts"], curve["pts"][1:])
    return [
        {
            "x0": min(p0[0], p1[0]),
            "x1": max(p0[0], p1[0]),
            "top": min(p0[1], p1[1]),
            "doctop": min(p0[1], p1[1]) + (curve["doctop"] - curve["top"]),
            "bottom": max(p0[1], p1[1]),
            "width": abs(p0[0] - p1[0]),
            "height": abs(p0[1] - p1[1]),
            "orientation": "v" if p0[0] == p1[0] else ("h" if p0[1] == p1[1] else None),
        }
        for p0, p1 in point_pairs
    ]


def rect_to_edges(rect: T_obj) -> T_obj_list:
    top, bottom, left, right = [dict(rect) for x in range(4)]
    top.update(
        {
            "object_type": "rect_edge",
            "height": 0,
            "y0": rect["y1"],
            "bottom": rect["top"],
            "orientation": "h",
        }
    )
    bottom.update(
        {
            "object_type": "rect_edge",
            "height": 0,
            "y1": rect["y0"],
            "top": rect["top"] + rect["height"],
            "doctop": rect["doctop"] + rect["height"],
            "orientation": "h",
        }
    )
    left.update(
        {
            "object_type": "rect_edge",
            "width": 0,
            "x1": rect["x0"],
            "orientation": "v",
        }
    )
    right.update(
        {
            "object_type": "rect_edge",
            "width": 0,
            "x0": rect["x1"],
            "orientation": "v",
        }
    )
    return [top, bottom, left, right]


def line_to_edge(line: T_obj) -> T_obj:
    edge = dict(line)
    edge["orientation"] = "h" if (line["top"] == line["bottom"]) else "v"
    return edge


def obj_to_edges(obj: T_obj) -> T_obj_list:
    return {
        "line": lambda x: [line_to_edge(x)],
        "rect": rect_to_edges,
        "rect_edge": rect_to_edges,
        "curve": curve_to_edges,
    }[obj["object_type"]](obj)


def filter_edges(
    edges: T_obj_list,
    orientation: Optional[str] = None,
    edge_type: Optional[str] = None,
    min_length: T_num = 1,
) -> T_obj_list:

    if orientation not in ("v", "h", None):
        raise ValueError("Orientation must be 'v' or 'h'")

    def test(e: T_obj) -> bool:
        dim = "height" if e["orientation"] == "v" else "width"
        et_correct = e["object_type"] == edge_type if edge_type is not None else True
        orient_correct = orientation is None or e["orientation"] == orientation
        return bool(et_correct and orient_correct and (e[dim] >= min_length))

    return list(filter(test, edges))
