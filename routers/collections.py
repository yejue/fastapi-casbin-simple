from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from auth import get_current_user
from schemas import CollectionCreate, CollectionResponse, CollectionItemCreate, CollectionItemResponse
from permissions import require_permission, Action, ResourceType

import models
from database import get_db

router = APIRouter(tags=["collections"])


# 创建集合
@router.post("/api/workspaces/{workspace_id}/collections", response_model=CollectionResponse)
async def create_collection(
        workspace_id: int,
        collection: CollectionCreate,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
        _perm=Depends(require_permission(
            ResourceType.API,
            "collections",
            Action.WRITE
        ))
):
    # 创建集合
    db_collection = models.Collection(
        name=collection.name,
        description=collection.description,
        workspace_id=workspace_id
    )
    db.add(db_collection)
    await db.commit()
    await db.refresh(db_collection)

    return db_collection


# 获取工作区下的所有集合
@router.get("/api/workspaces/{workspace_id}/collections", response_model=List[CollectionResponse])
async def get_collections(
        workspace_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
        _=Depends(require_permission(
            ResourceType.API,
            "collections",
            Action.READ
        ))
):
    # 获取集合列表
    result = await db.execute(
        select(models.Collection)
        .where(models.Collection.workspace_id == workspace_id)
    )
    collections = result.scalars().all()

    return collections


# 获取集合详情
@router.get("/api/workspaces/{workspace_id}/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
        workspace_id: int,
        collection_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
        _=Depends(require_permission(
            ResourceType.API,
            "collections/{collection_id}",
            Action.READ
        ))
):
    # 获取集合详情
    result = await db.execute(
        select(models.Collection)
        .where(models.Collection.workspace_id == workspace_id)
        .where(models.Collection.id == collection_id)
    )
    collection = result.scalars().first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    return collection


# 创建集合项
@router.post("/api/workspaces/{workspace_id}/collections/{collection_id}/items", response_model=CollectionItemResponse)
async def create_collection_item(
        workspace_id: int,
        collection_id: int,
        item: CollectionItemCreate,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
        _=Depends(require_permission(
            ResourceType.API,
            "collections/{collection_id}/items",
            Action.WRITE
        ))
):
    # 验证集合是否存在
    result = await db.execute(
        select(models.Collection)
        .where(models.Collection.id == collection_id)
        .where(models.Collection.workspace_id == workspace_id)
    )
    collection = result.scalars().first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # 创建集合项
    db_item = models.CollectionItem(
        name=item.name,
        image_path=item.image_path,
        collection_id=collection_id
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    return db_item


# 获取集合中所有项目
@router.get("/api/workspaces/{workspace_id}/collections/{collection_id}/items",
            response_model=List[CollectionItemResponse])
async def get_collection_items(
        workspace_id: int,
        collection_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
        _=Depends(require_permission(
            ResourceType.API,
            "collections/{collection_id}/items",
            Action.READ
        ))
):
    # 验证集合是否存在
    result = await db.execute(
        select(models.Collection)
        .where(models.Collection.id == collection_id)
        .where(models.Collection.workspace_id == workspace_id)
    )
    collection = result.scalars().first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # 获取集合项目列表
    result = await db.execute(
        select(models.CollectionItem)
        .where(models.CollectionItem.collection_id == collection_id)
    )
    items = result.scalars().all()

    return items
