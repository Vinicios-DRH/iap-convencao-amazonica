from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import validate_csrf

from src import app
from src.decorators import cms_manager_required
from src.forms import MandateForm, MandateMemberForm, MinistryForm, MinistrySocialLinkForm
from src.models import Ministry, MinistryMandate, MinistryMandateMember, MinistrySocialLink, User
from src.services.portal.inline_uploads import upload_inline_image
from src.services.portal.ministries import (
    create_mandate,
    create_member,
    create_ministry,
    create_ministry_social_link,
    get_current_mandate,
    list_mandates,
    list_members,
    list_ministries,
    list_ministry_social_links,
    set_current_mandate,
    set_member_active,
    set_ministry_active,
    set_ministry_social_link_active,
    update_member,
    update_ministry,
    update_ministry_social_link,
)

NO_USER_CHOICE = (0, "— nenhum —")


def _get_ministry_or_404(ministry_id) -> Ministry:
    return Ministry.query.get_or_404(ministry_id)


def _populate_user_choices(form):
    users = User.query.order_by(User.email).all()
    form.user_id.choices = [NO_USER_CHOICE] + [(u.id, u.email) for u in users]


# ===== ministério =====

@app.route("/portal/painel/ministerios")
@cms_manager_required
def portal_manage_ministries():
    return render_template("portal/manage/ministries_list.html", ministries=list_ministries())


