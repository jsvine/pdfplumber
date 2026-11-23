import itertools
from collections.abc import Hashable
from operator import itemgetter
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from .._typing import T_num, T_obj


def cluster_list(xs: List[T_num], tolerance: T_num = 0) -> List[List[T_num]]:
    if tolerance == 0:
        return [[x] for x in sorted(xs)]
    if len(xs) < 2:
        return [[x] for x in sorted(xs)]
    groups = []
    xs = list(sorted(xs))
    current_group = [xs[0]]
    last = xs[0]
    for x in xs[1:]:
        if x <= (last + tolerance):
            current_group.append(x)
        else:
            groups.append(current_group)
            current_group = [x]
        last = x
    groups.append(current_group)
    return groups


def make_cluster_dict(values: Iterable[T_num], tolerance: T_num) -> Dict[T_num, int]:
    clusters = cluster_list(list(set(values)), tolerance)

    nested_tuples = [
        [(val, i) for val in value_cluster] for i, value_cluster in enumerate(clusters)
    ]

    return dict(itertools.chain(*nested_tuples))


Clusterable = TypeVar("Clusterable", T_obj, Tuple[Any, ...])


def assign_cluster_ids(
    xs: List[Clusterable],
    key_fn: Callable[[Clusterable], T_num],
    tolerance_fn: Callable[[Clusterable], T_num],
) -> List[int]:
    """
    Like `make_cluster_dict`, but with a per-object tolerance. Returns the
    cluster index of each object in `xs`, in the same order as `xs`.
    """
    order = sorted(range(len(xs)), key=lambda i: key_fn(xs[i]))
    ids = [0] * len(xs)
    cluster_id = 0
    last = None
    for i in order:
        x = xs[i]
        if last is not None and key_fn(x) > key_fn(last) + tolerance_fn(last):
            cluster_id += 1
        ids[i] = cluster_id
        last = x
    return ids


def cluster_objects(
    xs: List[Clusterable],
    key_fn: Union[Hashable, Callable[[Clusterable], T_num]],
    tolerance: Union[T_num, Callable[[Clusterable], T_num]],
    preserve_order: bool = False,
) -> List[List[Clusterable]]:
    """
    Group objects whose `key_fn` values lie within `tolerance` of the
    previous value. If `tolerance` is a callable, it is called with the
    previous object to get the tolerance for that step, which lets the
    tolerance vary with, e.g., font size.
    """

    if not callable(key_fn):
        key_fn = itemgetter(key_fn)

    cluster_ids: Sequence[Optional[int]]
    if callable(tolerance):
        cluster_ids = assign_cluster_ids(xs, key_fn, tolerance)
    else:
        cluster_dict = make_cluster_dict(map(key_fn, xs), tolerance)
        cluster_ids = [cluster_dict.get(key_fn(x)) for x in xs]

    get_0, get_1 = itemgetter(0), itemgetter(1)

    if preserve_order:
        cluster_tuples = list(zip(xs, cluster_ids))
    else:
        cluster_tuples = sorted(zip(xs, cluster_ids), key=get_1)

    grouped = itertools.groupby(cluster_tuples, key=get_1)

    return [list(map(get_0, v)) for k, v in grouped]
