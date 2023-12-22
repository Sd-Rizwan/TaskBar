import smtplib
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('sd.rizwan724@gmail.com','scql bdxs nnsg hdok')
    msg=EmailMessage()
    msg['From']='sd.rizwan724@gmail.com'
    msg['Subject']=subject
    msg['to']=to
    msg.set_content(body)
    server.send_message(msg)
    server.quit()