@app.route("/portal/painel/ministerios/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_new():
    form = MinistryForm()

    if form.validate_on_submit():
        create_ministry(form, actor_user_id=current_user.id)
        flash("Ministério criado com sucesso!", "success")
        return redirect(url_for("portal_manage_ministries"))

    return render_template("portal/manage/ministry_form.html", form=form, ministry=None)


@app.route("/portal/painel/ministerios/<int:ministry_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_edit(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    form = MinistryForm(obj=ministry)

    if form.validate_on_submit():
        update_ministry(ministry, form, actor_user_id=current_user.id)
        flash("Ministério atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_ministries"))

    return render_template("portal/manage/ministry_form.html", form=form, ministry=ministry)


@app.route("/portal/painel/ministerios/upload-imagem", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_upload_image():
    """Mesmo papel de portal_manage_post_upload_image, mas pro editor da descrição
    do ministério — pasta e álbum próprios na Galeria, pra não misturar com artigos."""
    try:
        validate_csrf(request.form.get("csrf_token"))
    except CSRFValidationError:
        return jsonify({"error": "Sessão expirada, recarregue a página e tente de novo."}), 400

    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    url = upload_inline_image(
        image,
        request.form.get("description"),
        folder="cms/ministries/corpo",
        album="Ministérios",
        default_caption="Imagem inserida na descrição do ministério",
    )
    return jsonify({"url": url})


@app.route("/portal/painel/ministerios/<int:ministry_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_hide(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    set_ministry_active(ministry, is_active=False, actor_user_id=current_user.id)
    flash("Ministério ocultado.", "info")
    return redirect(url_for("portal_manage_ministries"))


@app.route("/portal/painel/ministerios/<int:ministry_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_show(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    set_ministry_active(ministry, is_active=True, actor_user_id=current_user.id)
    flash("Ministério reativado.", "success")
    return redirect(url_for("portal_manage_ministries"))


# ===== mandatos de liderança =====

def _get_mandate_or_404(ministry: Ministry, mandate_id) -> MinistryMandate:
    mandate = MinistryMandate.query.get_or_404(mandate_id)
    if mandate.ministry_id != ministry.id:
        abort(404)
    return mandate


def _get_mandate_member_or_404(mandate: MinistryMandate, member_id) -> MinistryMandateMember:
    member = MinistryMandateMember.query.get_or_404(member_id)
    if member.mandate_id != mandate.id:
        abort(404)
    return member


@app.route("/portal/painel/ministerios/<int:ministry_id>/mandatos")
@cms_manager_required
def portal_manage_ministry_mandates(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    return render_template(
        "portal/manage/ministry_mandates_list.html",
        ministry=ministry,
        mandates=list_mandates(ministry),
        current_mandate=get_current_mandate(ministry),
    )


@app.route("/portal/painel/ministerios/<int:ministry_id>/mandatos/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_mandate_new(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    form = MandateForm()

    if form.validate_on_submit():
        create_mandate(ministry, form, actor_user_id=current_user.id)
        flash("Mandato criado com sucesso! Agora adicione os membros.", "success")
        return redirect(url_for("portal_manage_ministry_mandates", ministry_id=ministry.id))

    return render_template("portal/manage/mandate_form.html", form=form, ministry=ministry, board=False)


@app.route("/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/tornar-atual", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_mandate_set_current(ministry_id, mandate_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    set_current_mandate(ministry, mandate, actor_user_id=current_user.id)
    flash(f'"{mandate.label}" agora é o mandato atual, visível no site.', "success")
    return redirect(url_for("portal_manage_ministry_mandates", ministry_id=ministry.id))


# ===== membros (dentro de um mandato) =====

@app.route("/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/membros")
@cms_manager_required
def portal_manage_ministry_mandate_members(ministry_id, mandate_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    return render_template(
        "portal/manage/mandate_members_list.html",
        ministry=ministry,
        mandate=mandate,
        members=list_members(mandate),
        board=False,
    )


@app.route("/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/membros/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_mandate_member_new(ministry_id, mandate_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    form = MandateMemberForm()
    _populate_user_choices(form)

    if form.validate_on_submit():
        create_member(mandate, form, actor_user_id=current_user.id)
        flash("Membro adicionado com sucesso!", "success")
        return redirect(url_for("portal_manage_ministry_mandate_members", ministry_id=ministry.id, mandate_id=mandate.id))

    return render_template(
        "portal/manage/mandate_member_form.html", form=form, ministry=ministry, mandate=mandate, member=None, board=False
    )


@app.route(
    "/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/membros/<int:member_id>/editar",
    methods=["GET", "POST"],
)
@cms_manager_required
def portal_manage_ministry_mandate_member_edit(ministry_id, mandate_id, member_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    member = _get_mandate_member_or_404(mandate, member_id)

    form = MandateMemberForm(obj=member)
    _populate_user_choices(form)

    if form.validate_on_submit():
        update_member(member, form, actor_user_id=current_user.id)
        flash("Membro atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_ministry_mandate_members", ministry_id=ministry.id, mandate_id=mandate.id))

    return render_template(
        "portal/manage/mandate_member_form.html", form=form, ministry=ministry, mandate=mandate, member=member, board=False
    )


@app.route(
    "/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/membros/<int:member_id>/ocultar",
    methods=["POST"],
)
@cms_manager_required
def portal_manage_ministry_mandate_member_hide(ministry_id, mandate_id, member_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    member = _get_mandate_member_or_404(mandate, member_id)
    set_member_active(member, is_active=False, actor_user_id=current_user.id)
    flash("Membro ocultado.", "info")
    return redirect(url_for("portal_manage_ministry_mandate_members", ministry_id=ministry_id, mandate_id=mandate_id))


@app.route(
    "/portal/painel/ministerios/<int:ministry_id>/mandatos/<int:mandate_id>/membros/<int:member_id>/reativar",
    methods=["POST"],
)
@cms_manager_required
def portal_manage_ministry_mandate_member_show(ministry_id, mandate_id, member_id):
    ministry = _get_ministry_or_404(ministry_id)
    mandate = _get_mandate_or_404(ministry, mandate_id)
    member = _get_mandate_member_or_404(mandate, member_id)
    set_member_active(member, is_active=True, actor_user_id=current_user.id)
    flash("Membro reativado.", "success")
    return redirect(url_for("portal_manage_ministry_mandate_members", ministry_id=ministry_id, mandate_id=mandate_id))


# ===== redes sociais do ministério =====

@app.route("/portal/painel/ministerios/<int:ministry_id>/redes-sociais")
@cms_manager_required
def portal_manage_ministry_social_links(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    return render_template(
        "portal/manage/ministry_social_links_list.html",
        ministry=ministry,
        links=list_ministry_social_links(ministry),
    )


@app.route("/portal/painel/ministerios/<int:ministry_id>/redes-sociais/nova", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_social_link_new(ministry_id):
    ministry = _get_ministry_or_404(ministry_id)
    form = MinistrySocialLinkForm()

    if form.validate_on_submit():
        create_ministry_social_link(ministry, form, actor_user_id=current_user.id)
        flash("Rede social adicionada com sucesso!", "success")
        return redirect(url_for("portal_manage_ministry_social_links", ministry_id=ministry.id))

    return render_template("portal/manage/ministry_social_link_form.html", form=form, ministry=ministry, link=None)


@app.route("/portal/painel/ministerios/<int:ministry_id>/redes-sociais/<int:link_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_ministry_social_link_edit(ministry_id, link_id):
    ministry = _get_ministry_or_404(ministry_id)
    link = MinistrySocialLink.query.get_or_404(link_id)
    if link.ministry_id != ministry.id:
        abort(404)

    form = MinistrySocialLinkForm(obj=link)

    if form.validate_on_submit():
        update_ministry_social_link(link, form, actor_user_id=current_user.id)
        flash("Rede social atualizada com sucesso!", "success")
        return redirect(url_for("portal_manage_ministry_social_links", ministry_id=ministry.id))

    return render_template("portal/manage/ministry_social_link_form.html", form=form, ministry=ministry, link=link)


@app.route("/portal/painel/ministerios/<int:ministry_id>/redes-sociais/<int:link_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_social_link_hide(ministry_id, link_id):
    link = MinistrySocialLink.query.get_or_404(link_id)
    set_ministry_social_link_active(link, is_active=False, actor_user_id=current_user.id)
    flash("Rede social ocultada.", "info")
    return redirect(url_for("portal_manage_ministry_social_links", ministry_id=ministry_id))


@app.route("/portal/painel/ministerios/<int:ministry_id>/redes-sociais/<int:link_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_ministry_social_link_show(ministry_id, link_id):
    link = MinistrySocialLink.query.get_or_404(link_id)
    set_ministry_social_link_active(link, is_active=True, actor_user_id=current_user.id)
    flash("Rede social reativada.", "success")
    return redirect(url_for("portal_manage_ministry_social_links", ministry_id=ministry_id))
