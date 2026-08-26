from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import MandateForm, MandateMemberForm
from src.models import BoardMandate, BoardMember, User
from src.services.portal.board import (
    create_mandate,
    create_member,
    get_current_mandate,
    list_mandates,
    list_members,
    set_current_mandate,
    set_member_active,
    update_member,
)

NO_USER_CHOICE = (0, "— nenhum —")


def _populate_user_choices(form):
    users = User.query.order_by(User.email).all()
    form.user_id.choices = [NO_USER_CHOICE] + [(u.id, u.email) for u in users]


def _get_mandate_or_404(mandate_id) -> BoardMandate:
    return BoardMandate.query.get_or_404(mandate_id)


def _get_member_or_404(mandate: BoardMandate, member_id) -> BoardMember:
    member = BoardMember.query.get_or_404(member_id)
    if member.mandate_id != mandate.id:
        abort(404)
    return member


@app.route("/portal/painel/diretoria")
@cms_manager_required
def portal_manage_board_mandates():
    return render_template(
        "portal/manage/board_mandates_list.html",
        mandates=list_mandates(),
        current_mandate=get_current_mandate(),
    )


@app.route("/portal/painel/diretoria/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_board_mandate_new():
    form = MandateForm()

    if form.validate_on_submit():
        create_mandate(form, actor_user_id=current_user.id)
        flash("Mandato criado com sucesso! Agora adicione os membros.", "success")
        return redirect(url_for("portal_manage_board_mandates"))

    return render_template("portal/manage/mandate_form.html", form=form, ministry=None, board=True)


@app.route("/portal/painel/diretoria/<int:mandate_id>/tornar-atual", methods=["POST"])
@cms_manager_required
def portal_manage_board_mandate_set_current(mandate_id):
    mandate = _get_mandate_or_404(mandate_id)
    set_current_mandate(mandate, actor_user_id=current_user.id)
    flash(f'"{mandate.label}" agora é o mandato atual, visível no site.', "success")
    return redirect(url_for("portal_manage_board_mandates"))


@app.route("/portal/painel/diretoria/<int:mandate_id>/membros")
@cms_manager_required
def portal_manage_board_mandate_members(mandate_id):
    mandate = _get_mandate_or_404(mandate_id)
    return render_template(
        "portal/manage/mandate_members_list.html",
        ministry=None,
        mandate=mandate,
        members=list_members(mandate),
        board=True,
    )


@app.route("/portal/painel/diretoria/<int:mandate_id>/membros/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_board_mandate_member_new(mandate_id):
    mandate = _get_mandate_or_404(mandate_id)
    form = MandateMemberForm()
    _populate_user_choices(form)

    if form.validate_on_submit():
        create_member(mandate, form, actor_user_id=current_user.id)
        flash("Membro adicionado com sucesso!", "success")
        return redirect(url_for("portal_manage_board_mandate_members", mandate_id=mandate.id))

    return render_template(
        "portal/manage/mandate_member_form.html", form=form, ministry=None, mandate=mandate, member=None, board=True
    )


@app.route("/portal/painel/diretoria/<int:mandate_id>/membros/<int:member_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_board_mandate_member_edit(mandate_id, member_id):
    mandate = _get_mandate_or_404(mandate_id)
    member = _get_member_or_404(mandate, member_id)

    form = MandateMemberForm(obj=member)
    _populate_user_choices(form)

    if form.validate_on_submit():
        update_member(member, form, actor_user_id=current_user.id)
        flash("Membro atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_board_mandate_members", mandate_id=mandate.id))

    return render_template(
        "portal/manage/mandate_member_form.html", form=form, ministry=None, mandate=mandate, member=member, board=True
    )


@app.route("/portal/painel/diretoria/<int:mandate_id>/membros/<int:member_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_board_mandate_member_hide(mandate_id, member_id):
    mandate = _get_mandate_or_404(mandate_id)
    member = _get_member_or_404(mandate, member_id)
    set_member_active(member, is_active=False, actor_user_id=current_user.id)
    flash("Membro ocultado.", "info")
    return redirect(url_for("portal_manage_board_mandate_members", mandate_id=mandate_id))


@app.route("/portal/painel/diretoria/<int:mandate_id>/membros/<int:member_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_board_mandate_member_show(mandate_id, member_id):
    mandate = _get_mandate_or_404(mandate_id)
    member = _get_member_or_404(mandate, member_id)
    set_member_active(member, is_active=True, actor_user_id=current_user.id)
    flash("Membro reativado.", "success")
    return redirect(url_for("portal_manage_board_mandate_members", mandate_id=mandate_id))
