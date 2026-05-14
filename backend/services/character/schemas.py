from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1024, description="人名/主题/需求描述")
    name: str | None = Field(default=None, max_length=64, description="可选：指定 skill 名称，不指定则自动生成")


class CharacterCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=1024)
    tags: list[str] = Field(default_factory=list)
    is_public: bool = False


class CharacterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1024)
    tags: list[str] | None = None
    is_public: bool | None = None


class CharacterListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None


class GalleryQuery(BaseModel):
    after: str | None = None  # ISO timestamp cursor
    page_size: int = Field(default=20, ge=1, le=50)
    search: str | None = None
    tag: str | None = None


class FileContentRequest(BaseModel):
    path: str = Field(default="SKILL.md")  # relative path within skill dir
    content: str | None = Field(default=None, description="写入时提供内容，读取时不传")


class CharacterResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    tags: list[str]
    is_public: bool
    status: str
    source_count: int | None = None
    model_count: int | None = None
    created_at: str
    updated_at: str


class CharacterListResponse(BaseModel):
    items: list[CharacterResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class FileListResponse(BaseModel):
    files: list[str]
    skill_dir: str


class GenerationStatusResponse(BaseModel):
    skill_id: str
    status: str  # generating | ready | error
    progress: str | None = None  # current phase description
