import urllib2, json, re, smtplib, datetime, sched, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup, element
from datetime import datetime as dt

# Get the hackernews who is hiring page for the month
def get_hackernews_page(id = ""):
	# If we don't specify the id of the page, we have to parse through the titles of the top pages
	# on the website right now
	if len(id) == 0:
		# Get the recent ask posts
		ids = "https://hacker-news.firebaseio.com/v0/askstories.json?print=pretty"
		response = urllib2.urlopen(ids)
		data = json.loads(response.read())
		for id in data:
			url = "https://news.ycombinator.com/item?id=" + str(id)
			soup = getSoup(url)
			title = soup.title.text
			# If post is a who is hiring thread, return the soup
			if u"Ask HN: Who is hiring?" in title:
				return soup
	# Otherwise we can just connect to the page given and check if it is correct
	else:
		url = "https://news.ycombinator.com/item?id=" + id
		soup = getSoup(url)
		title = soup.title.text
		if u"Ask HN: Who is hiring?" in title:
			return soup
		return None

# Get the beautiful soup from a url
def getSoup(url):
	request = urllib2.Request(url)
	request.add_header('Accept-Encoding', 'utf-8')
	response = urllib2.urlopen(request)
	soup = BeautifulSoup(response.read().decode('utf-8', 'ignore'), "html5lib")
	return soup

# Parse the beautiful soup to get the relevant intern postings
def get_hackernews_listings(soup):
	intern_listings = []
	tr_tags = soup.findAll("tr")
	for tr in tr_tags:
		td = tr.find("td")
		if td:
			img = td.find("img")
			if img and str(img.get('width')) == str(0):
				comment = tr.find("td", {"class":"default"})
				if comment:
					comment = comment.find("div", {"class":"comment"})
					if comment:
						comment = comment.find("span", {"class":"c00"})
						if comment and type(comment.contents[0]) is element.NavigableString:
							comment_header = comment.contents[0].strip()
							comment_body = comment.text.replace(comment_header, "").replace("reply", "").strip()
							id = tr.parent.parent.parent.parent.get('id')
							if id and not "https://whoishiring.io" in comment_body:
								# Use regex to search for main comments regarding interns in their header
								intern_search = re.search( r'(|\W)intern(\W|((s|ship(s|))(\W|$)))', comment_header, re.I)
								# If it is an intern posting, add it to the list
								if intern_search:
									header_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', comment_header)
									body_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', comment_body)
									intern_listings.append((comment_header, header_urls, body_urls))
	return intern_listings

# Create the body of the message (a plain-text and an HTML version).
def create_email_content(listings, month_name):
	text = "Intern listings for " + month_name + "\n\n"
	html = "<html><head></head><body style=\"color:black;\"><p>Hackernews intern listings for " + month_name + "</p>"
	for listing in listings:
		html = html + "<p>"
		for i in range(0,3):
			if i == 0:
				text = text + listing[i].encode('utf-8') + "\n"
				html = html + "<br>".join(listing[i].encode('utf-8').split("\n")) + "<br>"
			elif not len(listing[i]) == 0:
				for url in listing[i]:
					if not url in listing[0]:
						text = text + url.encode('utf-8') + ", "
						html = html + url.encode('utf-8') + ", "
		html = html[:-2] + "</p>"
		text = text[:-2] + "\n"
	html = html + "</body></html>"
	return (text, html)

# Send the email with the intern listings to the emails requested
def send_email(email_content, month_name):
	SERVER = "smtp.gmail.com"

	# This will be your gmail password where the email is coming from
	EMAIL_PASSWORD = "password"

	# You will have to create your own email here
	from_addr = "test@gmail.com"

	# Login to the gmail server
	server = smtplib.SMTP(SERVER, 587)
	server.starttls()
	server.login(from_addr, EMAIL_PASSWORD)

	# Who you want to send the email to
	to_addrs = ["test@gmail.com"]
	
	# Format the email
	msg = MIMEMultipart('alternative')
	part1 = MIMEText(email_content[0], 'plain')
	part2 = MIMEText(email_content[1], 'html')
	msg.attach(part1)
	msg.attach(part2)

	# Set the subject
	msg['Subject'] = month_name + " Intern Listings"
	msg['From'] = from_addr
	
	print("sending emails")

	# Send the email to each of the emails
	for to_addr in to_addr:
		msg['To'] = to_addr
		server.sendmail(from_addr, to_addr, msg.as_string())
	server.quit()
	print("emails delivered")

# Get the first monday of the next month
def find_first_monday():
	now = datetime.datetime.now()
	year = now.year
	month = now.month
	day = now.day
	today = datetime.date(year, month, day)
	next_month = today.replace(day=28) + datetime.timedelta(days=4)
	last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
	days_ahead = 0 - last_day_of_month.weekday() # 0 -> Monday
	if days_ahead <= 0: # Target day already happened this week
		days_ahead += 7
	return last_day_of_month + datetime.timedelta(days_ahead)

# Return the string representation of the current time
def now_str():
    t = dt.now().time()
    return t.strftime("%H:%M:%S")

def main():
	def send_intern_email():
		print('RUNNING:', now_str())

		# Get the current month
		now = datetime.datetime.now()
		month_name = now.strftime("%B")

		# Get the latest who is hiring thread
		hackernews_soup = get_hackernews_page()

		# Get the intern listings from the page
		hackernews_listings = get_hackernews_listings(hackernews_soup)

		# Format the listing for an email
		emailContent = create_email_content(hackernews_listings, month)

		# send the email
		send_email(emailContent, month)

		# Schedule the next time to run the script (first tuesday of every month)
		first_monday = find_first_monday()
		run_script_day = first_monday + datetime.timedelta(days=1)
		scheduler.enterabs(time.mktime(run_script_day.timetuple()), 1, send_intern_email, ('Running again',))

	# Build a scheduler object that will look at absolute times
	scheduler = sched.scheduler(time.time, time.sleep)
	print('START:', now_str())

    # Get the first day to run the script
	first_monday = find_first_monday()
	run_script_day = first_monday + datetime.timedelta(days=1)

	# Run the script initially
	scheduler.enterabs(time.mktime(run_script_day.timetuple()), 1, send_intern_email, ('Run the first time',))
	scheduler.run()

if __name__ == '__main__':
    main()