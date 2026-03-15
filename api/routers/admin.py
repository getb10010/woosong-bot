from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from api.dependencies import get_db, get_admin_user
from db.models.user import User
from db.models.message import Message
from db.models.report import Report
from db.models.admin_log import AdminLog

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.onboarding_complete == True)
    )
    banned_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_banned == True)
    )
    total_messages = await db.scalar(select(func.count()).select_from(Message))
    hidden_messages = await db.scalar(
        select(func.count()).select_from(Message).where(Message.is_hidden == True)
    )
    pending_reports = await db.scalar(
        select(func.count()).select_from(Report).where(Report.is_valid == None)
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "total_messages": total_messages,
        "hidden_messages": hidden_messages,
        "pending_reports": pending_reports,
    }


@router.get("/users")
async def list_users(
    section: str = Query(None),
    banned: bool = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if section:
        query = query.where(User.section == section)
    if banned is not None:
        query = query.where(User.is_banned == banned)

    query = query.order_by(desc(User.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "tg_id": u.tg_id,
            "username": u.username,
            "section": u.section,
            "is_banned": u.is_banned,
            "warning_count": u.warning_count,
            "auto_hide_count": u.auto_hide_count,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/reports")
async def list_reports(
    resolved: bool = Query(False),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if resolved:
        query = select(Report).where(Report.is_valid != None)
    else:
        query = select(Report).where(Report.is_valid == None)

    query = query.order_by(desc(Report.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "message_id": r.message_id,
            "reporter_id": r.reporter_id,
            "category": r.category,
            "is_valid": r.is_valid,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    valid: bool = Query(...),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    report.is_valid = valid

    # Егер report негізсіз болса — reporter credibility азайту
    if not valid:
        reporter = await db.execute(
            select(User).where(User.id == report.reporter_id)
        )
        r_user = reporter.scalar_one_or_none()
        if r_user:
            # Барлық report-тарын тексеру
            total = await db.scalar(
                select(func.count()).select_from(Report).where(
                    Report.reporter_id == r_user.id, Report.is_valid != None
                )
            )
            invalid = await db.scalar(
                select(func.count()).select_from(Report).where(
                    Report.reporter_id == r_user.id, Report.is_valid == False
                )
            )
            if total and total > 5:
                r_user.report_credibility = max(0.1, 1.0 - (invalid / total))

    # Audit log
    log = AdminLog(
        admin_id=admin.id,
        action="review_report",
        target_type="report",
        target_id=report_id,
        details={"valid": valid},
    )
    db.add(log)

    return {"status": "resolved", "valid": valid}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    msg.is_hidden = True
    msg.hidden_reason = "admin"

    log = AdminLog(
        admin_id=admin.id,
        action="delete_message",
        target_type="message",
        target_id=message_id,
    )
    db.add(log)

    return {"status": "deleted"}


@router.get("/logs")
async def get_audit_logs(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AdminLog)
        .order_by(desc(AdminLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": l.id,
            "admin_id": l.admin_id,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]