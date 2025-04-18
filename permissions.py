from fastapi import Depends, HTTPException, status, Request
from casbin_config import get_enforcer
from auth import get_current_user
import models
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from typing import Callable, List, Optional, Dict, Any
from functools import wraps


# 资源类型常量
class ResourceType:
    API = "api"
    MENU = "menu"
    DATA = "data"


# 常用操作类型
class Action:
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ALL = "*"


def require_permission(resource_type: str, resource_path: str, action: str):
    """
    通用权限检查依赖函数

    Args:
        resource_type: 资源类型 (api, menu, data)
        resource_path: 资源路径，如 "collections", "collections/1" 等
        action: 操作类型 (read, write, delete, execute)
    """

    async def check_permission(
            request: Request,
            current_user: models.User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ) -> bool:
        # 获取enforcer实例
        enforcer = await get_enforcer(db)

        # 超级用户拥有所有权限
        if current_user.is_superuser:
            return True

        # 获取当前工作区ID
        workspace_id = None
        for param_name, param_value in request.path_params.items():
            if param_name == "workspace_id":
                workspace_id = param_value
                break

        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少工作区ID参数"
            )

        # 构建用户标识
        user_key = f"user:{current_user.id}"

        # 替换路径参数
        actual_path = resource_path
        for param_name, param_value in request.path_params.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in actual_path:
                actual_path = actual_path.replace(placeholder, str(param_value))

            placeholder = f":{param_name}"
            if placeholder in actual_path:
                actual_path = actual_path.replace(placeholder, str(param_value))

        # 构造资源对象
        resource_obj = f"{resource_type}:{workspace_id}:{actual_path}"

        # 检查权限
        print("Enforce with: ", user_key, resource_obj, action)
        has_permission = enforcer.enforce(user_key, workspace_id, resource_obj, action)

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有足够的权限执行此操作: [{resource_type}] {actual_path} [{action}]"
            )

        return True

    return check_permission


# 为角色分配权限
async def assign_role_permission(
        role_id: int,
        workspace_id: int,
        resource_type: str,
        resource_path: str,
        action: str,
        enforcer=None
):
    """
    为角色分配权限

    Args:
        role_id: 角色ID
        workspace_id: 工作区ID
        resource_type: 资源类型 (api, menu, data)
        resource_path: 资源路径，如 "collections", "collections/1" 等
        action: 操作类型
    """
    if enforcer is None:
        enforcer = await get_enforcer()

    role_key = f"role:{role_id}"
    resource_obj = f"{resource_type}:{workspace_id}:{resource_path}"

    await enforcer.add_policy(role_key, str(workspace_id), resource_obj, action)
    return True


# 为用户分配特定资源权限
async def assign_user_permission(
        user_id: int,
        workspace_id: int,
        resource_type: str,
        resource_path: str,
        action: str,
        enforcer=None
):
    """
    为用户分配权限 (ACL方式)

    Args:
        user_id: 用户ID
        workspace_id: 工作区ID
        resource_type: 资源类型
        resource_path: 资源路径
        action: 操作类型
    """
    if enforcer is None:
        enforcer = await get_enforcer()

    user_key = f"user:{user_id}"
    resource_obj = f"{resource_type}:{workspace_id}:{resource_path}"

    await enforcer.add_policy(user_key, str(workspace_id), resource_obj, action)
    return True


# 为用户分配角色
async def assign_user_role(
        user_id: int,
        role_id: int,
        workspace_id: int,
        enforcer=None
):
    """
    为用户分配角色

    Args:
        user_id: 用户ID
        role_id: 角色ID
        workspace_id: 工作区ID
    """
    if enforcer is None:
        enforcer = await get_enforcer()

    user_key = f"user:{user_id}"
    role_key = f"role:{role_id}"

    await enforcer.add_grouping_policy(user_key, role_key, str(workspace_id))
    return True


# 获取用户可访问的菜单
async def get_user_menus(
        user_id: int,
        workspace_id: int,
        db: AsyncSession = None,
        enforcer=None
):
    """
    获取用户在指定工作区中可访问的菜单
    """
    if db is None:
        async for session in get_db():
            db = session
            break

    if enforcer is None:
        enforcer = await get_enforcer(db)

    # 获取所有菜单
    result = await db.execute(select(models.Menu))
    all_menus = result.scalars().all()

    # 超级用户可以访问所有菜单
    user_result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = user_result.scalars().first()
    if user and user.is_superuser:
        return all_menus

    # 检查每个菜单的权限
    accessible_menus = []
    user_key = f"user:{user_id}"

    for menu in all_menus:
        # 构造菜单资源对象
        resource_obj = f"{ResourceType.MENU}:{workspace_id}:{menu.path}"

        # 检查用户是否有权限访问该菜单
        has_permission = await enforcer.enforce(user_key, str(workspace_id), resource_obj, Action.READ)
        if has_permission:
            accessible_menus.append(menu)

    return accessible_menus
