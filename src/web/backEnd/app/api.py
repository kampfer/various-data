from fastapi import APIRouter

from app.sinaFinanceNews.router import router as sinaRouter
from app.nbs.router import router as nbsRouter
from app.akshare.router import router as akshareRouter

apiRouter = APIRouter(prefix="/api")

apiRouter.include_router(sinaRouter)
apiRouter.include_router(nbsRouter)
apiRouter.include_router(akshareRouter)
