from src import database, bcrypt, login_manager
from flask_login import UserMixin
from datetime import datetime
import pytz
from sqlalchemy import UniqueConstraint

fuso_am = pytz.timezone("America/Manaus")


def agora_manaus():
    return datetime.now(fuso_am)


user_roles = database.Table(
    "user_roles",
    database.Column("user_id", database.Integer,
                    database.ForeignKey("users.id"), primary_key=True),
    database.Column("role_id", database.Integer,
                    database.ForeignKey("roles.id"), primary_key=True),
)


class Role(database.Model):
    __tablename__ = "roles"
    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(50), unique=True, nullable=False)

    # permissões simples (MVP)
    is_super = database.Column(database.Boolean, default=False)
    can_access_admin = database.Column(database.Boolean, default=False)
    can_review_payments = database.Column(database.Boolean, default=False)

    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Role {self.name}>"


class User(database.Model, UserMixin):
    __tablename__ = "users"
    id = database.Column(database.Integer, primary_key=True)

    email = database.Column(database.String(
        120), unique=True, nullable=False, index=True)
    password_hash = database.Column(database.String(255), nullable=False)

    must_change_password = database.Column(
        database.Boolean, default=False)  # NOVO
    password_reset_at = database.Column(database.DateTime, nullable=True)

    is_active = database.Column(database.Boolean, default=True)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    roles = database.relationship(
        "Role", secondary=user_roles, backref="users")

    # 1 usuário -> 1 inscrição (você pode mudar pra 1:N depois)
    registration = database.relationship(
        "Registration",
        back_populates="user",
        uselist=False,
        foreign_keys="Registration.user_id"
    )

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(
            password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_super(self) -> bool:
        return any(r.is_super for r in self.roles)

    @property
    def can_access_admin(self) -> bool:
        return self.is_super or any(r.can_access_admin for r in self.roles)

    @property
    def can_review_payments(self) -> bool:
        return self.is_super or any(r.can_review_payments for r in self.roles)

    @property
    def can_manage_cms(self) -> bool:
        return self.is_super or any(r.name == "GESTOR_CMS" for r in self.roles)

    @property
    def display_name(self) -> str:
        if self.registration and self.registration.full_name:
            first_name = self.registration.full_name.strip().split()
            if first_name:
                return first_name[0]
        return self.email

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Registration(database.Model):
    __tablename__ = "registrations"

    id = database.Column(database.Integer, primary_key=True)
    user_id = database.Column(database.Integer, database.ForeignKey(
        "users.id"), unique=True, nullable=False)

    full_name = database.Column(database.String(150), nullable=False)
    cpf = database.Column(database.String(
        14), nullable=False)  # pode vir formatado
    phone = database.Column(database.String(20), nullable=False)
    iap_local = database.Column(database.String(120), nullable=False)

    transport = database.Column(database.String(
        20), nullable=False)  # "onibus" | "carro"
    # "pix" | "cartao" | "dinheiro" etc.
    # payment_method = database.Column(database.String(30), nullable=False)

    lot_name = database.Column(database.String(
        40), nullable=False, default="1_LOTE")
    lot_value_cents = database.Column(
        database.Integer, nullable=False, default=18000)

    payment_type = database.Column(database.String(
        20), nullable=False, default="pix")  # pix | credito
    installments = database.Column(
        database.Integer, nullable=False, default=1)        # 1..3

    status = database.Column(database.String(
        30), nullable=False, default="AGUARDANDO_CONFIRMACAO")
    status_message = database.Column(database.String(255), nullable=True)

    age = database.Column(database.Integer, nullable=True)  # 4.2

    has_kids_u5 = database.Column(
        database.Boolean, default=False, nullable=False)  # 4.1
    kids_u5_names = database.Column(
        database.String(255), nullable=True)  # 4.1 (nome(s))

    agree_no_refund = database.Column(
        database.Boolean, default=False, nullable=False)  # 4.3
    is_church_member = database.Column(
        database.Boolean, default=False, nullable=False)  # 4.4

    # comprovante pix
    proof_file_path = database.Column(database.String(255), nullable=True)
    proof_uploaded_at = database.Column(database.DateTime, nullable=True)

    reviewed_by_user_id = database.Column(
        database.Integer, database.ForeignKey("users.id"), nullable=True)
    reviewed_at = database.Column(database.DateTime, nullable=True)
    review_note = database.Column(database.Text, nullable=True)

    created_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(
        database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("cpf", name="uq_registrations_cpf"),
    )

    user = database.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="registration"
    )

    reviewer = database.relationship(
        "User",
        foreign_keys=[reviewed_by_user_id]
    )

    def __repr__(self):
        return f"<Registration {self.full_name} ({self.status})>"


