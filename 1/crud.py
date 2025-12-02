from typing import Any, cast

from sqlalchemy import select, func, desc, asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
import models, schemas


def fake_hash_password(password: str) -> str:
    return "fakehashed" + password


async def get_user_by_username(db: AsyncSession, username: str):
    q = select(models.User).where(models.User.username == username)
    result = await db.execute(q)
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: schemas.UserCreate):
    user = models.User(
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=fake_hash_password(user_in.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_item(db: AsyncSession, item_in: schemas.ItemCreate, owner_username: str):
    owner = await get_user_by_username(db, owner_username)
    if not owner:
        raise ValueError("owner not found")
    item = models.Item(title=item_in.title, description=item_in.description, owner_id=owner.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_item(db: AsyncSession, item_id: int):
    q = select(models.Item).where(models.Item.id == item_id).options()
    result = await db.execute(q)
    return result.scalars().first()


async def get_items(
    db: AsyncSession,
    q: str | None = None,
    limit: int = 10,
    offset: int = 0,
    sort_by: str | None = "id",
    order: str | None = "asc",
):
    query = select(models.Item).join(models.User)
    count_q = select(func.count(models.Item.id))
    if q:
        term = f"%{q}%"
        query = query.where((models.Item.title.ilike(term)) | (models.Item.description.ilike(term)))
        count_q = count_q.where((models.Item.title.ilike(term)) | (models.Item.description.ilike(term)))

    # sorting
    sort_col = models.Item.id
    if sort_by is not None and hasattr(models.Item, sort_by):
        sort_col = getattr(models.Item, sort_by)

    if order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))

    total_res = await db.execute(count_q)
    total = total_res.scalars().first() or 0

    res = await db.execute(query.offset(offset).limit(limit))
    items = res.scalars().unique().all()
    return items, total


async def update_item(db: AsyncSession, item_id: int, item_in: schemas.ItemUpdate, owner_username: str):
    # Ensure owner owns the item
    q = select(models.Item).join(models.User).where(models.Item.id == item_id, models.User.username == owner_username)
    res = await db.execute(q)
    item = res.scalars().first()
    if not item:
        return None

    # For type-checkers: treat ORM instance as dynamic for attribute writes
    item_obj = cast(Any, item)

    if item_in.title is not None:
        item_obj.title = item_in.title
    if item_in.description is not None:
        item_obj.description = item_in.description

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int, owner_username: str):
    q = select(models.Item).join(models.User).where(models.Item.id == item_id, models.User.username == owner_username)
    res = await db.execute(q)
    item = res.scalars().first()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True
