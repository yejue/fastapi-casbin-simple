from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth import get_current_user
from casbin_config import get_enforcer
from permissions import assign_role_permission, assign_user_permission, ResourceType, Action
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


# 请求模型
class RolePermissionRequest(BaseModel):
    role_name: str
    resource_type: str  # api, menu, data
    resource_path: str  # 资源路径，如 collections, collections/1 等
    action: str


class UserPermissionRequest(BaseModel):
    user_id: int
    resource_type: str  # api, menu, data
    resource_path: str  # 资源路径，如 collections, collections/1 等
    action: str


# 为工作区角色分配权限
@router.post("/workspaces/{workspace_id}/roles/permissions", response_model=Dict[str, Any])
async def set_role_permission(
        workspace_id: int,
        permission: RolePermissionRequest,
        current_user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    # 获取 enforcer
    enforcer = await get_enforcer()

    # 验证用户是否是工作区管理员
    result = await db.execute(
        select(models.WorkspaceUser)
        .join(models.Role)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
        .where(models.Role.name == "管理员")
    )
    if not result.scalars().first() and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有工作区管理员可以设置角色权限"
        )

    # 验证角色是否存在于工作区
    result = await db.execute(
        select(models.Role)
        .where(models.Role.workspace_id == workspace_id)
        .where(models.Role.name == permission.role_name)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"角色 '{permission.role_name}' 在工作区中不存在"
        )

    # 分配权限
    await assign_role_permission(
        role.id,
        workspace_id,
        permission.resource_type,
        permission.resource_path,
        permission.action,
        enforcer
    )

    return {"message": f"已为角色 '{role.name}' 分配权限"}


# 为用户分配特定资源的权限
@router.post("/workspaces/{workspace_id}/users/permissions", response_model=Dict[str, Any])
async def set_user_permission(
        workspace_id: int,
        permission: UserPermissionRequest,
        current_user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    # 获取 enforcer
    enforcer = await get_enforcer()

    # 验证用户是否是工作区管理员
    result = await db.execute(
        select(models.WorkspaceUser)
        .join(models.Role)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
        .where(models.Role.name == "管理员")
    )
    if not result.scalars().first() and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有工作区管理员可以设置用户权限"
        )

    # 验证被分配权限的用户是否存在
    result = await db.execute(
        select(models.User)
        .where(models.User.id == permission.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户ID {permission.user_id} 不存在"
        )

    # 验证用户是否在工作区中
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == permission.user_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user.username} 不在工作区中"
        )

    # 验证资源是否存在（特定场景下）
    if permission.resource_type == ResourceType.DATA and permission.resource_path.startswith("collections/"):
        parts = permission.resource_path.split("/")
        if len(parts) >= 2 and parts[1].isdigit():
            collection_id = int(parts[1])
            result = await db.execute(
                select(models.Collection)
                .where(models.Collection.id == collection_id)
                .where(models.Collection.workspace_id == workspace_id)
            )
            resource = result.scalars().first()
            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"集合ID {collection_id} 不存在或不属于此工作区"
                )

    # 分配权限
    await assign_user_permission(
        permission.user_id,
        workspace_id,
        permission.resource_type,
        permission.resource_path,
        permission.action,
        enforcer
    )

    return {"message": f"已为用户 {user.username} 分配权限"}


# 获取用户可访问的菜单
@router.get("/workspaces/{workspace_id}/menus", response_model=List[Dict[str, Any]])
async def get_user_menus(
        workspace_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 验证用户是否属于该工作区
    result = await db.execute(
        select(models.WorkspaceUser)
        .where(models.WorkspaceUser.workspace_id == workspace_id)
        .where(models.WorkspaceUser.user_id == current_user.id)
    )
    if not result.scalars().first() and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不属于此工作区"
        )

    # 获取可访问的菜单
    from permissions import get_user_menus
    accessible_menus = await get_user_menus(
        current_user.id,
        workspace_id,
        db
    )

    # 构建菜单树
    root_menus = [menu for menu in accessible_menus if menu.parent_id is None]
    menu_tree = await build_menu_tree(db, root_menus, accessible_menus)

    return menu_tree


# 辅助函数：构建菜单树
async def build_menu_tree(db, root_menus, all_menus=None):
    menu_tree = []

    for root in root_menus:
        menu_item = {
            "id": root.id,
            "name": root.name,
            "path": root.path,
            "children": []
        }

        # 过滤或获取子菜单
        if all_menus is not None:
            children = [menu for menu in all_menus if menu.parent_id == root.id]
        else:
            result = await db.execute(
                select(models.Menu).where(models.Menu.parent_id == root.id)
            )
            children = result.scalars().all()

        if children:
            menu_item["children"] = await build_menu_tree(db, children, all_menus)

        menu_tree.append(menu_item)

    return menu_tree