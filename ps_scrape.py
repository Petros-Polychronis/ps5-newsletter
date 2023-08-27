#!/bin/usr/env python

## IMPORT LIBRARIES
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from lxml import etree
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os


# READ EMAILS AND TRACKED PS STORE PRODUCTS

## Note: file json file named "recipients_requests.json" must exist in the same folder as the script.
with open('/home/ec2-user/ps5-newsletter/recipients_requests.json') as json_file:
    recipients_requests = json.load(json_file)

# SCRAPING
## Loops over all users and all links, scrapes the relevant information (product name on PS Store, original price, final price, whether the product is on sale, sale duration,  and the product pic)

users = dict()

for user in recipients_requests.keys():

    data = dict()
    for url in recipients_requests[user]:
        print(url)

        #Headers missing
        webpage = requests.get(url)
        soup = BeautifulSoup(webpage.content, "html.parser")
        dom = etree.HTML(str(soup))

        sale = 1
        game_title = dom.xpath('//h1[@data-qa="mfe-game-title#name"]')[0].text
        original_price = dom.xpath("//span[@class='psw-l-line-left psw-l-line-wrap']//span[@data-qa='mfeCtaMain#offer0#originalPrice']/text()")
        final_price = dom.xpath("//span[@class='psw-l-line-left psw-l-line-wrap']//span[@data-qa='mfeCtaMain#offer0#finalPrice']")[0].text
        #OR
        # final_price  = dom.xpath("//span[@class='psw-l-line-left psw-l-line-wrap']//span[@data-qa='mfeCtaMain#offer0#finalPrice']/text()")[0]
        

        if len(original_price)==0:
            sale=0
            data[url] = {
                        'game_title':game_title, 
                        'final_price':final_price, 
                        'sale': sale
                        }
        else:
            sale=1
            #original price
            original_price = original_price[0]

            #potential path for pics:
            pic_links = dom.xpath("//div[@data-qa='gameBackgroundImage']//span//img/@src")
            if len(pic_links)==2:
                pic_link = pic_links[1]
            elif len(pic_links)==1:
                pic_link = pic_links[0]
            else:
                pic_link ="No Image Found"

            #potential path for sale duration:
            sale_duration = dom.xpath("//span[@data-qa='mfeCtaMain#offer0#discountDescriptor']")[0].text
            
            data[url] ={'game_title':game_title, 
                        'final_price':final_price, 
                        'sale': sale,
                        'pic_link':pic_link, 
                        'sale_duration':sale_duration, 
                        'original_price':original_price}
            
        users[user] = data

# SAVE SCRAPED INFO IN OUTPUT FILE
with open("/home/ec2-user/ps5-newsletter/output.json", "w") as outfile:
    json.dump(users, outfile)


# SENDING EMAILS

## PT1 OPEN TEMPLATE
template = open('/home/ec2-user/ps5-newsletter/email.html')
soup = BeautifulSoup(template.read(), "html.parser")
game_temp = soup.find_all('tr')[6]

html_start = str(soup)[:str(soup).find(str(game_temp))]
html_end = str(soup)[str(soup).find(str(game_temp))+len(str(game_temp)):]
html_start = html_start.replace('\n','')
html_end = html_end.replace('\n','')


### PTII: Building the newsletter content

email_contents = dict()

for user in recipients_requests.keys():

#### Build newsletter content
    newsletter_content = ""

    for game in recipients_requests[user]:
        
        if users[user][game]['sale'] ==1:
            game_temp.img['src'] = data[game]['pic_link']
            game_temp.find('a').string.replaceWith(data[game]['game_title'])
            game_temp.find('a')['href'] = game
            game_temp.p = data[game]['sale_duration']
            game_temp.find('span').string.replaceWith(data[game]['final_price'])

            newsletter_content+= str(game_temp).replace('\n', '')

    email_contents[user] = html_start + newsletter_content + html_end


### PTIII SEND EMAILS


sender_email = "petros.newsletter@gmail.com"
#comment out load_dotenv() for the cloud version. Theoretically, I will have set up the pass as environment variable, so just the code below should be able to fetch it?
#load_dotenv()
password = os.environ['email_pass']  # do not change, this is a specific gapps password



# Create secure connection with server and send email
context = ssl.create_default_context()

with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.ehlo()
    server.login(sender_email, password)

    for user in email_contents.keys():
        receiver_email = user

        message = MIMEMultipart("alternative")
        message["Subject"] = "PS5 sales newsletter by Petros"
        message["From"] = sender_email
        message["To"] = receiver_email

        # Create the plain-text and HTML version of your message
        #text = "Hi, I've found some article that you might find interesting: %s" % previews
        html = email_contents[user]

        # Turn these into plain/html MIMEText objects
        #part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")


        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        #message.attach(part1)
        message.attach(part2)

        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
