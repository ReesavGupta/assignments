from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=120)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserOut(UserBase):
    id: int

    model_config = {"from_attributes": True}


class ItemBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9 '\-_,\.]+$",
    )
    description: Optional[str] = Field(None, min_length=0, max_length=2000)

    @field_validator("title")
    def no_banned_words(cls, v):
        banned = ["badword"]
        if any(b in v.lower() for b in banned):
            raise ValueError("title contains banned words")
        return v


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=0, max_length=2000)

    @field_validator("title")
    def title_validator(cls, v):
        if v and len(v) < 3:
            raise ValueError("title too short")
        return v


class ItemOut(ItemBase):
    id: int
    owner: UserOut

    model_config = {"from_attributes": True}

class ItemList(BaseModel):
    items: List[ItemOut]
    total: int
    limit: int
    offset: int
