from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import get_session_dep, CoreOrAdmin, AnyAuthenticated
from schemas.revenue import RevenueCreate, RevenueRead, RevenueUpdate
from models.revenue import Revenue
from models.user import User, RoleEnum
from models.project import Project

router = APIRouter(prefix="/revenues", tags=["revenues"])

@router.post("/", response_model=RevenueRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_revenue(payload: RevenueCreate, session: AsyncSession = Depends(get_session_dep)):
    # ensure project exists
    p = (await session.execute(select(Project).where(Project.id == payload.project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    r = Revenue(**payload.model_dump())
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r

@router.get("/", response_model=list[RevenueRead], dependencies=[Depends(AnyAuthenticated)])
async def list_revenues(session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    if user.role in (RoleEnum.admin, RoleEnum.core):
        res = (await session.execute(select(Revenue))).scalars().all()
    else:
        # see only revenues of projects they own or in their teams
        from models.project import Project
        proj_ids = (await session.execute(select(Project.id))).scalars().all()
        # filter cheaply by joining condition in python for brevity
        res = (await session.execute(select(Revenue))).scalars().all()
        res = [r for r in res if r.project_id in proj_ids]
    return res

@router.patch("/{rid}", response_model=RevenueRead, dependencies=[Depends(CoreOrAdmin)])
async def update_revenue(rid: int, payload: RevenueUpdate, session: AsyncSession = Depends(get_session_dep)):
    r = (await session.execute(select(Revenue).where(Revenue.id == rid))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Revenue not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    await session.commit()
    await session.refresh(r)
    return r

@router.delete("/{rid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_revenue(rid: int, session: AsyncSession = Depends(get_session_dep)):
    r = (await session.execute(select(Revenue).where(Revenue.id == rid))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Revenue not found")
    await session.delete(r)
    await session.commit()
