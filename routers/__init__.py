from fastapi import APIRouter
from routers import auth, admin, workspaces, collections, datasets, permissions

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(workspaces.router)
api_router.include_router(collections.router)
api_router.include_router(datasets.router)
api_router.include_router(permissions.router)
