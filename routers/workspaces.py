from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db

from auth import get_current_user
from schemas import WorkspaceCreate, WorkspaceResponse, WorkspaceInvitation

import models

from permissions import get_enforcer, assign_user_role


router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# 创建工作区
@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    workspace: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 创建工作区
    db_workspace = models.Workspace(
        name=workspace.name,
        description=workspace.description
    )
    db.add(db_workspace)
    await db.commit()
    await db.refresh(db_workspace)
    
    # 创建工作区角色：管理员、数据标注员、工程师
    roles = [
        models.Role(name="管理员", workspace_id=db_workspace.id),
        models.Role(name="数据标注员", workspace_id=db_workspace.id),
        models.Role(name="工程师", workspace_id=db_workspace.id)
    ]
    for role in roles:
        db.add(role)
    
    await db.commit()
    
    # 为当前用户分配管理员角色
    admin_role = await db.execute(
        select(models.Role)
        .where(models.Role.workspace_id == db_workspace.id)
        .where(models.Role.name == "管理员")
    )
    admin_role = admin_role.scalars().first()
    
    # 创建工作区用户关系
    workspace_user = models.WorkspaceUser(
        user_id=current_user.id,
        workspace_id=db_workspace.id,
        role_id=admin_role.id
    )
    db.add(workspace_user)
    await db.commit()
    
    return db_workspace


# 获取工作区列表
@router.get("", response_model=List[WorkspaceResponse])
async def get_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 获取用户所在的所有工作区
    result = await db.execute(
        select(models.Workspace)
        .join(models.WorkspaceUser)
        .where(models.WorkspaceUser.user_id == current_user.id)
    )
    workspaces = result.scalars().all()
    return workspaces


# 获取工作区详情
@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
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
    
    # 获取工作区详情
    result = await db.execute(
        select(models.Workspace)
        .where(models.Workspace.id == workspace_id)
    )
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return workspace


# 邀请用户加入工作区
@router.post("/{workspace_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_user(
        workspace_id: int,
        invitation: WorkspaceInvitation,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 验证当前用户是否是工作区管理员
    result = await db.execute(
        select(models.WorkspaceUser)
        .join(models.Role)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
        .where(models.Role.name == "管理员")
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can invite users"
        )

    # 验证被邀请的用户是否存在
    result = await db.execute(
        select(models.User)
        .where(models.User.id == invitation.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 验证角色是否存在于该工作区
    result = await db.execute(
        select(models.Role)
        .where(models.Role.id == invitation.role_id)
        .where(models.Role.workspace_id == workspace_id)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found in this workspace"
        )

    # 检查用户是否已在工作区
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == invitation.user_id)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already in workspace"
        )

    # 创建工作区用户关系
    workspace_user = models.WorkspaceUser(
        user_id=invitation.user_id,
        workspace_id=workspace_id,
        role_id=invitation.role_id
    )
    db.add(workspace_user)
    await db.commit()

    enforcer = await get_enforcer()
    await assign_user_role(
        invitation.user_id,
        invitation.role_id,
        workspace_id,
        enforcer
    )

    return {"message": "User invited successfully"}
