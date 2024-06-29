from django.shortcuts import render
from django.http import HttpResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import schedule
import time
from threading import Thread
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def index(request):
    return render(request, 'notifications/front.html')

def process_form(request):
    if request.method == 'POST':
        sheet_link = request.POST.get('sheet_link')
        email_address = request.POST.get('email')
        email_password = request.POST.get('password')
        minutes = int(request.POST.get('minutes'))

        logging.debug(f"Received form data - Sheet link: {sheet_link}, Email: {email_address}, Password: {email_password}, Minutes: {minutes}")

        # Extract the sheet ID from the link
        try:
            sheet_id = sheet_link.split('/d/')[1].split('/')[0]
            logging.debug(f"Extracted sheet ID: {sheet_id}")
        except IndexError as e:
            logging.error(f"Error extracting sheet ID: {e}")
            return HttpResponse("Invalid sheet link format.")

        def check_and_send_notifications():
            try:
                logging.debug("Starting check_and_send_notifications function...")
                # Setup Google Sheets and get data
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_name('E:/python/project/excel-tracker-424816-bbeec2741061.json', scope)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(sheet_id).sheet1

                logging.debug("Google Sheets setup successful")

                data = sheet.get_all_records()
                logging.debug(f"Data from sheet: {data}")

                missing_data_info = check_missing_data(data)
                logging.debug(f"Missing data info: {missing_data_info}")

                for email, missing_columns in missing_data_info:
                    send_email(email, missing_columns, sheet_id, email_address, email_password)
            except Exception as e:
                logging.error(f"Error during notification process: {e}")

        def schedule_task():
            logging.debug(f"Scheduling task to run every {minutes} minutes.")
            schedule.every(minutes).minutes.do(check_and_send_notifications)
            while True:
                schedule.run_pending()
                time.sleep(1)

        # Start the scheduling in a separate thread
        thread = Thread(target=schedule_task)
        thread.daemon = True
        thread.start()

        logging.debug("Scheduling task has started.")
        return HttpResponse("Emails have been sent successfully and scheduling is set.", content_type='text/plain')

    return HttpResponse("Invalid request method.", content_type='text/plain')

def check_missing_data(data):
    missing_data_info = []
    for row in data:
        if None in row.values() or '' in row.values():
            missing_columns = [k for k, v in row.items() if v is None or v == '']
            missing_data_info.append((row['email'], missing_columns))
    return missing_data_info

def send_email(to_address, missing_columns, sheet_id, email_address, email_password):
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = to_address
    msg['Subject'] = 'Missing Data Notification'
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    body = f"Dear User,\n\nYou have missing data in the following columns: {', '.join(missing_columns)}.\nPlease update your information. You can access the Google Sheet here: {sheet_url}\n\nRegards,\nDharanya S"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_address, email_password)
            text = msg.as_string()
            server.sendmail(email_address, to_address, text)
            logging.debug(f"Notification sent to {to_address} for missing columns: {', '.join(missing_columns)}")
    except smtplib.SMTPException as e:
        logging.error(f"Error sending email to {to_address}: {e}")
