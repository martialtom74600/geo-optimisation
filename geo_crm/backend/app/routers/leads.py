from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead
from app.schemas import LeadOut, LeadUpdate

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    crm_status: str | None = None,
    proof_status: str | None = None,
    city: str | None = None,
    q: str | None = None,
    order: str | None = None,
    limit: int = Query(200, le=2000),
) -> list[Lead]:
    stmt = select(Lead)
    if crm_status:
        stmt = stmt.where(Lead.crm_status == crm_status)
    if proof_status:
        stmt = stmt.where(Lead.proof_status == proof_status)
    if city:
        stmt = stmt.where(Lead.city.ilike(f"%{city}%"))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Lead.company_name.ilike(like),
                Lead.url.ilike(like),
                Lead.metier.ilike(like),
            )
        )
    if order == "score_desc":
        stmt = stmt.order_by(
            Lead.score_opportunite_geo.desc().nulls_last(), Lead.created_at.desc()
        )
    elif order == "score_asc":
        stmt = stmt.order_by(
            Lead.score_opportunite_geo.asc().nulls_last(), Lead.created_at.desc()
        )
    else:
        stmt = stmt.order_by(Lead.created_at.desc())
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    l = db.get(Lead, lead_id)
    if not l:
        raise HTTPException(404, "Lead introuvable")
    return l


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)
) -> Lead:
    l = db.get(Lead, lead_id)
    if not l:
        raise HTTPException(404, "Lead introuvable")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "crm_status" and value is not None:
            if value not in ("new", "to_contact", "won", "lost"):
                raise HTTPException(400, "crm_status invalide")
        setattr(l, key, value)
    db.add(l)
    db.commit()
    db.refresh(l)
    return l


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> None:
    l = db.get(Lead, lead_id)
    if not l:
        raise HTTPException(404, "Lead introuvable")
    db.delete(l)
    db.commit()