class AuditLog(database.Model):
    __tablename__ = "audit_logs"
    id = database.Column(database.Integer, primary_key=True)
    actor_user_id = database.Column(
        database.Integer, database.ForeignKey("users.id"), nullable=True)
    action = database.Column(database.String(80), nullable=False)
    details = database.Column(database.Text, nullable=True)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    actor = database.relationship("User", foreign_keys=[actor_user_id])


class AppSetting(database.Model):
    __tablename__ = "app_settings"

    id = database.Column(database.Integer, primary_key=True)
    key = database.Column(database.String(80), unique=True, nullable=False)
    value = database.Column(database.String(255), nullable=False)
    updated_at = database.Column(
        database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoracaoNome(database.Model):
    __tablename__ = "coracao_nome"

    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(120), nullable=False)
    nome_normalizado = database.Column(database.String(
        120), nullable=False, unique=True, index=True)
    created_at = database.Column(
        database.DateTime, default=datetime.utcnow, nullable=False)


# =======================
# CMS DO PORTAL
# =======================

class Author(database.Model):
    __tablename__ = "cms_authors"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(150), nullable=False)
    bio = database.Column(database.Text, nullable=True)
    photo_key = database.Column(database.String(255), nullable=True)
    is_active = database.Column(database.Boolean, default=True, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Author {self.name}>"


class Tag(database.Model):
    __tablename__ = "cms_tags"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(50), nullable=False, unique=True)
    slug = database.Column(database.String(60), nullable=False, unique=True, index=True)

    def __repr__(self):
        return f"<Tag {self.name}>"


cms_post_tags = database.Table(
    "cms_post_tags",
    database.Column("post_id", database.Integer,
                    database.ForeignKey("cms_posts.id"), primary_key=True),
    database.Column("tag_id", database.Integer,
                    database.ForeignKey("cms_tags.id"), primary_key=True),
)


