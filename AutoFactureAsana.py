import imaplib
import email
from email.header import decode_header
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv()

IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.ionos.fr")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
USERNAME = os.environ.get("IMAP_USERNAME")
PASSWORD = os.environ.get("IMAP_PASSWORD")
API_TOKEN = os.environ.get("ASANA_API_TOKEN")

MAIL_FOLDER = "INBOX/02-STRIPE"
SEARCH_CRITERIA = "UNSEEN"
SENDER = "no-reply@axonaut.com"
MAX_EMAILS = 20

PROJECT_GID = "1205932647714556"
CUSTOM_FIELD_PAIMENT = "1205959178241727"
ENUM_OPTION_PAYE = "1205959178241728"
BASE_URL = "https://app.asana.com/api/1.0"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def get_log_directory():
    appdata = os.environ.get("APPDATA") or os.getcwd()
    log_dir = os.path.join(appdata, "AutoFacture Asana")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

LOG_DIR = get_log_directory()
LOG_FILE = os.path.join(LOG_DIR, "actions.log")
LOG_FILE_ERROR = os.path.join(LOG_DIR, "actions_error.log")

invoice_pattern = re.compile(r"^Votre facture\s+(F\d{8}-\d+)\s+a été payée en ligne", re.IGNORECASE)
client_pattern = re.compile(r"Client\s*:\s*(.+)", re.IGNORECASE)

def test_api():
    url = f"{BASE_URL}/projects/{PROJECT_GID}?opt_expand=custom_field_settings"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return False, f"Erreur API: {response.status_code} - {response.text}"
    project = response.json().get("data", {})
    cf_settings = project.get("custom_field_settings", [])
    field_found = None
    for setting in cf_settings:
        field = setting.get("custom_field", {})
        if field.get("gid") == CUSTOM_FIELD_PAIMENT:
            field_found = field
            break
    if not field_found:
        return False, "Champ 'Paiement CG FRANCE' introuvable dans le projet."
    enum_options = field_found.get("enum_options", [])
    option_found = False
    for option in enum_options:
        if option.get("gid") == ENUM_OPTION_PAYE:
            option_found = True
            break
    if not option_found:
        return False, "L'option 'Payé' introuvable dans le champ 'Paiement CG FRANCE'."
    return True, "L'API est accessible et le champ ainsi que l'option existent."

def connect_imap():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(USERNAME, PASSWORD)
        return mail
    except Exception as e:
        print("Erreur IMAP :", e)
        return None

def fetch_email_ids(mail, folder=MAIL_FOLDER, criteria=SEARCH_CRITERIA):
    if mail.select(folder)[0] != "OK":
        return []
    status, data = mail.search(None, criteria)
    return data[0].split() if status == "OK" else []

