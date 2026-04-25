import smtplib
from email.mime.text import MIMEText
from subprocess import check_output
import time
import subprocess

def check_wifi():
	try:
		output_wifi = subprocess.check_output(["iwgetid"]).decode('utf-8').strip()
		if "SSID" in output_wifi:
			return True
	except subprocess.CalledProcessError:
		return False
        
while not check_wifi():
    time.sleep(10) 
    print("----------------------Wait----------------------")

#get IP
ip_address = check_output(['hostname', '-I']).decode('utf-8').strip()

# setting for sender and receiver
sender_email = "qwe14789kkk@163.com"
receiver_email = "whitefaceprince@gmail.com"
password = "123321kkk"

message = MIMEText('Raspberry Pi IP address is {}'.format(ip_address))
message["Subject"] = "Raspberry Pi IP Address_AHHHHHHHHYOUBASTER"
message["From"] = sender_email
message["To"] = receiver_email

try:
	server = smtplib.SMTP('smtp.163.com',25)
	server.starttls()
	server.login(sender_email,password)
	server.sendmail(sender_email,receiver_email, message.as_string())
	server.quit()
	print("Success")
except Exception as e:
	print('problem', e)
finally:
	if 'server' in locals():
		server.quit()
