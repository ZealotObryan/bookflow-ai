import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, Project, User
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.identity.router import get_current_user
from app.modules.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/businesses/{business_id}/projects", tags=["Projects"])


def _audit(db: Session, business_id: uuid.UUID, actor_id: uuid.UUID, action: str, project: Project) -> None:
    db.add(AuditEvent(
        business_id=business_id,
        actor_user_id=actor_id,
        action=action,
        target_type="project",
        target_id=str(project.id),
        event_metadata={"title": project.title, "status": project.status},
    ))


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Project]:
    require_membership(business_id, user, db)
    set_tenant_context(db, business_id)
    return list(db.scalars(
        select(Project).where(Project.business_id == business_id).order_by(Project.updated_at.desc())
    ).all())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    business_id: uuid.UUID,
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    project = Project(
        business_id=business.id,
        title=payload.title,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        client_email=payload.client_email,
        project_type=payload.project_type,
        status=payload.status,
        description=payload.description,
        due_date=payload.due_date,
        quoted_amount=payload.quoted_amount,
        deposit_amount=payload.deposit_amount,
        amount_paid=payload.amount_paid,
        currency=business.currency,
    )
    db.add(project)
    db.flush()
    _audit(db, business.id, user.id, "project.created", project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    business_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    project = db.scalar(select(Project).where(
        Project.id == project_id, Project.business_id == business.id
    ).with_for_update())
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field in {"title", "client_name", "project_type"} and value is not None:
            value = value.strip()
        setattr(project, field, value)
    if project.deposit_amount > project.quoted_amount or project.amount_paid > project.quoted_amount:
        raise HTTPException(status_code=422, detail="Payments and deposit cannot exceed the quoted amount")
    _audit(db, business.id, user.id, "project.updated", project)
    db.commit()
    db.refresh(project)
    return project
