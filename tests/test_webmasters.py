import httpx
import pytest
import respx
from conftest import api_video

from nightreel.models import Period, Sort
from nightreel.providers import NotFoundError, ProviderError
from nightreel.providers.webmasters import BASE_URL, WebmastersProvider

SEARCH = f"{BASE_URL}/webmasters/search"


@pytest.fixture
def provider() -> WebmastersProvider:
    return WebmastersProvider()


@respx.mock
def test_search_parses_videos(provider: WebmastersProvider) -> None:
    route = respx.get(SEARCH).mock(
        return_value=httpx.Response(200, json={"videos": [api_video(i) for i in range(30)]})
    )
    page = provider.search("hello world", page=2, sort=Sort.RATED, period=Period.MONTH)
    assert len(page.items) == 30 and page.has_next and page.number == 2
    v = page.items[1]
    assert (v.id, v.duration, v.views, v.rating) == ("abc001", 754, 1500, 87.5)
    assert v.tags == ["one", "two"] and v.categories == ["cat-a"] and v.performers == ["Someone"]
    params = route.calls[0].request.url.params
    assert params["search"] == "hello world"
    assert params["ordering"] == "rating" and params["period"] == "monthly"
    assert params["page"] == "2"


@respx.mock
def test_period_only_sent_for_views_and_rating(provider: WebmastersProvider) -> None:
    route = respx.get(SEARCH).mock(return_value=httpx.Response(200, json={"videos": []}))
    provider.search(None, sort=Sort.NEWEST, period=Period.WEEK, category="cat-a")
    params = route.calls[0].request.url.params
    assert "period" not in params and "search" not in params
    assert params["category"] == "cat-a"


@respx.mock
def test_no_results_code(provider: WebmastersProvider) -> None:
    respx.get(SEARCH).mock(
        return_value=httpx.Response(200, json={"code": "2001", "message": "No Videos found!"})
    )
    page = provider.search("zzz")
    assert page.items == [] and not page.has_next


@respx.mock
def test_video_not_found(provider: WebmastersProvider) -> None:
    respx.get(f"{BASE_URL}/webmasters/video_by_id").mock(
        return_value=httpx.Response(200, json={"code": "2002", "message": "No video"})
    )
    with pytest.raises(NotFoundError):
        provider.video("missing")


@respx.mock
def test_categories_sorted(provider: WebmastersProvider) -> None:
    respx.get(f"{BASE_URL}/webmasters/categories").mock(
        return_value=httpx.Response(
            200,
            json={"categories": [{"id": 2, "category": "zeta"}, {"id": 1, "category": "big-a"}]},
        )
    )
    cats = provider.categories()
    assert [(c.id, c.name) for c in cats] == [("big-a", "Big A"), ("zeta", "Zeta")]


@respx.mock
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(451), "region"),
        (httpx.Response(500), "HTTP 500"),
        (
            httpx.Response(200, text="<html>gate</html>", headers={"content-type": "text/html"}),
            "non-JSON",
        ),
        (httpx.Response(200, json={"categories": "oops"}), "unexpected"),
    ],
)
def test_errors_are_friendly(
    provider: WebmastersProvider, response: httpx.Response, message: str
) -> None:
    respx.get(f"{BASE_URL}/webmasters/categories").mock(return_value=response)
    with pytest.raises(ProviderError, match=message):
        provider.categories()


def test_parse_ref(provider: WebmastersProvider) -> None:
    assert provider.parse_ref("abc123") == "abc123"
    assert provider.parse_ref(f"{BASE_URL}/view_video.php?viewkey=ph99&x=1") == "ph99"
    with pytest.raises(ValueError):
        provider.parse_ref("not valid!")
    with pytest.raises(ValueError):
        provider.parse_ref("https://example.test/other")
