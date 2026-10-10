"""医薬品情報意思決定支援のドメインモデル。

各 bounded context は ``attachment``、``medicine``、``retrieval`` のように
ドメイン名で分け、その配下を ``primitives.py``、``value_objects.py``、
``entities.py``、``repositories.py``、``services.py``、``exceptions.py`` の
責務別モジュールに整理する。REST/WebSocketの配信やLLMの呼び出しは、
application/presentation/infrastructureで扱う。
"""
