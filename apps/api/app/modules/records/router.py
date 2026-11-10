import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, Customer, Service, User
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.identity.router import get_current_user
from app.modules.records.schemas import (
    CustomerCreate, CustomerResponse, CustomerUpdate,
    ServiceCreate, ServiceResponse, ServiceUpdate,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["Business records"])


def _audit(db: Session, business_id: uuid.UUID, actor_id: uuid.UUID,
           action: str, target_type: str, target_id: uuid.UUID) -> None:
    db.add(AuditEvent(
        business_id=business_id,
        actor_user_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        event_metadata={},
    ))


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(business_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_membership(business_id, user, db)
    set_tenant_context(db, business_id)
    return list(db.scalars(
        select(Customer).where(Customer.business_id == business_id)
        .order_by(Customer.display_name.asc())
    ).all())


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(business_id: uuid.UUID, payload: CustomerCreate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    customer = Customer(business_id=business.id, **payload.model_dump())
    db.add(customer)
    db.flush()
    _audit(db, business.id, user.id, "customer.created", "customer", customer.id)
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(business_id: uuid.UUID, customer_id: uuid.UUID, payload: CustomerUpdate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.business_id == business.id
    ).with_for_update())
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    _audit(db, business.id, user.id, "customer.updated", "customer", customer.id)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/services", response_model=list[ServiceResponse])
def list_services(business_id: uuid.UUID, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    require_membership(business_id, user, db)
    set_tenant_context(db, business_id)
    return list(db.scalars(
        select(Service).where(Service.business_id == business_id)
        .order_by(Service.name.asc())
    ).all())


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(business_id: uuid.UUID, payload: ServiceCreate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    service = Service(business_id=business.id, **payload.model_dump())
    db.add(service)
    db.flush()
    _audit(db, business.id, user.id, "service.created", "service", service.id)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/services/{service_id}", response_model=ServiceResponse)
def update_service(business_id: uuid.UUID, service_id: uuid.UUID, payload: ServiceUpdate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    service = db.scalar(select(Service).where(
        Service.id == service_id, Service.business_id == business.id
    ).with_for_update())
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    _audit(db, business.id, user.id, "service.updated", "service", service.id)
    db.commit()
    db.refresh(service)
    return service
