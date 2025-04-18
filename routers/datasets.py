from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from auth import get_current_user
from schemas import DatasetCreate, DatasetResponse, AddItemsToDataset
import models
from typing import List

router = APIRouter(tags=["datasets"])

# 创建数据集
@router.post("/api/workspaces/{workspace_id}/datasets", response_model=DatasetResponse)
async def create_dataset(
    workspace_id: str,
    dataset: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 验证用户是否属于该工作区
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not in workspace"
        )
    
    # 创建数据集
    db_dataset = models.Dataset(
        name=dataset.name,
        description=dataset.description,
        workspace_id=workspace_id
    )
    db.add(db_dataset)
    await db.commit()
    await db.refresh(db_dataset)
    
    return db_dataset

# 获取工作区下的所有数据集
@router.get("/api/workspaces/{workspace_id}/datasets", response_model=List[DatasetResponse])
async def get_datasets(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 验证用户是否属于该工作区
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not in workspace"
        )
    
    # 获取数据集列表
    result = await db.execute(
        select(models.Dataset)
        .where(models.Dataset.workspace_id == workspace_id)
    )
    datasets = result.scalars().all()
    
    return datasets

# 将项目添加到数据集
@router.post("/api/workspaces/{workspace_id}/datasets/{dataset_id}/items", status_code=status.HTTP_201_CREATED)
async def add_items_to_dataset(
    workspace_id: str,
    dataset_id: str,
    items: AddItemsToDataset,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 验证用户是否属于该工作区
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not in workspace"
        )
    
    # 验证数据集是否存在
    result = await db.execute(
        select(models.Dataset)
        .where(models.Dataset.id == dataset_id)
        .where(models.Dataset.workspace_id == workspace_id)
    )
    dataset = result.scalars().first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # 获取数据集对象
    for item_id in items.item_ids:
        # 验证项目是否存在
        result = await db.execute(
            select(models.CollectionItem)
            .where(models.CollectionItem.id == item_id)
        )
        item = result.scalars().first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        # 验证项目是否已经在数据集中
        result = await db.execute(
            select(models.dataset_items)
            .where(models.dataset_items.c.dataset_id == dataset_id)
            .where(models.dataset_items.c.item_id == item_id)
        )
        if result.first():
            continue  # 跳过已经存在的项目
        
        # 添加项目到数据集
        stmt = models.dataset_items.insert().values(dataset_id=dataset_id, item_id=item_id)
        await db.execute(stmt)
    
    await db.commit()
    
    return {"message": "Items added to dataset successfully"} 