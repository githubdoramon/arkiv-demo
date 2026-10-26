from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from arkiv.attributes import Value

from arkiv_reviews.service import snapshot_from_client


@dataclass
class Entity:
    key: str
    creator: str
    owner: str
    created_at: int
    expires_at: int
    attributes: dict
    payload_value: dict
    creation_flags: object

    def to_json(self):
        return self.payload_value


class Page:
    def __init__(self, block_number, entities, next_page=None):
        self.block_number = block_number
        self.entities = entities
        self._next_page = next_page

    def has_next_page(self):
        return self._next_page is not None

    def next(self):
        return self._next_page


class Builder:
    def __init__(self, client):
        self.client = client

    def where(self, expression):
        self.client.predicate = str(expression)
        return self

    def limit(self, size):
        self.client.limit_size = size
        return self

    def at_block(self, block_number):
        self.client.query_block = block_number
        return self

    def fetch(self):
        return self.client.first_page


class FakeClient:
    def __init__(self):
        self.eth = SimpleNamespace(
            chain_id=1337,
            block_number=50,
            get_block=lambda number: {
                "timestamp": 1_800_000_000 if number == 50 else 1_700_000_000 + number
            },
        )
        flags = SimpleNamespace(readonly=True, permissionless_extension=True)
        first = Entity(
            key="0x" + "A" * 64,
            creator="0x" + "B" * 40,
            owner="0x" + "C" * 40,
            created_at=4,
            expires_at=9_999,
            attributes={
                "app": Value("str", "arkiv-review-demo"),
                "kind": Value("str", "review-root"),
            },
            payload_value={"schema": "review-root/v1"},
            creation_flags=flags,
        )
        second = Entity(
            key="0x" + "D" * 64,
            creator="0x" + "E" * 40,
            owner="0x" + "F" * 40,
            created_at=5,
            expires_at=8_888,
            attributes={"rating": Value("i32", 9)},
            payload_value={"schema": "review-revision/v1"},
            creation_flags=flags,
        )
        self.first_page = Page(50, [first], Page(50, [second]))
        self.query_block = None
        self.limit_size = None
        self.predicate = None
        self.timestamp_blocks = []

        def get_block(number):
            self.timestamp_blocks.append(number)
            return {"timestamp": 1_700_000_000 + number}

        self.eth.get_block = get_block

    def select(self, **fields):
        self.selected_fields = fields
        return Builder(self)


def test_snapshot_fetches_all_pages_at_one_block_and_normalizes_values() -> None:
    client = FakeClient()
    result = snapshot_from_client(client, rpc_url="http://example.invalid")

    assert result["chain_id"] == 1337
    assert result["block_number"] == client.query_block == 50
    assert result["block_timestamp"] == 1_700_000_050
    assert result["evaluation_day"] == 1_700_000_050 // 86_400
    assert client.limit_size == 200
    assert client.predicate == "app = str('arkiv-review-demo')"
    assert len(result["entities"]) == 2
    assert result["entities"][0]["key"] == "0x" + "a" * 64
    assert result["entities"][0]["creator"] == "0x" + "b" * 40
    assert result["entities"][0]["attributes"] == {
        "app": "arkiv-review-demo",
        "kind": "review-root",
    }
    assert result["entities"][0]["created_at_timestamp"] == 1_700_000_004
    assert result["entities"][0]["flags"] == {"readonly": True, "permissionless_extension": True}
    assert client.timestamp_blocks == [50, 4, 5]
