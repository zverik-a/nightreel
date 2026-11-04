import pytest

from nightreel.models import Sort
from nightreel.providers import NotFoundError
from nightreel.providers.demo import DemoProvider


def test_demo_provider() -> None:
    p = DemoProvider()
    first = p.search()
    assert len(first.items) == 20 and first.has_next
    assert all("sunset" in v.title.lower() or "sunset" in v.tags for v in p.search("sunset").items)
    rated = p.search(sort=Sort.RATED).items
    assert rated == sorted(rated, key=lambda v: v.rating, reverse=True)
    assert {c.id for c in p.categories()} == {"ambient", "city", "nature", "travel"}
    assert all(v.categories == ["city"] for v in p.search(category="city").items)
    v = first.items[0]
    assert p.video(p.parse_ref(p.url_for(v.id))) == v
    with pytest.raises(NotFoundError):
        p.video("nope")
