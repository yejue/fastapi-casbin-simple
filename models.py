from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from database import Base
import uuid
from datetime import datetime


def generate_uuid():
    return str(uuid.uuid4())


# 数据集与集合项关系表
dataset_items = Table(
    "dataset_items",
    Base.metadata,
    Column("dataset_id", String, ForeignKey("datasets.id")),
    Column("item_id", String, ForeignKey("collection_items.id"))
)


# 用户表
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # 关系
    workspace_users = relationship("WorkspaceUser", back_populates="user")


# 菜单表
class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    path = Column(String)
    parent_id = Column(Integer, ForeignKey('menus.id'), nullable=True)

    # 修改自引用关系定义
    children = relationship(
        "Menu",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )


# 工作区表
class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # 关系
    workspace_users = relationship("WorkspaceUser", back_populates="workspace")
    collections = relationship("Collection", back_populates="workspace")
    datasets = relationship("Dataset", back_populates="workspace")


# 角色表
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))

    # 关系
    workspace_users = relationship("WorkspaceUser", back_populates="role")


# 工作区用户表
class WorkspaceUser(Base):
    __tablename__ = "workspace_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))

    # 关系
    user = relationship("User", back_populates="workspace_users")
    workspace = relationship("Workspace", back_populates="workspace_users")
    role = relationship("Role", back_populates="workspace_users")


# 集合表 (Collection)
class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    created_at = Column(DateTime, default=func.now())

    # 关系
    workspace = relationship("Workspace", back_populates="collections")
    items = relationship("CollectionItem", back_populates="collection")


# 集合项表 (Collection Item)
class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    image_path = Column(String)
    collection_id = Column(Integer, ForeignKey("collections.id"))
    created_at = Column(DateTime, default=func.now())

    # 关系
    collection = relationship("Collection", back_populates="items")
    datasets = relationship("Dataset", secondary=dataset_items, back_populates="items")


# 数据集表 (Dataset)
class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    workspace = relationship("Workspace", back_populates="datasets")
    items = relationship("CollectionItem", secondary=dataset_items, back_populates="datasets") 