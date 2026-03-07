# enviar_emails_convencao.py
# ✅ Duplo clique pra rodar (abre janela)
# Requisitos: Python instalado no PC (3.10+)
# (Tkinter já vem junto no Windows normalmente)

import ssl
import smtplib
import time
import re
import threading
from email.message import EmailMessage
from email.utils import formataddr
import tkinter as tk
from tkinter import messagebox, scrolledtext

# =========================
# CONFIG FIXA (JÁ DO SEU LINK)
# =========================
FROM_NAME = "Convenção Jovem — Tempo de Resplandecer"
FROM_EMAIL = "convencao.jovem.iap@gmail.com"

LANDING_URL = "https://iap-convencao-amazonica-production.up.railway.app/"
BANNER_URL = "https://iap-convencao-amazonica-production.up.railway.app/static/img/capa2.webp"

WHATSAPP = "(92) 98459-6369"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # STARTTLS

# envio em lotes (pra não estressar SMTP)
BATCH_SIZE = 35
SLEEP_BETWEEN_BATCHES = 2.0

# =========================
# LISTA DE E-MAILS
# =========================
RAW_EMAILS = """
7519957@gmail.com
jflteixeira31@gmail.com
salesauzier13@gmail.com
ronaldenogueira31888@gmail.com
brunofmcosta@gmail.com
werlesonoli@gmail.com
laramelisaa123@gmail.com
marlene.silva.8417@gmail.com
slteixeira17leal@gmail.com
engfelipecostaxp@gmail.com
grazielev892@gmail.com
brenda.15.veiga@gmail.com
eline.veiga30@gmail.com
moniqueoliveira2397@gmail.com
araujo.ria08@gmail.com
vianamarialvadradany@gmail.com
marialvadradany@gmail.com
pauload061@gmail.com
valeriavalentee50@gmail.com
martinsmauricio1717@gmail.com
luizlikegames@gmail.com
alanaalmeida312@gmail.com
alderlisilvasouza@gmail.com
manoelsimao771@gmail.com
nizaleal@gmail.com
debyribei06@gmail.com
camaraoalmeidar@gmail.com
pattyradtec@hotmail.com
urielassuncao012@gmail.com
isaacgois95@gmail.com
lucileiaapinheiro@gmail.com
deusenirpontes20@gmail.com
ebenezerbrito@gmail.com
deusenirpontes@gmail.com
hmfigueredo@hotmail.com
rodriguesgraziela550@gmail.com
lianesantoslopess@gmail.com
lohannafernandess16@gmail.com
franciscomarinhooliveira1968@gmail.com
luzinetefernandes1976@gmail.com
lohannafernandes19@gmail.com
anasophiasilvar6@gmail.com
auziersete82@gmail.com
grazielesvitor@gmail.com
gustavolucasgonzagalopes134@gmail.com
hmfigueredo@hotmail.com
jadsonanjos32@gmail.com
jefersonanjos416@gmail.com
leticiagiselle1903@gmail.com
leticiagiselle2017@gmail.com
nalandadelfino@gmail.com
ritakleuton@gmail.com
rogeriomelo435@gmail.com
ronaldenogueira31888@gmail.com
senagustavo021@gmail.com
sophiakrame@gmail.com
""".strip()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_emails(raw: str) -> list[str]:
    seen = set()
    out = []
    for line in raw.splitlines():
        e = line.strip().lower()
        if not e:
            continue
        if not EMAIL_RE.match(e):
            continue
        if e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def subject() -> str:
    return "⚡ HOJE 23:59 — Último dia do 1º lote (não deixa passar!)"


def text_body() -> str:
    return (
        "Convenção Jovem — Tempo de Resplandecer\n\n"
        "HOJE 23:59 é o último dia do 1º lote promocional.\n"
        "A partir de segunda-feira, o valor será integral.\n\n"
        f"Faça sua inscrição agora: {LANDING_URL}\n"
        f"Dúvidas: {WHATSAPP}\n"
    )