def decode_mime_words(s):
    result = []
    for word, encoding in decode_header(s):
        if isinstance(word, bytes):
            result.append(word.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(word)
    return " ".join(result)

def get_email_content(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
        for part in msg.walk():
            if part.get_content_type() == "text/html" and "attachment" not in str(part.get("Content-Disposition")):
                html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                return BeautifulSoup(html, "html.parser").get_text("\n").strip()
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
        return BeautifulSoup(body, "html.parser").get_text("\n").strip() if msg.get_content_type() == "text/html" else body
    return ""

def get_tasks_in_project(project_gid):
    tasks = []
    url = f"{BASE_URL}/projects/{project_gid}/tasks?opt_fields=name&limit=100"
    
    while url:
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            tasks.extend(data.get("data", []))
            next_page = data.get("next_page")
            if next_page:
                url = next_page.get("uri")
            else:
                url = None
        else:
            print("Erreur lors de la récupération des tâches d'Asana:", r.status_code, r.text)
            break
    return tasks


def update_task_payment_field(task_gid, custom_field_id, enum_option_id):
    url = f"{BASE_URL}/tasks/{task_gid}"
    payload = {"data": {"custom_fields": {custom_field_id: enum_option_id}}}
    r = requests.put(url, headers=HEADERS, json=payload)
    if r.status_code == 200:
        return True
    else:
        print(f"Échec de mise à jour pour la tâche {task_gid}: {r.status_code} - {r.text}")
        return False

def find_task_by_invoice(invoice_number):
    tasks = get_tasks_in_project(PROJECT_GID)
    found_task_gid = None
    for task in tasks:
        name = task.get("name", "")
        matches = re.findall(r"(F\d{8}-\d+)", name)
        if invoice_number in matches:
            found_task_gid = task.get("gid")
            break
    return found_task_gid


def update_asana_for_invoice(invoice_number):
    task_gid = find_task_by_invoice(invoice_number)
    return update_task_payment_field(task_gid, CUSTOM_FIELD_PAIMENT, ENUM_OPTION_PAYE) if task_gid else False

def log_action(invoice, client):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - Facture: {invoice}, Client: {client}\n")

def log_action_error(invoice, client):
    with open(LOG_FILE_ERROR, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - Erreur: Facture: {invoice}, Client: {client}\n")

dark_bg = "#2e2e2e"
dark_fg = "#ffffff"
entry_bg = "#3e3e3e"
button_bg = "#4e4e4e"

root = tk.Tk()
root.title("AutoFacture Asana")
root.configure(bg=dark_bg)

status, msg = test_api()
if not status:
    messagebox.showerror("Test API", msg)

frame = tk.Frame(root, padx=10, pady=10, bg=dark_bg)
frame.pack(fill=tk.BOTH, expand=True)

app_title = tk.Label(frame, text="AutoFacture Asana", bg=dark_bg, fg=dark_fg, font=("Segoe UI", 14, "bold"))
app_title.pack(pady=(0,10))

scan_button = tk.Button(frame, text="Scanner les e-mails", command=lambda: on_scan_click(),
                        bg=button_bg, fg=dark_fg, activebackground="#606060", font=("Segoe UI", 10, "bold"))
scan_button.pack(pady=5)

output_text = scrolledtext.ScrolledText(frame, width=80, height=20, bg=entry_bg, fg=dark_fg, insertbackground=dark_fg)
output_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))
output_text.tag_configure("success", foreground="green")
output_text.tag_configure("failure", foreground="red")

def on_scan_click():
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Scan des e-mails en cours...\n")
    invoices = scan_emails()
    if invoices:
        output_text.insert(tk.END, f"\n{len(invoices)} facture(s) trouvée(s).\n", "success")
        for inv, cli in invoices:
            output_text.insert(tk.END, f"Facture: {inv} | Client: {cli}\n", "success")
        open_results_window(invoices)
    else:
        output_text.insert(tk.END, "\nAucune facture trouvée.\n", "failure")

def open_results_window(invoices):
    results_window = tk.Toplevel(root)
    results_window.title("Résultats")
    results_window.configure(bg=dark_bg)
    header = tk.Label(results_window, text="Factures extraites", bg=dark_bg, fg=dark_fg, font=("Segoe UI", 12, "bold"))
    header.pack(pady=10)
    rows_info = []
    for invoice, client in invoices:
        row = tk.Frame(results_window, bg=dark_bg)
        row.pack(fill=tk.X, padx=10, pady=5)
        info_label = tk.Label(row, text=f"Facture: {invoice} | Client: {client}", bg=dark_bg, fg=dark_fg, font=("Segoe UI", 10))
        info_label.pack(side=tk.LEFT, padx=(0,10))
        status_label = tk.Label(row, text="", bg=dark_bg, font=("Segoe UI", 10, "bold"))
        status_label.pack(side=tk.LEFT, padx=(0,10))
        btn = tk.Button(row, text="Asana Payé", bg=button_bg, fg=dark_fg, activebackground="#606060",
                        font=("Segoe UI", 10, "bold"),
                        command=lambda inv=invoice, cli=client, lab=status_label: on_asana_paye(inv, cli, lab))
        btn.pack(side=tk.RIGHT)
        rows_info.append((invoice, client, status_label))
    update_all_btn = tk.Button(results_window, text="Tout mettre à jour", bg=button_bg, fg=dark_fg, activebackground="#606060",
                                 font=("Segoe UI", 10, "bold"),
                                 command=lambda: update_all(rows_info))
    update_all_btn.pack(pady=10)
    close_btn = tk.Button(results_window, text="Fermer", command=results_window.destroy,
                          bg=button_bg, fg=dark_fg, activebackground="#606060", font=("Segoe UI", 10, "bold"))
    close_btn.pack(pady=10)

def update_all(rows_info):
    for invoice, client, status_label in rows_info:
        on_asana_paye(invoice, client, status_label)

def on_asana_paye(invoice, client, status_label):
    success = update_asana_for_invoice(invoice)
    if success:
        status_label.config(text="Mis à jour", fg="green")
        log_action(invoice, client)
    else:
        status_label.config(text="Erreur", fg="red")
        log_action_error(invoice, client)

def scan_emails():
    mail = connect_imap()
    if not mail:
        messagebox.showerror("Erreur", "Impossible de se connecter au serveur IMAP.")
        return []
    
    email_ids = fetch_email_ids(mail)
    if not email_ids:
        status, data = mail.search(None, "ALL")
        if status == "OK":
            email_ids = data[0].split()
        else:
            mail.logout()
            return []
    
    extracted = []
    for mail_id in email_ids[-MAX_EMAILS:]:
        status, data = mail.fetch(mail_id, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(data[0][1])
        subject = decode_mime_words(msg.get("Subject", ""))
        if not subject.lower().startswith("votre facture"):
            continue
        invoice_match = invoice_pattern.search(subject)
        invoice_number = invoice_match.group(1) if invoice_match else "Inconnu"
        body = get_email_content(msg)
        client_match = client_pattern.search(body)
        client_name = client_match.group(1).strip() if client_match else "Inconnu"
        extracted.append((invoice_number, client_name))

    mail.logout()
    return extracted

root.mainloop()
