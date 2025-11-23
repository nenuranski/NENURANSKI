import os
import imaplib
import email
import smtplib
import requests
import markdown
from email.mime.text import MIMEText
import json
import re
&nbsp;
# --- הגדרות קבועות ---
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
THREADS_FILE = "threads.json"
&nbsp;
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
&nbsp;
# --- טעינה ושמירה של השרשורים מקובץ JSON ---
def load_threads():
try:
with open(THREADS_FILE, "r", encoding="utf-8") as f:
return json.load(f)
except FileNotFoundError:
return {}
except Exception as e:
print(f"[!] Error loading threads: {e}")
return {}
&nbsp;
def save_threads(threads):
try:
with open(THREADS_FILE, "w", encoding="utf-8") as f:
json.dump(threads, f, ensure_ascii=False, indent=2)
except Exception as e:
print(f"[!] Error saving threads: {e}")
&nbsp;
# --- ניקוי חתימות והודעות חוזרות ---
def clean_email_body(body):
patterns_to_remove = [
r"--\s*\n.*",# קו חתימה --
r"Sent from my .*",# טקסטים כמו Sent from my iPhone
r"שלח:.*",# שורות של מייל קודם בעברית
r"נשלח:.*",
r"From:.*",
r"To:.*",
r"Cc:.*",
r"Subject:.*",
r"-----Original Message-----",
r"^>+",# ציטוטים מקויים
]
pattern = "|".join(patterns_to_remove)
body = re.split(pattern, body, flags=re.IGNORECASE | re.MULTILINE)[0]
return body.strip()
&nbsp;
# --- קבלת מיילים חדשים ---
def get_unread_emails():
try:
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
mail.select("inbox")
&nbsp;
result, data = mail.search(None, "(UNSEEN)")
unread_msg_nums = data[0].split()
messages = []
&nbsp;
for num in unread_msg_nums:
result, msg_data = mail.fetch(num, "(RFC822)")
raw_email = msg_data[0][1]
msg = email.message_from_bytes(raw_email)
&nbsp;
sender = email.utils.parseaddr(msg["From"])[1]
subject = msg["Subject"] if msg["Subject"] else "(ללא נושא)"
message_id = msg["Message-ID"]
in_reply_to = msg.get("In-Reply-To")
body = ""
&nbsp;
if msg.is_multipart():
for part in msg.walk():
if part.get_content_type() == "text/plain":
charset = part.get_content_charset() or "utf-8"
body += part.get_payload(decode=True).decode(charset, errors="ignore")
else:
charset = msg.get_content_charset() or "utf-8"
body += msg.get_payload(decode=True).decode(charset, errors="ignore")
&nbsp;
body = clean_email_body(body)
&nbsp;
messages.append({
"from": sender,
"subject": subject,
"body": body,
"message_id": message_id,
"in_reply_to": in_reply_to
})
&nbsp;
mail.logout()
return messages
&nbsp;
except Exception as e:
print(f"[!] Error fetching emails: {e}")
return []
&nbsp;
# --- בניית השרשור עבור ג'מיני ---
def build_thread_for_gemini(message, threads):
thread_id = message["in_reply_to"] or message["message_id"]
&nbsp;
if thread_id not in threads:
threads[thread_id] = []
&nbsp;
# הוספת הודעת המשתמש החדשה
threads[thread_id].append({
"from": "user",
"body": message["body"]
})
&nbsp;
# בניית טקסט לג'מיני
gemini_prompt = ""
for msg in threads[thread_id]:
if msg["from"] == "user":
gemini_prompt += f"[משתמש כתב]:\n{msg['body']}\n\n"
elif msg["from"] == "gemini":
gemini_prompt += f"[ג'מיני כתב]:\n{msg['body']}\n\n"
&nbsp;
return gemini_prompt, thread_id
&nbsp;
# --- שליחת מייל כולל שרשור ---
def send_email(to_email, subject, body_text, original_message_id=None):
try:
formatted_text = markdown.markdown(body_text)
&nbsp;
signature = """
<hr>
<div style="color:#666; font-size:14px; margin-top:10px;">
בינה מלאכותית ג'מיני באימייל נבנה ע"י @טשיקאוור ניוז
</div>
"""
&nbsp;
html_body = f"""
<html>
<body style="direction: rtl; text-align: right; font-family: Arial, sans-serif;">
{formatted_text}
{signature}
</body>
</html>
"""
&nbsp;
msg = MIMEText(html_body, "html", "utf-8")
msg["From"] = EMAIL_ACCOUNT
msg["To"] = to_email
msg["Subject"] = subject
&nbsp;
if original_message_id:
msg["In-Reply-To"] = original_message_id
msg["References"] = original_message_id
&nbsp;
with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
server.sendmail(EMAIL_ACCOUNT, to_email, msg.as_string())
&nbsp;
print(f"[✔] Sent reply to {to_email}")
&nbsp;
except Exception as e:
print(f"[!] Error sending email: {e}")
&nbsp;
# --- קבלת תגובה מג'מיני ---
def get_gemini_reply(prompt):
try:
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
&nbsp;
headers = {
"Content-Type": "application/json",
"X-goog-api-key": GEMINI_API_KEY
}
&nbsp;
data = {
"contents": [
{"parts": [{"text": prompt}]}
]
}
&nbsp;
response = requests.post(url, headers=headers, json=data)
&nbsp;
if response.status_code == 200:
result = response.json()
return result["candidates"][0]["content"]["parts"][0]["text"]
&nbsp;
print("[!] Gemini API error:", response.text)
return "אירעה שגיאה בעת יצירת התגובה."
&nbsp;
except Exception as e:
print(f"[!] Error contacting Gemini API: {e}")
return "שגיאה פנימית בתקשורת עם Gemini."
&nbsp;
# --- הפעלת הבוט ---
def main():
print("Starting Gemini Email Bot...")
&nbsp;
threads = load_threads()
emails = get_unread_emails()
&nbsp;
if not emails:
&import os
import imaplib
import email
import smtplib
import requests
import markdown
from email.mime.text import MIMEText
import json
import re
&nbsp;
# --- הגדרות קבועות ---
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
THREADS_FILE = "threads.json"
&nbsp;
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
&nbsp;
# --- טעינה ושמירה של השרשורים מקובץ JSON ---
def load_threads():
&nbsp; &nbsp; try:
&nbsp; &nbsp; &nbsp; &nbsp; with open(THREADS_FILE, "r", encoding="utf-8") as f:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return json.load(f)
&nbsp; &nbsp; except FileNotFoundError:
&nbsp; &nbsp; &nbsp; &nbsp; return {}
&nbsp; &nbsp; except Exception as e:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[!] Error loading threads: {e}")
&nbsp; &nbsp; &nbsp; &nbsp; return {}
&nbsp;
def save_threads(threads):
&nbsp; &nbsp; try:
&nbsp; &nbsp; &nbsp; &nbsp; with open(THREADS_FILE, "w", encoding="utf-8") as f:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; json.dump(threads, f, ensure_ascii=False, indent=2)
&nbsp; &nbsp; except Exception as e:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[!] Error saving threads: {e}")
&nbsp;
# --- ניקוי חתימות והודעות חוזרות ---
def clean_email_body(body):
&nbsp; &nbsp; patterns_to_remove = [
&nbsp; &nbsp; &nbsp; &nbsp; r"--\s*\n.*",&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;# קו חתימה --
&nbsp; &nbsp; &nbsp; &nbsp; r"Sent from my .*",&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # טקסטים כמו Sent from my iPhone
&nbsp; &nbsp; &nbsp; &nbsp; r"שלח:.*",&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;# שורות של מייל קודם בעברית
&nbsp; &nbsp; &nbsp; &nbsp; r"נשלח:.*",
&nbsp; &nbsp; &nbsp; &nbsp; r"From:.*",
&nbsp; &nbsp; &nbsp; &nbsp; r"To:.*",
&nbsp; &nbsp; &nbsp; &nbsp; r"Cc:.*",
&nbsp; &nbsp; &nbsp; &nbsp; r"Subject:.*",
&nbsp; &nbsp; &nbsp; &nbsp; r"-----Original Message-----",
&nbsp; &nbsp; &nbsp; &nbsp; r"^>+",&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;# ציטוטים מקויים
&nbsp; &nbsp; ]
&nbsp; &nbsp; pattern = "|".join(patterns_to_remove)
&nbsp; &nbsp; body = re.split(pattern, body, flags=re.IGNORECASE | re.MULTILINE)[0]
&nbsp; &nbsp; return body.strip()
&nbsp;
# --- קבלת מיילים חדשים ---
def get_unread_emails():
&nbsp; &nbsp; try:
&nbsp; &nbsp; &nbsp; &nbsp; mail = imaplib.IMAP4_SSL(IMAP_SERVER)
&nbsp; &nbsp; &nbsp; &nbsp; mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
&nbsp; &nbsp; &nbsp; &nbsp; mail.select("inbox")
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; result, data = mail.search(None, "(UNSEEN)")
&nbsp; &nbsp; &nbsp; &nbsp; unread_msg_nums = data[0].split()
&nbsp; &nbsp; &nbsp; &nbsp; messages = []
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; for num in unread_msg_nums:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; result, msg_data = mail.fetch(num, "(RFC822)")
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; raw_email = msg_data[0][1]
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; msg = email.message_from_bytes(raw_email)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; sender = email.utils.parseaddr(msg["From"])[1]
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; subject = msg["Subject"] if msg["Subject"] else "(ללא נושא)"
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; message_id = msg["Message-ID"]
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; in_reply_to = msg.get("In-Reply-To")
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; body = ""
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if msg.is_multipart():
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; for part in msg.walk():
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if part.get_content_type() == "text/plain":
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; charset = part.get_content_charset() or "utf-8"
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; body += part.get_payload(decode=True).decode(charset, errors="ignore")
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; else:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; charset = msg.get_content_charset() or "utf-8"
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; body += msg.get_payload(decode=True).decode(charset, errors="ignore")
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; body = clean_email_body(body)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; messages.append({
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "from": sender,
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "subject": subject,
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "body": body,
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "message_id": message_id,
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "in_reply_to": in_reply_to
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; })
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; mail.logout()
&nbsp; &nbsp; &nbsp; &nbsp; return messages
&nbsp;
&nbsp; &nbsp; except Exception as e:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[!] Error fetching emails: {e}")
&nbsp; &nbsp; &nbsp; &nbsp; return []
&nbsp;
# --- בניית השרשור עבור ג'מיני ---
def build_thread_for_gemini(message, threads):
&nbsp; &nbsp; thread_id = message["in_reply_to"] or message["message_id"]
&nbsp;
&nbsp; &nbsp; if thread_id not in threads:
&nbsp; &nbsp; &nbsp; &nbsp; threads[thread_id] = []
&nbsp;
&nbsp; &nbsp; # הוספת הודעת המשתמש החדשה
&nbsp; &nbsp; threads[thread_id].append({
&nbsp; &nbsp; &nbsp; &nbsp; "from": "user",
&nbsp; &nbsp; &nbsp; &nbsp; "body": message["body"]
&nbsp; &nbsp; })
&nbsp;
&nbsp; &nbsp; # בניית טקסט לג'מיני
&nbsp; &nbsp; gemini_prompt = ""
&nbsp; &nbsp; for msg in threads[thread_id]:
&nbsp; &nbsp; &nbsp; &nbsp; if msg["from"] == "user":
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; gemini_prompt += f"[משתמש כתב]:\n{msg['body']}\n\n"
&nbsp; &nbsp; &nbsp; &nbsp; elif msg["from"] == "gemini":
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; gemini_prompt += f"[ג'מיני כתב]:\n{msg['body']}\n\n"
&nbsp;
&nbsp; &nbsp; return gemini_prompt, thread_id
&nbsp;
# --- שליחת מייל כולל שרשור ---
def send_email(to_email, subject, body_text, original_message_id=None):
&nbsp; &nbsp; try:
&nbsp; &nbsp; &nbsp; &nbsp; formatted_text = markdown.markdown(body_text)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; signature = """
&nbsp; &nbsp; &nbsp; &nbsp; <hr>
&nbsp; &nbsp; &nbsp; &nbsp; <div style="color:#666; font-size:14px; margin-top:10px;">
&nbsp; &nbsp; &nbsp; &nbsp; בינה מלאכותית ג'מיני באימייל נבנה ע"י @טשיקאוור ניוז
&nbsp; &nbsp; &nbsp; &nbsp; </div>
&nbsp; &nbsp; &nbsp; &nbsp; """
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; html_body = f"""
&nbsp; &nbsp; &nbsp; &nbsp; <html>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <body style="direction: rtl; text-align: right; font-family: Arial, sans-serif;">
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {formatted_text}
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {signature}
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; </body>
&nbsp; &nbsp; &nbsp; &nbsp; </html>
&nbsp; &nbsp; &nbsp; &nbsp; """
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; msg = MIMEText(html_body, "html", "utf-8")
&nbsp; &nbsp; &nbsp; &nbsp; msg["From"] = EMAIL_ACCOUNT
&nbsp; &nbsp; &nbsp; &nbsp; msg["To"] = to_email
&nbsp; &nbsp; &nbsp; &nbsp; msg["Subject"] = subject
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; if original_message_id:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; msg["In-Reply-To"] = original_message_id
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; msg["References"] = original_message_id
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; server.sendmail(EMAIL_ACCOUNT, to_email, msg.as_string())
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[✔] Sent reply to {to_email}")
&nbsp;
&nbsp; &nbsp; except Exception as e:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[!] Error sending email: {e}")
&nbsp;
# --- קבלת תגובה מג'מיני ---
def get_gemini_reply(prompt):
&nbsp; &nbsp; try:
&nbsp; &nbsp; &nbsp; &nbsp; url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; headers = {
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "Content-Type": "application/json",
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "X-goog-api-key": GEMINI_API_KEY
&nbsp; &nbsp; &nbsp; &nbsp; }
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; data = {
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "contents": [
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {"parts": [{"text": prompt}]}
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ]
&nbsp; &nbsp; &nbsp; &nbsp; }
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; response = requests.post(url, headers=headers, json=data)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; if response.status_code == 200:
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; result = response.json()
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return result["candidates"][0]["content"]["parts"][0]["text"]
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; print("[!] Gemini API error:", response.text)
&nbsp; &nbsp; &nbsp; &nbsp; return "אירעה שגיאה בעת יצירת התגובה."
&nbsp;
&nbsp; &nbsp; except Exception as e:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[!] Error contacting Gemini API: {e}")
&nbsp; &nbsp; &nbsp; &nbsp; return "שגיאה פנימית בתקשורת עם Gemini."
&nbsp;
# --- הפעלת הבוט ---
def main():
&nbsp; &nbsp; print("Starting Gemini Email Bot...")
&nbsp;
&nbsp; &nbsp; threads = load_threads()
&nbsp; &nbsp; emails = get_unread_emails()
&nbsp;
&nbsp; &nbsp; if not emails:
&nbsp; &nbsp; &nbsp; &nbsp; print("No new emails.")
&nbsp; &nbsp; &nbsp; &nbsp; return
&nbsp;
&nbsp; &nbsp; for msg in emails:
&nbsp; &nbsp; &nbsp; &nbsp; print(f"[📩] New email from {msg['from']}")
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; # --- בניית השרשור המסומן ---
&nbsp; &nbsp; &nbsp; &nbsp; gemini_prompt, thread_id = build_thread_for_gemini(msg, threads)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; # --- שליחת השרשור לג'מיני לקבלת תשובה ---
&nbsp; &nbsp; &nbsp; &nbsp; gemini_reply = get_gemini_reply(gemini_prompt)
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; # --- שמירת תגובת ג'מיני בשרשור ---
&nbsp; &nbsp; &nbsp; &nbsp; threads[thread_id].append({
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "from": "gemini",
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; "body": gemini_reply
&nbsp; &nbsp; &nbsp; &nbsp; })
&nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; # --- שליחת המייל למשתמש ---
&nbsp; &nbsp; &nbsp; &nbsp; send_email(
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; msg["from"],
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; f"Re: {msg['subject']}",
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; gemini_reply,
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; msg["message_id"]
&nbsp; &nbsp; &nbsp; &nbsp; )
&nbsp;
&nbsp; &nbsp; # --- שמירה עדכנית של השרשורים ---
&nbsp; &nbsp; save_threads(threads)
&nbsp;
if __name__ == "__main__":
&nbsp; &nbsp; main()
&nbsp;
