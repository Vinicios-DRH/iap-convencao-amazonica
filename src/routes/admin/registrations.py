from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src import app
from src.decorators import can_admin, can_review, payment_reviewer_required
from src.forms import ReviewRegistrationForm
from src.models import Registration
from src.services.registration import review_registration, search_registrations


@app.route("/admin/inscricoes")
@payment_reviewer_required
def admin_inscricoes():
    if not can_admin():
        abort(403)

    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    per_page = max(10, min(per_page, 100))  # trava entre 10 e 100

    pagination = search_registrations(status=status, query_text=q, page=page, per_page=per_page)

    return render_template(
        "admin/inscricoes.html",
        regs=pagination.items,
        pagination=pagination,
        status=status,
        q=q,
        per_page=per_page,
    )


@app.route("/admin/inscricoes/<int:reg_id>", methods=["GET", "POST"])
@login_required
def admin_inscricao_detalhe(reg_id):
    if not can_review():
        abort(403)

    reg = Registration.query.get_or_404(reg_id)
    form = ReviewRegistrationForm()

    if form.validate_on_submit():
        review_registration(
            reg,
            decision=form.decision.data,
            note=(form.note.data or "").strip(),
            reviewer_id=current_user.id,
        )
        flash("Decisão salva com sucesso!", "success")
        return redirect(url_for("admin_inscricoes", status=request.args.get("status", "")))

    return render_template(
        "admin/inscricao_detalhe.html",
        reg=reg,
        user=reg.user,
        reviewer=reg.reviewer,
        form=form,
    )
