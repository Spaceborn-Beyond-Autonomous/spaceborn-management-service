from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.api.deps import get_session_dep, CoreOrAdmin
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.models.team import Team, team_members
from app.models.user import User

router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_team(payload: TeamCreate, session: AsyncSession = Depends(get_session_dep)):
    team = Team(name=payload.name)
    session.add(team)
    await session.flush()
    if payload.member_ids:
        for mid in set(payload.member_ids):
            await session.execute(team_members.insert().values(team_id=team.id, user_id=mid))
    await session.commit()
    await session.refresh(team)
    team.member_ids = [m.id for m in team.members]
    return team  # from_attributes: member_ids filled below

@router.get("/", response_model=list[TeamRead])
async def list_teams(session: AsyncSession = Depends(get_session_dep)):
    teams = (await session.execute(select(Team))).scalars().unique().all()
    for t in teams:
        t.member_ids = [m.id for m in t.members]
    return teams

@router.patch("/{team_id}", response_model=TeamRead, dependencies=[Depends(CoreOrAdmin)])
async def update_team(team_id: int, payload: TeamUpdate, session: AsyncSession = Depends(get_session_dep)):
    team = (await session.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if payload.name is not None:
        team.name = payload.name
    if payload.member_ids is not None:
        await session.execute(delete(team_members).where(team_members.c.team_id == team.id))
        for mid in set(payload.member_ids):
            await session.execute(team_members.insert().values(team_id=team.id, user_id=mid))
    await session.commit()
    await session.refresh(team)
    team.member_ids = [m.id for m in team.members]
    return team

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_team(team_id: int, session: AsyncSession = Depends(get_session_dep)):
    team = (await session.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await session.delete(team)
    await session.commit()