class Ministry(database.Model):
    __tablename__ = "cms_ministries"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(120), nullable=False, unique=True)
    slug = database.Column(database.String(140), nullable=False, unique=True, index=True)
    description = database.Column(database.Text, nullable=True)
    cover_image_key = database.Column(database.String(255), nullable=True)

    is_active = database.Column(database.Boolean, default=True, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Ministry {self.name}>"


class MinistryMandate(database.Model):
    """Um mandato de liderança do ministério (ex: "Mandato 2026-2030"). Trocar de liderança
    cria um mandato novo em vez de sobrescrever o antigo -- só um fica is_current=True por
    vez (regra de aplicação, não de banco -- ver set_current_mandate em services/portal/
    ministries.py), e só esse aparece pro público. Mandatos antigos ficam no painel como
    histórico."""
    __tablename__ = "cms_ministry_mandates"

    id = database.Column(database.Integer, primary_key=True)
    ministry_id = database.Column(database.Integer, database.ForeignKey("cms_ministries.id"), nullable=False)
    ministry = database.relationship("Ministry", backref="mandates")

    label = database.Column(database.String(80), nullable=False)
    is_current = database.Column(database.Boolean, default=False, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MinistryMandate {self.label} (ministry_id={self.ministry_id})>"


class MinistryMandateMember(database.Model):
    __tablename__ = "cms_ministry_mandate_members"

    id = database.Column(database.Integer, primary_key=True)
    mandate_id = database.Column(database.Integer, database.ForeignKey("cms_ministry_mandates.id"), nullable=False)
    mandate = database.relationship("MinistryMandate", backref="members")

    # gancho opcional pra uma conta existente — não é a fonte do nome exibido
    # (ver name abaixo), só referência pra uso futuro (login do próprio membro etc).
    user_id = database.Column(database.Integer, database.ForeignKey("users.id"), nullable=True)
    user = database.relationship("User")

    # sempre digitado pelo operador, mesmo quando user_id está preenchido — desacopla
    # o cartaz público de mudanças na conta e evita usar só o primeiro nome (display_name)
    # num contexto onde faz mais sentido o nome completo.
    name = database.Column(database.String(150), nullable=False)
    role = database.Column(database.String(80), nullable=False)
    photo_key = database.Column(database.String(255), nullable=True)

    order = database.Column(database.Integer, default=0, nullable=False)
    is_active = database.Column(database.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<MinistryMandateMember {self.name} ({self.role})>"


class BoardMandate(database.Model):
    """Mesma ideia de MinistryMandate, mas pra Diretoria da Convenção — que é única (sem
    ministry_id: só existe uma Diretoria, ao contrário dos vários Ministérios)."""
    __tablename__ = "cms_board_mandates"

    id = database.Column(database.Integer, primary_key=True)
    label = database.Column(database.String(80), nullable=False)
    is_current = database.Column(database.Boolean, default=False, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BoardMandate {self.label}>"


class BoardMember(database.Model):
    __tablename__ = "cms_board_members"

    id = database.Column(database.Integer, primary_key=True)
    mandate_id = database.Column(database.Integer, database.ForeignKey("cms_board_mandates.id"), nullable=False)
    mandate = database.relationship("BoardMandate", backref="members")

    user_id = database.Column(database.Integer, database.ForeignKey("users.id"), nullable=True)
    user = database.relationship("User")

    name = database.Column(database.String(150), nullable=False)
    role = database.Column(database.String(80), nullable=False)
    photo_key = database.Column(database.String(255), nullable=True)

    order = database.Column(database.Integer, default=0, nullable=False)
    is_active = database.Column(database.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<BoardMember {self.name} ({self.role})>"


class MinistrySocialLink(database.Model):
    __tablename__ = "cms_ministry_social_links"

    id = database.Column(database.Integer, primary_key=True)
    ministry_id = database.Column(database.Integer, database.ForeignKey("cms_ministries.id"), nullable=False)
    ministry = database.relationship("Ministry", backref="social_links")

    platform = database.Column(database.String(30), nullable=False)
    url = database.Column(database.String(300), nullable=False)

    order = database.Column(database.Integer, default=0, nullable=False)
    is_active = database.Column(database.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<MinistrySocialLink {self.platform}>"


cms_post_ministry = database.Table(
    "cms_post_ministry",
    database.Column("post_id", database.Integer,
                    database.ForeignKey("cms_posts.id"), primary_key=True),
    database.Column("ministry_id", database.Integer,
                    database.ForeignKey("cms_ministries.id"), primary_key=True),
)


class Post(database.Model):
    __tablename__ = "cms_posts"

    id = database.Column(database.Integer, primary_key=True)
    title = database.Column(database.String(200), nullable=False)
    slug = database.Column(database.String(220), nullable=False, unique=True, index=True)
    summary = database.Column(database.Text, nullable=True)
    body = database.Column(database.Text, nullable=True)
    cover_image_key = database.Column(database.String(255), nullable=True)

    # "artigo" hoje; "pagina" reservado para páginas institucionais futuras
    post_type = database.Column(database.String(20), nullable=False, default="artigo")
    category = database.Column(database.String(80), nullable=True)

    author_id = database.Column(database.Integer, database.ForeignKey("cms_authors.id"), nullable=True)
    author = database.relationship("Author")

    tags = database.relationship("Tag", secondary=cms_post_tags, backref="posts")

    # M2M no banco, mas tratado como "no máximo um" na aplicação inteira — use sempre
    # a property `ministry` abaixo (getter/setter) em vez de mexer em `ministries` direto.
    ministries = database.relationship("Ministry", secondary=cms_post_ministry, backref="posts")

    is_published = database.Column(database.Boolean, default=True, nullable=False)
    published_at = database.Column(database.DateTime, nullable=True)

    created_by_user_id = database.Column(database.Integer, database.ForeignKey("users.id"), nullable=True)
    created_by = database.relationship("User")

    created_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def ministry(self):
        return self.ministries[0] if self.ministries else None

    @ministry.setter
    def ministry(self, value):
        self.ministries = [value] if value else []

    def __repr__(self):
        return f"<Post {self.title}>"


class Download(database.Model):
    __tablename__ = "cms_downloads"

    id = database.Column(database.Integer, primary_key=True)
    title = database.Column(database.String(200), nullable=False)
    description = database.Column(database.Text, nullable=True)
    category = database.Column(database.String(80), nullable=True)

    # um dos dois: arquivo enviado (B2) ou link externo colado
    file_key = database.Column(database.String(255), nullable=True)
    external_url = database.Column(database.String(500), nullable=True)

    is_active = database.Column(database.Boolean, default=True, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Download {self.title}>"


class Photo(database.Model):
    __tablename__ = "cms_photos"

    id = database.Column(database.Integer, primary_key=True)
    caption = database.Column(database.String(200), nullable=True)
    image_key = database.Column(database.String(255), nullable=False)
    album = database.Column(database.String(80), nullable=True)

    is_active = database.Column(database.Boolean, default=True, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Photo {self.caption or self.id}>"


class Banner(database.Model):
    __tablename__ = "cms_banners"

    id = database.Column(database.Integer, primary_key=True)
    image_key = database.Column(database.String(255), nullable=False)
    description = database.Column(database.String(200), nullable=False)
    link_url = database.Column(database.String(300), nullable=True)
    order = database.Column(database.Integer, default=0, nullable=False)

    # cor de destaque extraída da própria imagem (ver src/services/portal/colors.py) --
    # usada como fundo do botão "Acesse aqui", pra combinar com cada banner. Nula pra
    # banners criados antes dessa coluna existir (o template cai num laranja padrão).
    accent_color = database.Column(database.String(7), nullable=True)

    is_active = database.Column(database.Boolean, default=True, nullable=False)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Banner {self.description}>"


class NavLink(database.Model):
    __tablename__ = "cms_nav_links"

    id = database.Column(database.Integer, primary_key=True)
    label = database.Column(database.String(80), nullable=False)
    url = database.Column(database.String(300), nullable=True)

    # alternativa ao url manual: linka pra uma página institucional cadastrada no CMS
    # (Post com post_type="pagina") -- ver property target_url logo abaixo.
    page_id = database.Column(database.Integer, database.ForeignKey("cms_posts.id"), nullable=True)
    page = database.relationship("Post")

    parent_id = database.Column(database.Integer, database.ForeignKey("cms_nav_links.id"), nullable=True)
    children = database.relationship(
        "NavLink",
        backref=database.backref("parent", remote_side=[id]),
        order_by="NavLink.order",
    )

    order = database.Column(database.Integer, default=0, nullable=False)
    is_active = database.Column(database.Boolean, default=True, nullable=False)

    @property
    def target_url(self):
        if self.page_id and self.page and self.page.is_published:
            from flask import url_for
            return url_for("portal_page_detail", slug=self.page.slug)
        return self.url or "#"

    def __repr__(self):
        return f"<NavLink {self.label}>"


class SocialLink(database.Model):
    __tablename__ = "cms_social_links"

    id = database.Column(database.Integer, primary_key=True)
    platform = database.Column(database.String(30), nullable=False)
    url = database.Column(database.String(300), nullable=False)

    order = database.Column(database.Integer, default=0, nullable=False)
    is_active = database.Column(database.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<SocialLink {self.platform}>"
