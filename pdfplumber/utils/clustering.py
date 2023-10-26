import itertools
from collections.abc import Hashable
from operator import itemgetter
from typing import Callable, Dict, Iterable, List, TypeVar, Union

from .._typing import T_num


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


R = TypeVar("R")


def cluster_objects(
    xs: List[R],
    key_fn: Union[Hashable, Callable[[R], T_num]],
    tolerance: T_num,
    preserve_order: bool = False,
) -> List[List[R]]:

    if not callable(key_fn):
        key_fn = itemgetter(key_fn)

    values = map(key_fn, xs)
    cluster_dict = make_cluster_dict(values, tolerance)

    get_0, get_1 = itemgetter(0), itemgetter(1)

    if preserve_order:
        cluster_tuples = [(x, cluster_dict.get(key_fn(x))) for x in xs]
    else:
        cluster_tuples = sorted(
            ((x, cluster_dict.get(key_fn(x))) for x in xs), key=get_1
        )

    grouped = itertools.groupby(cluster_tuples, key=get_1)

    return [list(map(get_0, v)) for k, v in grouped]
