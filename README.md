# FastAPI 项目

该项目是一个基于 FastAPI 框架的简单后端 API，实现了用户认证、工作区管理、集合和数据集管理等功能，并集成了基于 Casbin 的权限控制系统。

## 功能特性

- 超级用户管理（登录、创建菜单、创建用户）
- 用户认证（登录、获取当前用户信息）
- 工作区管理（创建工作区、获取工作区列表、获取工作区详情）
- 集合管理（创建集合、获取集合列表、获取集合详情）
- 集合项目管理（创建集合项目、获取集合项目列表）
- 数据集管理（创建数据集、获取数据集列表、将项目添加到数据集）
- 用户协作管理（邀请用户加入工作区并分配角色）
- 权限控制系统（基于 Casbin，支持 RBAC 和 ACL，多工作区隔离）

## 项目要求

- Python 3.8+
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite
- Casbin

## 安装与运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行应用：

```bash
python main.py
```

应用将在 http://localhost:8000 运行，API 文档位于 http://localhost:8000/docs

## 预设账户

系统启动时会自动创建以下账户，密码与用户名相同：

- 超级用户：admin（密码：admin）
- 普通用户：user1、user2、user3（密码同用户名）

## 数据模型设计

项目主要数据模型包括：

- **User**: 用户信息，包含基本账户信息和超级用户标识
- **Menu**: 系统菜单，支持多级嵌套结构
- **Workspace**: 工作区，作为资源隔离的主要单位
- **Role**: 角色，与工作区关联，定义权限组
- **WorkspaceUser**: 用户与工作区的关联，包含用户的角色信息
- **Collection**: 集合，属于特定工作区
- **CollectionItem**: 集合项，属于特定集合
- **Dataset**: 数据集，属于特定工作区，可包含多个集合项

## 权限系统设计

### 整体设计

权限系统基于 Casbin 实现，采用多域模型（Multi-domain Model），支持：

1. **多域隔离**: 以工作区为边界，不同工作区的权限相互隔离
2. **RBAC 与 ACL 结合**: 支持基于角色的访问控制和基于用户的直接权限分配
3. **资源分类**: 将资源分为 API、菜单、数据三类，实现精细化权限控制
4. **装饰器模式**: 提供简单易用的装饰器接口，方便在 API 接口中实现权限控制

### 权限结构

核心权限结构为：

- **主体 (Subject)**: 
  - 用户 (`user:{user_id}`)
  - 角色 (`role:{role_id}`)

- **域 (Domain)**: 
  - 工作区 ID (`{workspace_id}`)

- **对象 (Object)**: 
  - API资源: `api:{workspace_id}:{resource_path}`
  - 菜单资源: `menu:{workspace_id}:{menu_path}`
  - 数据资源: `data:{workspace_id}:{collection_id|dataset_id}`

- **动作 (Action)**:
  - 读取 (read)
  - 写入 (write)
  - 删除 (delete)
  - 执行 (execute)
  - 所有权限 (*)

### 权限检查流程

1. API 请求进入系统
2. 通过装饰器 `@require_permission` 检查当前用户权限
3. 首先检查用户是否为超级管理员，如是则直接通过
4. 检查用户是否拥有直接权限（ACL）
5. 检查用户在当前工作区的角色是否拥有权限（RBAC）
6. 任一检查通过则允许访问，否则返回 403 错误

## 权限使用示例

### 1. 使用装饰器保护 API 端点

```python
@router.post("/{workspace_id}/collections")
@require_permission(ResourceType.API, "{workspace_id}/collections", Action.WRITE)
async def create_collection(
    workspace_id: int,
    collection: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 创建集合的代码...
```

### 2. 为角色分配权限

```python
# 为 Labeler 角色分配访问集合的读权限
await assign_role_permission(
    role_id=labeler_role.id,
    workspace_id=workspace.id,
    resource_type=ResourceType.DATA,
    resource_path=f"{collection.id}",
    action=Action.READ
)
```

### 3. 为用户分配直接权限

```python
# 为用户分配对特定集合的写权限
await assign_user_permission(
    user_id=user.id,
    workspace_id=workspace.id,
    resource_type=ResourceType.DATA,
    resource_path=f"{collection.id}",
    action=Action.WRITE
)
```

### 4. 获取用户可访问的菜单

```python
# 获取用户在工作区中可访问的菜单
user_menus = await get_user_menus(user_id=user.id, workspace_id=workspace.id)
```

## API 接口列表

### 超级用户相关接口
- POST /api/auth/admin/login - 超级用户登录
- POST /api/admin/menus - 创建菜单
- POST /api/admin/users - 创建用户

### 用户认证接口
- POST /api/auth/login - 普通用户登录
- GET /api/auth/me - 获取当前用户信息

### 工作区相关接口
- POST /api/workspaces - 创建工作区
- GET /api/workspaces - 获取工作区列表
- GET /api/workspaces/{workspace_id} - 获取工作区详情

### 集合相关接口
- POST /api/workspaces/{workspace_id}/collections - 创建集合
- GET /api/workspaces/{workspace_id}/collections - 获取集合列表
- GET /api/workspaces/{workspace_id}/collections/{collection_id} - 获取集合详情

### 集合项目相关接口
- POST /api/workspaces/{workspace_id}/collections/{collection_id}/items - 创建集合项目
- GET /api/workspaces/{workspace_id}/collections/{collection_id}/items - 获取集合项目列表

### 数据集相关接口
- POST /api/workspaces/{workspace_id}/datasets - 创建数据集
- GET /api/workspaces/{workspace_id}/datasets - 获取数据集列表
- POST /api/workspaces/{workspace_id}/datasets/{dataset_id}/items - 将项目加入数据集

### 用户协作相关接口
- POST /api/workspaces/{workspace_id}/invitations - 邀请用户加入工作区并分配角色

### 权限管理接口
- POST /api/workspaces/{workspace_id}/permissions/roles - 为角色分配权限
- POST /api/workspaces/{workspace_id}/permissions/users - 为用户分配权限
- GET /api/workspaces/{workspace_id}/menus - 获取用户在当前工作区可访问的菜单 