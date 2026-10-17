"""外部ライブラリに依存しないJSON値の型。"""

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
