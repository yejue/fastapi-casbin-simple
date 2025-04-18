from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from auth import get_current_superuser, get_password_hash
from schemas import MenuCreate, MenuResponse, UserCreate, UserResponse
import models
from typing import List

router = APIRouter(prefix="/api/admin", tags=["admin"])


# 菜单创建
@router.post("/menus", response_model=MenuResponse)
async def create_menu(
        menu: MenuCreate,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_superuser)
):
    # 如果指定了父菜单，先验证父菜单是否存在
    if menu.parent_id:
        result = await db.execute(
            select(models.Menu).where(models.Menu.id == menu.parent_id)
        )
        parent_menu = result.scalars().first()
        if not parent_menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent menu not found"
            )

    # 创建菜单
    db_menu = models.Menu(
        name=menu.name,
        path=menu.path,
        parent_id=menu.parent_id
    )

    try:
        db.add(db_menu)
        await db.commit()
        await db.refresh(db_menu)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Menu already exists"
        )

    return db_menu


# 获取所有菜单
@router.get("/menus", response_model=List[MenuResponse])
async def get_menus(
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_superuser)
):
    # 获取所有菜单
    result = await db.execute(select(models.Menu))
    all_menus = result.scalars().all()

    # 构建菜单树的辅助函数
    def build_menu_tree(menus, parent_id=None):
        tree = []
        for menu in menus:
            if menu.parent_id == parent_id:
                children = build_menu_tree(menus, menu.id)
                menu_dict = {
                    "id": menu.id,
                    "name": menu.name,
                    "path": menu.path,
                    "parent_id": menu.parent_id,
                    "children": children
                }
                tree.append(menu_dict)
        return tree

    # 构建并返回菜单树
    return build_menu_tree(all_menus)


# 创建用户
@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_superuser)
):
    # 检查用户名是否已存在
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_superuser=user.is_superuser
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


# 获取所有用户
@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_superuser)
):
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    return users 