import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, Booking, Customer, Employee, Payment, SchedulableResource, Service, User
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.identity.router import get_current_user
from app.modules.records.schemas import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
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
    visit_counts = (
        select(Booking.customer_id.label("customer_id"), func.count(Booking.id).label("visit_count"))
        .where(Booking.business_id == business_id, Booking.status == "completed")
        .group_by(Booking.customer_id)
        .subquery()
    )
    paid_totals = (
        select(Booking.customer_id.label("customer_id"),
               func.coalesce(func.sum(Payment.amount), 0).label("lifetime_value"))
        .join(Payment, (Payment.business_id == Booking.business_id) & (Payment.booking_id == Booking.id))
        .where(Booking.business_id == business_id, Payment.status == "succeeded")
        .group_by(Booking.customer_id)
        .subquery()
    )
    rows = db.execute(
        select(Customer,
               func.coalesce(visit_counts.c.visit_count, 0).label("visits"),
               func.coalesce(paid_totals.c.lifetime_value, 0).label("lifetime_value"))
        .outerjoin(visit_counts, visit_counts.c.customer_id == Customer.id)
        .outerjoin(paid_totals, paid_totals.c.customer_id == Customer.id)
        .where(Customer.business_id == business_id)
        .order_by(Customer.display_name.asc())
    ).all()
    return [
        {"id": c.id, "business_id": c.business_id, "display_name": c.display_name,
         "email": c.email, "phone_e164": c.phone_e164, "notes": c.notes,
         "created_at": c.created_at, "visits": visits, "lifetime_value": value}
        for c, visits, value in rows
    ]


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


@router.get("/scheduling-options")
def list_scheduling_options(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_membership(business_id, user, db)
    set_tenant_context(db, business_id)
    employees = db.scalars(
        select(Employee).where(
            Employee.business_id == business_id,
            Employee.status == "active",
        ).order_by(Employee.display_name.asc())
    ).all()
    resources = db.scalars(
        select(SchedulableResource).where(
            SchedulableResource.business_id == business_id,
            SchedulableResource.status == "active",
        ).order_by(SchedulableResource.name.asc())
    ).all()
    return {
        "employees": [
            {"id": employee.id, "display_name": employee.display_name}
            for employee in employees
        ],
        "resources": [
            {"id": resource.id, "name": resource.name, "resource_type": resource.resource_type,
             "capacity": resource.capacity}
            for resource in resources
        ],
    }