def html_body() -> str:
    return f"""\
<!doctype html>
<html lang="pt-br">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#070711;font-family:Arial,Helvetica,sans-serif;color:#f4f4fb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:
           radial-gradient(900px 500px at 20% 10%, rgba(34,211,238,.18), transparent 60%),
           radial-gradient(900px 500px at 80% 20%, rgba(217,70,239,.20), transparent 60%),
           linear-gradient(180deg, #05050d, #070711);
           padding:24px 12px;">
    <tr><td align="center">

      <table role="presentation" width="640" cellpadding="0" cellspacing="0"
             style="max-width:640px;width:100%;border-radius:18px;overflow:hidden;
                    border:1px solid rgba(255,255,255,.14);
                    background:rgba(255,255,255,.06);">

        <tr>
          <td style="padding:18px;border-bottom:1px solid rgba(255,255,255,.12);background:rgba(0,0,0,.28);">
            <span style="display:inline-block;padding:7px 12px;border-radius:999px;
                         border:1px solid rgba(255,255,255,.16);
                         background:rgba(0,0,0,.22);
                         font-weight:900;letter-spacing:.02em;">
              CONVENÇÃO JOVEM • TEMPO DE RESPLANDECER
            </span>
            <div style="margin-top:10px;color:rgba(255,255,255,.72);font-size:12.5px;">
              “Levanta-te, resplandece, porque já vem a tua luz…” (Is 60:1)
            </div>
          </td>
        </tr>

        <tr><td style="padding:0;">
          <img src="{BANNER_URL}" alt="Capa do evento"
               style="display:block;width:100%;height:auto;border:0;outline:none;">
        </td></tr>

        <tr>
          <td style="padding:20px 18px;">
            <h1 style="margin:0 0 10px;font-size:24px;line-height:1.2;">
              ⏳ <span style="background:linear-gradient(90deg,#22d3ee,#d946ef);
                             -webkit-background-clip:text;background-clip:text;color:transparent;font-weight:1000;">
                Último dia do 1º lote promocional
              </span>
            </h1>

            <div style="margin:0 0 14px;color:rgba(255,255,255,.85);font-size:15px;line-height:1.65;">
              Se você estava “pensando em ir”, deixa eu te falar: <b>hoje é o dia</b>.
              O <b>1º lote</b> vai até <b>hoje às 23:59</b>. A partir de <b>segunda-feira</b>, o valor será <b>integral</b>.
            </div>

            <div style="border-radius:16px;padding:14px;border:1px solid rgba(255,255,255,.14);
                        background:rgba(0,0,0,.22);margin:0 0 14px;">
              <div style="font-weight:900;margin-bottom:6px;">✅ Garanta agora:</div>
              <div style="color:rgba(255,255,255,.86);font-size:14.5px;line-height:1.6;">
                <b>Faça sua inscrição hoje</b> para garantir o lote e o seu cadastro.
                Não deixa pra depois e perder a promoção.
              </div>
            </div>

            <div style="margin:0 0 14px;color:rgba(255,255,255,.84);font-size:15px;line-height:1.65;">
              Serão dias de <b>adoração</b>, <b>palavra</b>, <b>comunhão</b> e <b>renovo</b>.
              Um tempo marcado para uma geração que quer resplandecer a luz do Senhor.
            </div>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0 10px;">
              <tr><td align="center">
                <a href="{LANDING_URL}" target="_blank"
                   style="display:inline-block;text-decoration:none;
                          background:linear-gradient(90deg,#22d3ee,#d946ef);
                          color:#06060c;font-weight:1000;
                          padding:12px 18px;border-radius:12px;">
                  Fazer minha inscrição agora
                </a>
              </td></tr>
            </table>

            <div style="color:rgba(255,255,255,.68);font-size:12.8px;line-height:1.5;">
              Se o botão não abrir, copie e cole no navegador:<br>
              <span style="color:#22d3ee;">{LANDING_URL}</span>
            </div>

            <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.18),transparent);
                        margin:16px 0;"></div>

            <div style="color:rgba(255,255,255,.78);font-size:13px;line-height:1.6;">
              Dúvidas? WhatsApp: <b>{WHATSAPP}</b><br>
              ⚠️ <b>Lembrete:</b> o 1º lote encerra <b>hoje 23:59</b>.
            </div>
          </td>
        </tr>

        <tr>
          <td style="padding:14px 18px;background:rgba(0,0,0,.25);
                     border-top:1px solid rgba(255,255,255,.10);">
            <div style="color:rgba(255,255,255,.55);font-size:12px;line-height:1.5;">
              Você recebeu este e-mail porque está na lista de contatos da Convenção Jovem.
            </div>
          </td>
        </tr>

      </table>

      <div style="max-width:640px;margin:12px auto 0;text-align:center;
                  color:rgba(255,255,255,.45);font-size:12px;line-height:1.5;">
        © Convenção Jovem — Tempo de Resplandecer
      </div>

    </td></tr>
  </table>
</body>
</html>
"""


