"""Pydantic schema validation unit tests — no DB needed."""
import pytest
from pydantic import ValidationError

from backend.services.user.schemas import UserRegisterRequest, UserLoginRequest
from backend.services.character.schemas import (
    GenerateRequest, CharacterCreateRequest, CharacterUpdateRequest,
    GalleryQuery, CharacterListQuery,
)
from backend.services.discussion.schemas import (
    DiscussionCreateRequest, InterveneRequest, DiscussionMessageResponse,
)


class TestUserSchemas:
    def test_register_valid(self):
        r = UserRegisterRequest(username="testuser", password="secret123")
        assert r.username == "testuser"
        assert r.phone is None

    def test_register_with_phone(self):
        r = UserRegisterRequest(username="testuser", password="secret123", phone="13900000001")
        assert r.phone == "13900000001"

    def test_register_username_too_short(self):
        with pytest.raises(ValidationError) as exc:
            UserRegisterRequest(username="a", password="secret123")
        assert "username" in str(exc.value).lower() or "String should have at least" in str(exc.value)

    def test_register_password_too_short(self):
        with pytest.raises(ValidationError) as exc:
            UserRegisterRequest(username="testuser", password="12345")
        assert "password" in str(exc.value).lower()

    def test_register_username_max_64(self):
        r = UserRegisterRequest(username="a" * 64, password="secret123")
        assert len(r.username) == 64

    def test_register_username_too_long(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(username="a" * 65, password="secret123")

    def test_login_valid(self):
        r = UserLoginRequest(username="testuser", password="secret123")
        assert r.username == "testuser"

    def test_login_empty_username(self):
        with pytest.raises(ValidationError):
            UserLoginRequest(username="", password="secret123")


class TestCharacterSchemas:
    def test_generate_request_valid(self):
        r = GenerateRequest(query="Steve Jobs")
        assert r.query == "Steve Jobs"
        assert r.name is None

    def test_generate_request_empty_query(self):
        with pytest.raises(ValidationError):
            GenerateRequest(query="")

    def test_generate_request_query_too_long(self):
        with pytest.raises(ValidationError):
            GenerateRequest(query="x" * 1025)

    def test_character_create_valid(self):
        r = CharacterCreateRequest(name="Test", description="A test char", tags=["a", "b"], is_public=True)
        assert r.tags == ["a", "b"]
        assert r.is_public is True

    def test_character_create_defaults(self):
        r = CharacterCreateRequest(name="Test")
        assert r.description == ""
        assert r.tags == []
        assert r.is_public is False

    def test_character_create_empty_name(self):
        with pytest.raises(ValidationError):
            CharacterCreateRequest(name="")

    def test_character_update_partial(self):
        r = CharacterUpdateRequest(description="new desc")
        assert r.description == "new desc"
        assert r.name is None
        assert r.is_public is None

    def test_gallery_query_defaults(self):
        r = GalleryQuery()
        assert r.page_size == 20

    def test_gallery_page_size_max(self):
        with pytest.raises(ValidationError):
            GalleryQuery(page_size=51)

    def test_character_list_page_invalid(self):
        with pytest.raises(ValidationError):
            CharacterListQuery(page=0)

    def test_character_list_page_size_too_large(self):
        with pytest.raises(ValidationError):
            CharacterListQuery(page_size=101)


class TestDiscussionSchemas:
    def test_create_valid(self):
        r = DiscussionCreateRequest(
            topic="Test discussion",
            character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2,
            duration=600,
        )
        assert r.duration == 600

    def test_duration_minimum_exact(self):
        r = DiscussionCreateRequest(topic="X", character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2, duration=60)
        assert r.duration == 60

    def test_duration_too_low(self):
        with pytest.raises(ValidationError):
            DiscussionCreateRequest(topic="X", character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2, duration=59)

    def test_duration_maximum_exact(self):
        r = DiscussionCreateRequest(topic="X", character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2, duration=3600)
        assert r.duration == 3600

    def test_duration_too_high(self):
        with pytest.raises(ValidationError):
            DiscussionCreateRequest(topic="X", character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2, duration=3601)

    def test_empty_topic(self):
        with pytest.raises(ValidationError):
            DiscussionCreateRequest(topic="", character_ids=["550e8400-e29b-41d4-a716-446655440000"] * 2, duration=60)

    def test_empty_character_ids(self):
        with pytest.raises(ValidationError):
            DiscussionCreateRequest(topic="X", character_ids=[], duration=60)

    def test_too_many_characters(self):
        with pytest.raises(ValidationError):
            DiscussionCreateRequest(topic="X", character_ids=["id"] * 11, duration=60)

    def test_intervene_empty(self):
        with pytest.raises(ValidationError):
            InterveneRequest(content="")

    def test_intervene_too_long(self):
        with pytest.raises(ValidationError):
            InterveneRequest(content="x" * 501)

    def test_message_response_exclude_none_confidence(self):
        m = DiscussionMessageResponse(
            id="a", discussion_id="b", round_number=1,
            message_type="agent_speak", content="hello", created_at="2024-01-01T00:00:00",
        )
        d = m.model_dump(exclude_none=True)
        assert "confidence" not in d

    def test_message_response_include_confidence(self):
        m = DiscussionMessageResponse(
            id="a", discussion_id="b", round_number=1,
            message_type="agent_think", content="thinking...", confidence=0.87,
            created_at="2024-01-01T00:00:00",
        )
        d = m.model_dump(exclude_none=True)
        assert d["confidence"] == 0.87
