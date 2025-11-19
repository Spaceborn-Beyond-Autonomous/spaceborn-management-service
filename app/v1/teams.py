from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.deps import get_session_dep, CoreOrAdmin
from schemas.team import TeamCreate, TeamRead, TeamUpdate
from models.team import Team, team_members
from models.user import User

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post(
    "/",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Create a new team",
    response_description="The created team with members"
)
async def create_team(payload: TeamCreate, session: AsyncSession = Depends(get_session_dep)):
    """
    Create a new team with an optional set of member IDs.

    - **name**: Team name (unique)
    - **member_ids**: List of user IDs to add as members
    """
    team = Team(name=payload.name, lead_id=payload.lead_id)
    session.add(team)
    await session.flush()

    if payload.member_ids:
        # Validate member IDs exist
        valid_members = (await session.execute(select(User.id).where(User.id.in_(payload.member_ids)))).scalars().all()
        invalid_members = set(payload.member_ids) - set(valid_members)
        if invalid_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member IDs: {invalid_members}"
            )
        for mid in set(valid_members):
            await session.execute(team_members.insert().values(team_id=team.id, user_id=mid))

    await session.commit()
    # Eager load members before returning
    await session.refresh(team, attribute_names=["members"])
    return team


@router.get(
    "/",
    response_model=list[TeamRead],
    summary="List all teams",
    response_description="List of teams with members"
)
async def list_teams(session: AsyncSession = Depends(get_session_dep)):
    """
    Retrieve all teams with their members eagerly loaded to avoid N+1.
    """
    result = await session.execute(
        select(Team).options(selectinload(Team.members))
    )
    teams = result.scalars().unique().all()
    return teams


@router.patch(
    "/{team_id}",
    response_model=TeamRead,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Update an existing team",
    response_description="The updated team details"
)
async def update_team(
    payload: TeamUpdate,
    team_id: int = Path(..., description="ID of the team to update"),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Update team name and/or members list. Provide only fields to update.
    """
    result = await session.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.members))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if payload.name is not None:
        team.name = payload.name

    if payload.lead_id is not None:
        team.lead_id = payload.lead_id

    if payload.member_ids is not None:
        # Validate member IDs
        valid_members = (await session.execute(select(User.id).where(User.id.in_(payload.member_ids)))).scalars().all()
        invalid_members = set(payload.member_ids) - set(valid_members)
        if invalid_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member IDs: {invalid_members}"
            )
        # Delete old members and insert new batch
        await session.execute(delete(team_members).where(team_members.c.team_id == team.id))
        for mid in set(valid_members):
            await session.execute(team_members.insert().values(team_id=team.id, user_id=mid))

    await session.commit()
    await session.refresh(team, attribute_names=["members"])
    return team


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Delete a team"
)
async def delete_team(
    team_id: int = Path(..., description="ID of the team to delete"),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Delete team by ID if it exists.
    """
    result = await session.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    await session.delete(team)
    await session.commit()
