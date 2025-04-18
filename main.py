from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from database import get_db, init_db
from routers import api_router

import models
from auth import get_password_hash


@asynccontextmanager
async def lifespan(app_: FastAPI):
    # 初始化数据库
    await init_db()

    # 初始化 Casbin
    from casbin_config import init_enforcer
    await init_enforcer()

    # 创建超级管理员
    async for db in get_db():
        # 检查是否已存在超级管理员
        result = await db.execute(select(models.User).where(models.User.is_superuser == True))
        if not result.scalars().first():
            # 创建超级管理员
            hashed_password = get_password_hash("admin")
            admin = models.User(
                username="admin",
                email="admin@example.com",
                hashed_password=hashed_password,
                is_superuser=True
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print("超级管理员已创建")

    yield


app = FastAPI(title="FastAPI Project", lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


# 用于测试的根路由
@app.get("/")
async def root():
    return {"message": "API Server is running"}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
