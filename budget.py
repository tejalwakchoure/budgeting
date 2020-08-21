from __future__ import print_function
import pickle, base64, email, re
import os.path
from decimal import *
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests 
from bs4 import BeautifulSoup
import calendar
import datetime 
from datetime import date

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TWOPLACES = Decimal(10) ** -2

def get_expenses():
	"""Shows basic usage of the Gmail API.
	Lists the user's Gmail labels.
	"""
	creds = None
	# The file token.pickle stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	service = build('gmail', 'v1', credentials=creds)
	curr_month = date.today().strftime("%m")
	months = [m for m in range(1,13) if m>=1 and m<=int(curr_month)]
	spent_inr = dict()
	spent_usd = dict()
	cnt_expenses = 0
	
	# Call the Gmail API
	for m in months:
		spent_inr[m] = 0
		spent_usd[m] = 0
		after_date = str(m).zfill(2)+"/01/2019"
		if m<int(curr_month):
			before_date = str(m+1).zfill(2)+"/01/2019"
		else:
			before_date = (date.today() + datetime.timedelta(days=1)).strftime("%m/%d/%Y")

		# Customize the subject parameter according to your transaction alerts format
		response = service.users().messages().list(userId="me", labelIds="INBOX", 
			q='subject: Transaction Alert after: {0} before: {1}'.format(after_date, before_date)).execute()
		msg_list = []
		if 'messages' in response:
			msg_list.extend(response['messages'])
		for msg in msg_list:
			message = service.users().messages().get(userId="me", id=msg['id'], format='full').execute()
			payload = message['payload']['parts'][0]
			final_text = base64.urlsafe_b64decode(payload['body']['data']).decode("utf-8")
			substr = re.search('Amount :INR(.+?)Date :', final_text).group(1)
			spent_inr[m] = spent_inr[m] + Decimal(substr.strip().replace(",",""))
			cnt_expenses = cnt_expenses + 1

		# Customize the subject parameter according to your transaction alerts format
		response = service.users().messages().list(userId="me", labelIds="INBOX", 
			q='subject: Transaction Success Alert after: {0} before: {1}'.format(after_date, before_date)).execute()
		msg_list = []
		if 'messages' in response:
			msg_list.extend(response['messages'])
		for msg in msg_list:
			message = service.users().messages().get(userId="me", id=msg['id'], format='full').execute()
			payload = message['payload']
			final_text = base64.urlsafe_b64decode(payload['body']['data']).decode("utf-8")
			substr = re.search('USD(.+?)at ', final_text).group(1)
			spent_usd[m] = spent_usd[m] + Decimal(substr.strip().replace(",",""))
			cnt_expenses = cnt_expenses + 1

	return spent_inr, spent_usd, cnt_expenses, months

def convert_expenses(spent_inr):
	"""
	Get current INR to USD rate
	"""
	URL = "https://www.google.com/search?q=inr+to+usd"
	r = requests.get(URL) 
	soup = BeautifulSoup(r.content, 'html.parser') 

	conversion_rate = 0
	converted_expenses = 0

	for p in soup.select('div'):
		substr = re.search('Conversion / Currency(.+?) United States Dollar1 Indian RupeeDisclaimer', p.text)
		if substr is not None:
			conversion_rate = Decimal(substr.group(1).strip().replace(",",""))
			break

	converted_expenses = spent_inr * conversion_rate
	converted_expenses = converted_expenses.quantize(TWOPLACES)
	return converted_expenses, conversion_rate

def main():
	spent_inr, spent_usd, count_expenses, months = get_expenses()
	total_expenses_all_mths = 0
	curr_month = int(date.today().strftime("%m"))
	for m in months:
		converted_usd, conversion_rate = convert_expenses(spent_inr[m])
		total_expenses_in_usd = spent_usd[m] + converted_usd
		total_expenses_all_mths = total_expenses_all_mths + total_expenses_in_usd
		
		print("Month: "+calendar.month_name[m])
		# print("Expenses in INR:", spent_inr)
		# print("Expenses in USD:", spent_usd)
		# print("Current conversion rate from INR to USD:", conversion_rate)
		if m==curr_month:
			print("Total expenses in USD so far (date= "+date.today().strftime("%b %d")+"):", total_expenses_in_usd)
		else:
			print("Total expenses in USD:", total_expenses_in_usd)
		print()

	#print("Total number of expenses:", count_expenses)
	print("Total expenses in USD till now:", total_expenses_all_mths)
	print()


if __name__ == '__main__':
	main()
