from . import utils
from operator import itemgetter

def words_to_edges_h(words, min_words):
    """
    Find (imaginary) horizontal lines that connect the tops of at least `min_words` words.
    """
    by_top = utils.cluster_objects(words, "top", 1)
    large_clusters = filter(lambda x: len(x) >= min_words, by_top)
    bboxes = list(map(utils.objects_to_bbox, large_clusters))
    if len(bboxes) == 0:
        return []
    min_x0 = min(map(itemgetter(0), bboxes))
    max_x1 = max(map(itemgetter(2), bboxes))
    edges = [ {
        "x0": min_x0,
        "x1": max_x1,
        "top": top,
        "bottom": top,
        "width": max_x1 - min_x0,
        "orientation": "h"
    } for x0, top, x1, bottom in bboxes ] + [ {
        "x0": min_x0,
        "x1": max_x1,
        "top": bottom,
        "bottom": bottom,
        "width": max_x1 - min_x0,
        "orientation": "h"
    } for x0, top, x1, bottom in bboxes ]

    return edges

def words_to_edges_v(words, min_words):
    """
    Find (imaginary) vertical lines that connect the left, right, or center of at least `min_words` words.
    """
    # Find words that share the same left, right, or centerpoints
    by_x0 = utils.cluster_objects(words, "x0", 1)
    by_x1 = utils.cluster_objects(words, "x1", 1)
    by_center = utils.cluster_objects(words, lambda x: (x["x0"] + x["x1"])/2, 1)
    clusters = by_x0 + by_x1 + by_center
    
    # Find the points that align with the most words
    sorted_clusters = sorted(clusters, key=lambda x: -len(x))
    large_clusters = filter(lambda x: len(x) >= min_words, sorted_clusters)
    
    # For each of those points, find the rectangles fitting all matching words
    bboxes = map(utils.objects_to_bbox, large_clusters)
    
    # Iterate through those rectangles, condensing overlapping rectangles
    condensed_bboxes = []
    for bbox in bboxes:
        overlap = False
        for c in condensed_bboxes:
            if utils.bboxes_overlap_score(bbox, c) > 0:
                overlap = True
                break
        if overlap == False:
            condensed_bboxes.append(bbox)
            
    if len(condensed_bboxes) == 0:
        return []

    sorted_bboxes = list(sorted(condensed_bboxes, key=itemgetter(0)))

    # Find the far-right boundary of the rightmost rectangle
    last_bbox = sorted_bboxes[-1]
    while True:
        words_inside = utils.intersects_bbox(
            [ w for w in words if w["x0"] >= last_bbox[0] ],
            last_bbox
        )
        bbox = utils.objects_to_bbox(words_inside)
        if bbox == last_bbox:
            break
        else:
            last_bbox = bbox
    
    # Describe all the left-hand edges of each text cluster
    edges = [ {
        "x0": x0,
        "x1": x0,
        "top": top,
        "bottom": bottom,
        "height": bottom - top,
        "orientation": "v"
    } for x0, top, x1, bottom in sorted_bboxes ] + [ {
        "x0": last_bbox[2],
        "x1": last_bbox[2],
        "top": last_bbox[1],
        "bottom": last_bbox[3],
        "height": last_bbox[3] - last_bbox[1],
        "orientation": "v"
    } ]
    
    return edges

def find_text_edges(
        page,
        orientation,

        # How many words need to align to count as a boundary?
        min_words = 3,

        # Should the edges be extended to the extremity of the page?
        extend = False,

        # settings for utils.extract_words
        word_kwargs = {}
    ):

    words = page.extract_words(**word_kwargs)

    finder = { 
        "v": words_to_edges_v,
        "h": words_to_edges_h,
    }[orientation]

    found = finder(words, min_words=min_words)

    if extend:
        x0, top, x1, bottom = page.bbox
        for f in found:
            if f["orientation"] == "v":
                f["top"] = top
                f["bottom"] = bottom
            else:
                f["x0"] = x0
                f["x1"] = x1
    return found
