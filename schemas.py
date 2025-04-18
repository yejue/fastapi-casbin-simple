from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


# 用户相关模型
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    is_superuser: bool = False


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attribute: bool = True


# 登录相关模型
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str
    exp: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


# 菜单相关模型
class MenuBase(BaseModel):
    name: str
    path: str


class MenuCreate(MenuBase):
    parent_id: Optional[int] = None


class MenuResponse(MenuBase):
    id: int
    parent_id: Optional[int] = None
    children: List["MenuResponse"] = []

    class Config:
        from_attributes = True  # 使用新版本的配置


MenuResponse.model_rebuild()  # 更新前向引用


# 工作区相关模型
class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceResponse(WorkspaceBase):
    id: int
    created_at: datetime

    class Config:
        from_attribute: bool = True


# 角色相关模型
class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: int
    workspace_id: int

    class Config:
        from_attribute: bool = True


# 集合相关模型
class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionCreate(CollectionBase):
    pass


class CollectionResponse(CollectionBase):
    id: int
    workspace_id: int
    created_at: datetime

    class Config:
        from_attribute: bool = True


# 集合项目相关模型
class CollectionItemBase(BaseModel):
    name: str
    image_path: str


class CollectionItemCreate(CollectionItemBase):
    pass


class CollectionItemResponse(CollectionItemBase):
    id: int
    collection_id: int
    created_at: datetime

    class Config:
        from_attribute: bool = True


# 数据集相关模型
class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetResponse(DatasetBase):
    id: int
    workspace_id: int
    created_at: datetime

    class Config:
        from_attribute: bool = True


# 添加项目到数据集
class AddItemsToDataset(BaseModel):
    item_ids: List[int]


# 工作区用户邀请
class WorkspaceInvitation(BaseModel):
    user_id: int
    role_id: int
