import unittest
from unittest.mock import MagicMock
from flask import render_template
from src import app
from src.models import Registration


class TestInstallmentsAdjustment(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.app = app
        self.client = app.test_client()

    def test_property_for_mapped_ids(self):
        """Verifica se a property identifica os IDs alterados de 4x para 2x."""
        reg_mapped = Registration(id=65, full_name="Evelly Fabíola", status="AGUARDANDO_CONFIRMACAO", installments=2)
        self.assertTrue(reg_mapped.installments_adjusted_to_2x)

        reg_normal = Registration(id=9999, full_name="Normal User", status="AGUARDANDO_CONFIRMACAO", installments=2)
        self.assertFalse(reg_normal.installments_adjusted_to_2x)

    def test_panel_template_shows_alert_when_adjusted_and_not_confirmed(self):
        """Garante que o aviso aparece no painel para usuários afetados não confirmados."""
        with self.app.test_request_context("/painel"):
            reg_mock = MagicMock()
            reg_mock.id = 65
            reg_mock.full_name = "Evelly Fabíola"
            reg_mock.iap_local = "Central"
            reg_mock.transport = "onibus"
            reg_mock.status = "AGUARDANDO_CONFIRMACAO"
            reg_mock.status_message = "Aguardando confirmação do pagamento."
            reg_mock.payment_type = "pix"
            reg_mock.installments = 2
            reg_mock.installments_adjusted_to_2x = True
            reg_mock.lot_name = "1_LOTE"
            reg_mock.lot_value_cents = 20009
            reg_mock.proof_file_path = None
            reg_mock.proof_uploaded_at = None

            html = render_template(
                "convencao_jovem/dashboard/painel.html",
                reg=reg_mock,
                lot_info="R$200,09",
                pix_prices={"v1": 200.09, "v2": 100.09},
                credit_link="https://exemplo.com",
                pix_payloads={1: "payload1", 2: "payload2"},
                contato_pagamento="92999999999",
                contato_pagamento_texto="WhatsApp",
                inclui_itens=["Item 1"],
                criancas_msg="Aviso crianças",
            )

            # Verifica se o banner de aviso está presente
            self.assertIn("Aviso Importante", html)
            self.assertIn("Seu parcelamento foi alterado para 2x", html)
            self.assertIn("ainda não foi confirmada por falta de pagamento", html)
            self.assertIn("evento está bem próximo", html)
            self.assertIn("Atualizado para 2x", html)

    def test_panel_template_hides_alert_when_confirmed(self):
        """Garante que o aviso NÃO aparece se a inscrição já estiver CONFIRMADA."""
        with self.app.test_request_context("/painel"):
            reg_mock = MagicMock()
            reg_mock.id = 65
            reg_mock.full_name = "Evelly Fabíola"
            reg_mock.iap_local = "Central"
            reg_mock.transport = "onibus"
            reg_mock.status = "CONFIRMADA"
            reg_mock.status_message = "Inscrição confirmada."
            reg_mock.payment_type = "pix"
            reg_mock.installments = 2
            reg_mock.installments_adjusted_to_2x = True
            reg_mock.lot_name = "1_LOTE"
            reg_mock.lot_value_cents = 20009
            reg_mock.proof_file_path = "comprovante.jpg"
            reg_mock.proof_uploaded_at = None

            html = render_template(
                "convencao_jovem/dashboard/painel.html",
                reg=reg_mock,
                lot_info="R$200,09",
                pix_prices={"v1": 200.09, "v2": 100.09},
                credit_link="https://exemplo.com",
                pix_payloads={1: "payload1", 2: "payload2"},
                contato_pagamento="92999999999",
                contato_pagamento_texto="WhatsApp",
                inclui_itens=["Item 1"],
                criancas_msg="Aviso crianças",
            )

            # O banner de aviso NÃO deve ser exibido quando CONFIRMADA
            self.assertNotIn("Seu parcelamento foi alterado para 2x", html)
            self.assertNotIn("Atualizado para 2x", html)

    def test_login_flash_for_adjusted_installments(self):
        """Garante que a mensagem flash de aviso é disparada no login para usuários reajustados."""
        from flask import get_flashed_messages
        from unittest.mock import patch
        from src.models import User

        with self.app.test_request_context("/login", method="POST"):
            mock_user = MagicMock(spec=User)
            mock_user.id = 65
            mock_user.email = "evelly@teste.com"
            mock_user.must_change_password = False
            mock_user.check_password.return_value = True

            reg_mock = MagicMock()
            reg_mock.id = 65
            reg_mock.status = "AGUARDANDO_CONFIRMACAO"
            reg_mock.installments_adjusted_to_2x = True
            mock_user.registration = reg_mock

            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.email.data = "evelly@teste.com"
            mock_form.password.data = "123456"

            with patch("src.routes.auth.User.query") as mock_query, \
                 patch("src.routes.auth.LoginForm", return_value=mock_form), \
                 patch("src.routes.auth.login_user"):
                mock_query.filter_by.return_value.first.return_value = mock_user

                from src.routes.auth import login
                response = login()

                messages = get_flashed_messages(with_categories=True)
                warning_messages = [m for cat, m in messages if cat == "warning"]
                self.assertTrue(any("alterado para 2x" in m for m in warning_messages))
                self.assertTrue(any("evento está muito próximo" in m for m in warning_messages))


if __name__ == "__main__":
    unittest.main()
