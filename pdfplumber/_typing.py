from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

T_seq = Sequence
T_num = Union[int, float]
T_point = Tuple[T_num, T_num]
T_bbox = Tuple[T_num, T_num, T_num, T_num]
T_obj = Dict[str, Any]
T_obj_list = List[T_obj]
T_obj_iter = Iterable[T_obj]