def build_message(bcc_list: list[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject()
    msg["From"] = formataddr((FROM_NAME, FROM_EMAIL))
    msg["To"] = FROM_EMAIL         # To interno
    msg["Bcc"] = ", ".join(bcc_list)  # lista vai no BCC

    msg.set_content(text_body())
    msg.add_alternative(html_body(), subtype="html")
    return msg


# =========================
# UI + ENVIO
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Envio de e-mails — Convenção Jovem")
        self.geometry("780x520")
        self.resizable(True, True)

        self.emails = clean_emails(RAW_EMAILS)

        top = tk.Frame(self)
        top.pack(fill="x", padx=12, pady=10)

        tk.Label(top, text="Senha de app do Gmail:",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        self.pass_entry = tk.Entry(top, show="*", width=40)
        self.pass_entry.pack(anchor="w", pady=(2, 8))

        info = (
            f"• Envia de: {FROM_EMAIL}\n"
            f"• Link: {LANDING_URL}\n"
            f"• Destinatários (únicos): {len(self.emails)}\n\n"
            "⚠️ Use SENHA DE APP do Gmail (não é a senha normal)."
        )
        tk.Label(top, text=info, fg="#444").pack(anchor="w")

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=12, pady=(0, 8))

        self.send_btn = tk.Button(btns, text="ENVIAR AGORA", bg="#22d3ee", fg="#000", font=("Arial", 10, "bold"),
                                  command=self.on_send)
        self.send_btn.pack(side="left")

        self.test_btn = tk.Button(
            btns, text="TESTAR (enviar só pra mim)", command=self.on_test)
        self.test_btn.pack(side="left", padx=8)

        self.log = scrolledtext.ScrolledText(
            self, height=18, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=12, pady=10)
        self._log(f"[INFO] Pronto. Total de emails únicos: {len(self.emails)}")

    def _log(self, s: str):
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.update_idletasks()

    def on_test(self):
        pwd = self.pass_entry.get().strip()
        if not pwd:
            messagebox.showwarning(
                "Senha faltando", "Digite a SENHA DE APP do Gmail.")
            return
        self.send_btn.config(state="disabled")
        self.test_btn.config(state="disabled")
        t = threading.Thread(target=self._send_worker,
                             args=(pwd, True), daemon=True)
        t.start()

    def on_send(self):
        pwd = self.pass_entry.get().strip()
        if not pwd:
            messagebox.showwarning(
                "Senha faltando", "Digite a SENHA DE APP do Gmail.")
            return

        if not self.emails:
            messagebox.showerror(
                "Sem emails", "A lista de emails está vazia ou inválida.")
            return

        ok = messagebox.askyesno(
            "Confirmar envio", f"Você vai enviar para {len(self.emails)} pessoas (BCC).\nContinuar?")
        if not ok:
            return

        self.send_btn.config(state="disabled")
        self.test_btn.config(state="disabled")
        t = threading.Thread(target=self._send_worker,
                             args=(pwd, False), daemon=True)
        t.start()

    def _send_worker(self, pwd: str, only_me: bool):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=40) as server:
                self._log("[SMTP] Conectando...")
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()

                self._log("[SMTP] Logando...")
                server.login(FROM_EMAIL, pwd)

                if only_me:
                    self._log(
                        "[TESTE] Enviando apenas para o seu próprio e-mail...")
                    msg = build_message([FROM_EMAIL])
                    server.send_message(msg)
                    self._log("[OK] Teste enviado com sucesso.")
                    messagebox.showinfo(
                        "Sucesso", "Email de teste enviado pra sua caixa.")
                    return

                batches = list(chunks(self.emails, BATCH_SIZE))
                total = 0
                for i, batch in enumerate(batches, start=1):
                    msg = build_message(batch)
                    server.send_message(msg)
                    total += len(batch)
                    self._log(
                        f"[OK] Lote {i}/{len(batches)} enviado: {len(batch)} | Total: {total}")
                    if i < len(batches):
                        time.sleep(SLEEP_BETWEEN_BATCHES)

                self._log(f"[DONE] Envio finalizado. Total enviado: {total}")
                messagebox.showinfo(
                    "Finalizado", f"Envio concluído! Total: {total}")

        except smtplib.SMTPAuthenticationError:
            self._log(
                "[ERRO] Falha de autenticação. Isso acontece quando a senha NÃO é senha de app.")
            messagebox.showerror(
                "Falha de login",
                "Falha de autenticação.\n\n"
                "Use SENHA DE APP do Gmail (não a senha normal).\n"
                "Ative verificação em 2 etapas e gere uma senha de app."
            )
        except Exception as e:
            self._log(f"[ERRO] {type(e).__name__}: {e}")
            messagebox.showerror(
                "Erro", f"Ocorreu um erro:\n{type(e).__name__}: {e}")
        finally:
            self.send_btn.config(state="normal")
            self.test_btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
