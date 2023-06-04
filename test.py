from email.message import EmailMessage
import smtplib

sender = "alex.randles@outlook.com"
recipient = "alex.randles@outlook.com"
message = "Your notification policy has been fulfilled!"

email = EmailMessage()
email["From"] = sender
email["To"] = recipient
email["Subject"] = "Notification Details"
email.set_content(message)

smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
smtp.starttls()
smtp.login(sender, "R7LwqD9rMnERh9Q")
smtp.sendmail(sender, recipient, email.as_string())
smtp.quit()
