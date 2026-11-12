import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, delete
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import (
    AuditEvent, Booking, Customer, Employee, Payment, SchedulableResource,
    Service, ServiceEmployeeEligibility, ServiceResourceRequirement, User,
)
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.identity.router import get_current_user
from app.modules.records.schemas import (
    CustomerCreate, CustomerResponse, CustomerUpdate, EmployeeCreate,
    EmployeeResponse, EmployeeUpdate, ResourceCreate, ResourceResponse,
    ResourceUpdate, ServiceCreate, ServiceResponse, ServiceUpdate,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["Business records"])


def _audit(db: Session, business_id: uuid.UUID, actor_id: uuid.UUID,
           action: str, target_type: str, target_id: uuid.UUID) -> None:
    db.add(AuditEvent(
        business_id=business_id, actor_user_id=actor_id, action=action,
        target_type=target_type, target_id=str(target_id), event_metadata={},
    ))


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(business_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_membership(business_id, user, db)
    set_tenant_context(db, business_id)
    visit_counts = (
        select(Booking.customer_id.label("customer_id"), func.count(Booking.id).label("visit_count"))
        .where(Booking.business_id == business_id, Booking.status == "completed")
        .group_by(Booking.customer_id).subquery()
    )
    paid_totals = (
        select(Booking.customer_id.label("customer_id"),
               func.coalesce(func.sum(Payment.amount), 0).label("lifetime_value"))
        .join(Payment, (Payment.business_id == Booking.business_id) & (Payment.booking_id == Booking.id))
        .where(Booking.business_id == business_id, Payment.status == "succeeded")
        .group_by(Booking.customer_id).subquery()
    )
    rows = db.execute(
        select(Customer, func.coalesce(visit_counts.c.visit_count, 0).label("visits"),
               func.coalesce(paid_totals.c.lifetime_value, 0).label("lifetime_value"))
        .outerjoin(visit_counts, visit_counts.c.customer_id == Customer.id)
        .outerjoin(paid_totals, paid_totals.c.customer_id == Customer.id)
        .where(Customer.business_id == business_id).order_by(Customer.display_name.asc())
    ).all()
    return [{"id": c.id, "business_id": c.business_id, "display_name": c.display_name,
             "email": c.email, "phone_e164": c.phone_e164, "notes": c.notes,
             "created_at": c.created_at, "visits": visits, "lifetime_value": value}
            for c, visits, value in rows]


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(business_id: uuid.UUID, payload: CustomerCreate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    customer = Customer(business_id=business.id, **payload.model_dump())
    db.add(customer); db.flush()
    _audit(db, business.id, user.id, "customer.created", "customer", customer.id)
    db.commit(); db.refresh(customer)
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(business_id: uuid.UUID, customer_id: uuid.UUID, payload: CustomerUpdate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    customer = db.scalar(select(Customer).where(Customer.id == customer_id,
        Customer.business_id == business.id).with_for_update())
    if customer is None: raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(customer, key, value)
    _audit(db, business.id, user.id, "customer.updated", "customer", customer.id)
    db.commit(); db.refresh(customer)
    return customer


@router.get("/services", response_model=list[ServiceResponse])
def list_services(business_id: uuid.UUID, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    require_membership(business_id, user, db); set_tenant_context(db, business_id)
    return list(db.scalars(select(Service).where(Service.business_id == business_id)
        .order_by(Service.name.asc())).all())


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(business_id: uuid.UUID, payload: ServiceCreate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    service = Service(business_id=business.id, **payload.model_dump())
    db.add(service); db.flush()
    _audit(db, business.id, user.id, "service.created", "service", service.id)
    db.commit(); db.refresh(service)
    return service


@router.patch("/services/{service_id}", response_model=ServiceResponse)
def update_service(business_id: uuid.UUID, service_id: uuid.UUID, payload: ServiceUpdate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    service = db.scalar(select(Service).where(Service.id == service_id,
        Service.business_id == business.id).with_for_update())
    if service is None: raise HTTPException(status_code=404, detail="Service not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(service, key, value)
    _audit(db, business.id, user.id, "service.updated", "service", service.id)
    db.commit(); db.refresh(service)
    return service


@router.get("/services/{service_id}/scheduling")
def get_service_scheduling(business_id: uuid.UUID, service_id: uuid.UUID,
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_membership(business_id, user, db); set_tenant_context(db, business_id)
    service = db.scalar(select(Service).where(Service.id == service_id, Service.business_id == business_id))
    if service is None: raise HTTPException(status_code=404, detail="Service not found")
    employee_ids = db.scalars(select(ServiceEmployeeEligibility.employee_id).where(
        ServiceEmployeeEligibility.business_id == business_id,
        ServiceEmployeeEligibility.service_id == service_id)).all()
    requirements = db.execute(select(ServiceResourceRequirement, SchedulableResource.name,
        SchedulableResource.resource_type).join(SchedulableResource,
        (SchedulableResource.business_id == ServiceResourceRequirement.business_id) &
        (SchedulableResource.id == ServiceResourceRequirement.resource_id)).where(
        ServiceResourceRequirement.business_id == business_id,
        ServiceResourceRequirement.service_id == service_id)).all()
    return {"service_id": service_id, "employee_ids": employee_ids,
            "resource_requirements": [{"resource_id": row.resource_id, "name": name,
                "resource_type": kind, "quantity": row.quantity} for row, name, kind in requirements]}


@router.put("/services/{service_id}/scheduling")
def replace_service_scheduling(business_id: uuid.UUID, service_id: uuid.UUID, payload: dict,
                               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    service = db.scalar(select(Service).where(Service.id == service_id,
        Service.business_id == business.id).with_for_update())
    if service is None: raise HTTPException(status_code=404, detail="Service not found")
    employee_ids = payload.get("employee_ids", [])
    requirements = payload.get("resource_requirements", [])
    if not isinstance(employee_ids, list) or not isinstance(requirements, list):
        raise HTTPException(status_code=422, detail="employee_ids and resource_requirements must be lists")
    try:
        employee_ids = list(dict.fromkeys(uuid.UUID(str(value)) for value in employee_ids))
        parsed = [(uuid.UUID(str(item["resource_id"])), int(item.get("quantity", 1)))
                  for item in requirements]
    except (ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(status_code=422, detail="Invalid employee or resource assignment") from None
    if any(quantity < 1 or quantity > 1000 for _, quantity in parsed):
        raise HTTPException(status_code=422, detail="Resource quantity must be between 1 and 1000")
    if len({resource_id for resource_id, _ in parsed}) != len(parsed):
        raise HTTPException(status_code=422, detail="Each resource can only be assigned once")
    if service.requires_employee and not employee_ids:
        raise HTTPException(status_code=422, detail="Assign at least one eligible team member to this service")
    valid_employees = set(db.scalars(select(Employee.id).where(
        Employee.business_id == business.id, Employee.id.in_(employee_ids),
        Employee.status == "active")).all()) if employee_ids else set()
    if valid_employees != set(employee_ids):
        raise HTTPException(status_code=422, detail="One or more team members are not active in this business")
    resource_ids = [resource_id for resource_id, _ in parsed]
    resources = db.scalars(select(SchedulableResource).where(
        SchedulableResource.business_id == business.id,
        SchedulableResource.id.in_(resource_ids), SchedulableResource.status == "active")).all() if resource_ids else []
    resources_by_id = {item.id: item for item in resources}
    if set(resources_by_id) != set(resource_ids):
        raise HTTPException(status_code=422, detail="One or more resources are not active in this business")
    if any(quantity > resources_by_id[resource_id].capacity for resource_id, quantity in parsed):
        raise HTTPException(status_code=422, detail="Required quantity cannot exceed resource capacity")
    db.execute(delete(ServiceEmployeeEligibility).where(
        ServiceEmployeeEligibility.business_id == business.id,
        ServiceEmployeeEligibility.service_id == service.id))
    db.execute(delete(ServiceResourceRequirement).where(
        ServiceResourceRequirement.business_id == business.id,
        ServiceResourceRequirement.service_id == service.id))
    for employee_id in employee_ids:
        db.add(ServiceEmployeeEligibility(business_id=business.id, service_id=service.id, employee_id=employee_id))
    for resource_id, quantity in parsed:
        db.add(ServiceResourceRequirement(business_id=business.id, service_id=service.id,
            resource_id=resource_id, quantity=quantity))
    _audit(db, business.id, user.id, "service.scheduling_updated", "service", service.id)
    db.commit()
    return {"service_id": service.id, "employee_ids": employee_ids,
            "resource_requirements": [{"resource_id": resource_id, "quantity": quantity}
                                      for resource_id, quantity in parsed]}


@router.get("/scheduling-options")
def list_scheduling_options(business_id: uuid.UUID, user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    require_membership(business_id, user, db); set_tenant_context(db, business_id)
    employees = db.scalars(select(Employee).where(Employee.business_id == business_id,
        Employee.status == "active").order_by(Employee.display_name.asc())).all()
    resources = db.scalars(select(SchedulableResource).where(
        SchedulableResource.business_id == business_id, SchedulableResource.status == "active")
        .order_by(SchedulableResource.name.asc())).all()
    return {"employees": [{"id": item.id, "display_name": item.display_name} for item in employees],
            "resources": [{"id": item.id, "name": item.name, "resource_type": item.resource_type,
                           "capacity": item.capacity} for item in resources]}


@router.get("/team", response_model=list[EmployeeResponse])
def list_team(business_id: uuid.UUID, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    require_membership(business_id, user, db); set_tenant_context(db, business_id)
    return list(db.scalars(select(Employee).where(Employee.business_id == business_id)
        .order_by(Employee.display_name.asc())).all())


@router.post("/team", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_team_member(business_id: uuid.UUID, payload: EmployeeCreate,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    employee = Employee(business_id=business.id, **payload.model_dump())
    db.add(employee); db.flush()
    _audit(db, business.id, user.id, "employee.created", "employee", employee.id)
    db.commit(); db.refresh(employee)
    return employee


@router.patch("/team/{employee_id}", response_model=EmployeeResponse)
def update_team_member(business_id: uuid.UUID, employee_id: uuid.UUID, payload: EmployeeUpdate,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    employee = db.scalar(select(Employee).where(Employee.id == employee_id,
        Employee.business_id == business.id).with_for_update())
    if employee is None: raise HTTPException(status_code=404, detail="Team member not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(employee, key, value)
    _audit(db, business.id, user.id, "employee.updated", "employee", employee.id)
    db.commit(); db.refresh(employee)
    return employee


@router.get("/resources", response_model=list[ResourceResponse])
def list_resources(business_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_membership(business_id, user, db); set_tenant_context(db, business_id)
    return list(db.scalars(select(SchedulableResource).where(
        SchedulableResource.business_id == business_id).order_by(SchedulableResource.name.asc())).all())


@router.post("/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(business_id: uuid.UUID, payload: ResourceCreate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    resource = SchedulableResource(business_id=business.id, **payload.model_dump())
    db.add(resource); db.flush()
    _audit(db, business.id, user.id, "resource.created", "resource", resource.id)
    db.commit(); db.refresh(resource)
    return resource


@router.patch("/resources/{resource_id}", response_model=ResourceResponse)
def update_resource(business_id: uuid.UUID, resource_id: uuid.UUID, payload: ResourceUpdate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    resource = db.scalar(select(SchedulableResource).where(
        SchedulableResource.id == resource_id, SchedulableResource.business_id == business.id
    ).with_for_update())
    if resource is None: raise HTTPException(status_code=404, detail="Resource not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(resource, key, value)
    _audit(db, business.id, user.id, "resource.updated", "resource", resource.id)
    db.commit(); db.refresh(resource)
    return resource
