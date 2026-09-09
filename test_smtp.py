import smtplib

sender = "your.mail@gmail.com"
receiver = "target.mail@gmail.com"
password = "your_app_password_here"


try:
    #connect to gmail on port 587
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    
    #login
    server.login(sender, password)
    
    #sending message
    msg = f"Subject: Test SMTP from Laptop\n\nThis is a test email."
    server.sendmail(sender, receiver, msg)
    server.quit()
    print("message sent successfully")
except Exception as e:
    print(f"ERROR: {e}")

