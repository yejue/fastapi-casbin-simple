from pathlib import Path
from typing import Optional
from casbin import AsyncEnforcer
from casbin_async_sqlalchemy_adapter import Adapter, Base as CasbinBase
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine

# 确保配置目录存在
CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)

# Casbin 模型文件路径
MODEL_PATH = CONFIG_DIR / "rbac_model.conf"

# 如果模型文件不存在，创建它
if not MODEL_PATH.exists():
    MODEL_CONF = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && \
    (r.dom == p.dom || p.dom == '*') && \
    keyMatch2(r.obj, p.obj) && \
    (r.act == p.act || p.act == '*')
"""
    MODEL_PATH.write_text(MODEL_CONF.strip())

# 全局 enforcer 实例
_enforcer: Optional[AsyncEnforcer] = None
_adapter: Optional[Adapter] = None


# 创建 Casbin 表
async def create_casbin_tables():
    """创建 Casbin 规则表"""
    async with engine.begin() as conn:
        await conn.run_sync(CasbinBase.metadata.create_all)


async def init_enforcer():
    """初始化 Casbin Enforcer"""
    global _enforcer, _adapter

    if _enforcer is None:
        # 首先创建表
        await create_casbin_tables()

        # 创建适配器 - 使用 engine 而不是 session
        _adapter = Adapter(engine)

        # 创建enforcer
        _enforcer = AsyncEnforcer(str(MODEL_PATH), _adapter)

        # 加载策略
        await _enforcer.load_policy()

    return _enforcer


async def get_enforcer(db: AsyncSession = None) -> AsyncEnforcer:
    """获取 Casbin Enforcer 实例"""
    global _enforcer, _adapter

    if _enforcer is None:
        await init_enforcer()

    return _enforcer
