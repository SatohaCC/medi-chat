"""業務語彙に依存しない不変Value Objectの基底。"""

from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, eq=False)
class ImmutableMapping[T](Mapping[str, T]):
    """入力と読取結果を独立させ、未知の項目も保持するMapping。"""

    _data: Mapping[str, T] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_data", deepcopy(dict(self._data)))

    def __getitem__(self, key: str) -> T:
        return deepcopy(self._data[key])

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Mapping) and dict(self) == dict(other)

    def to_dict(self) -> dict[str, T]:
        return deepcopy(dict(self._data))
