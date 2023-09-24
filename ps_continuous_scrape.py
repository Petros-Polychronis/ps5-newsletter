import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from lxml import etree
import numpy as np
import time
import datetime
from scrape_functions import build_game_url, check_grid, check_edition, get_console_edition


# PTI

# 1.a: Load dictionary called game_titles
with open("/home/ec2-user/ps5-newsletter/game_titles.json", "r") as outfile:
    game_titles = json.load(outfile)

# 1.b: Load dataframe called games
games = pd.read_csv('/home/ec2-user/ps5-newsletter/games.csv', index_col = 0)

# needed once
if "needs_scrape" not in games.columns:
    games['needs_scrape'] = 0


# 2.a Find new games
new_games = list(set(game_titles['game_titles']) - set(games['game_name']))
new_games_dict = {"game_name": new_games,
                  "needs_scrape": [1]*len(new_games)}

# 2.b Append new games to dataframe 
games = pd.concat([games, pd.DataFrame(new_games_dict)]).reset_index().drop(columns = ['index'])


# 3.a run test on which of the scraped links might need re-scraping
for game in games[games['needs_scrape']==0]['game_name']:
    
    grid_check = check_grid(game_link = games[games['game_name']==game]['game_links'].values[0])

    if grid_check==-1:
        games.loc[games['game_name']==game, 'needs_scrape']= 1


# 3.b scrape links again for all games with needs_scrape=1

for game in games[games['needs_scrape']==1]['game_name']:

    game_url, release_date, genre = build_game_url(game)
    games.loc[games['game_name']==game, 'game_links'] = game_url
    games.loc[games['game_name']==game, 'release_date'] = release_date
    games.loc[games['game_name']==game, 'genre'] = genre
    games.loc[games['game_name']==game, 'needs_scrape'] = 0


# 3.c check which link needs to be re-scraped another time.
games.loc[games['game_links'].isin([np.nan, 'not_found']), 'needs_scrape'] = 1

# 4. update games.csv
games.to_csv("/home/ec2-user/ps5-newsletter/games.csv")


# new dataframe for new scrapes
new_game_prices = pd.DataFrame()

print("PTI is complete, moving on to scraping prices from valid links")


## PT II

today = pd.Timestamp(datetime.date.today())

game_links = games[games['needs_scrape']==0]['game_links']

for url in game_links:
    
    game_dict = {}
    game_dict[url] = {} 

    # theoretically all links scraped have been cheched in advance, edition_grid should exist for all
    edition_grid = check_grid(game_link = url)
    edition_num = len(edition_grid)

    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    dom = etree.HTML(str(soup))

    # iterate over editions:
    for i in range(edition_num):
        
        # check if the neccessary parts exists, else skip!
        game_edition, game_pic, final_price = check_edition(i, dom)

        if game_edition!=-1:

            #original_price
            original_price_path = "//span[@data-qa='mfeUpsell#productEdition" + str(i) + "#ctaWithPrice#offer0#originalPrice']/text()"
            original_price = dom.xpath(original_price_path)
            
            if len(original_price)==0:
                sale=0
                game_dict[url][str(i)] = {
                    'game_edition':[game_edition],
                    'sale':[sale],
                    'game_pic': [game_pic],
                    'final_price':[final_price],
                    'game_links':[url]
                }

            elif len(original_price)==1:
                sale = 1
                original_price = original_price[0]

                #save in percentage
                save_amount_text_path = "//span[@data-qa='mfeUpsell#productEdition" + str(i) + "#ctaWithPrice#offer0#discountInfo']/text()"
                save_amount_text = dom.xpath(save_amount_text_path)[0]

                # offer ends date
                offer_ends_path =  "//span[@data-qa='mfeUpsell#productEdition" + str(i) + "#ctaWithPrice#offer0#discountDescriptor']/text()"
                offer_ends = dom.xpath(offer_ends_path)[0]


                game_dict[url][str(i)] = {
                'game_edition':[game_edition],   # giving them as list of 1 item to aid dataframe row construction
                'sale':[sale],
                'game_pic':[game_pic],
                'final_price':[final_price],
                'original_price':[original_price],
                'save_text':[save_amount_text],
                'offer_ends':[offer_ends],
                'game_links':[url]
            }


            game_dict[url][str(i)]['console_edition']= [get_console_edition(i, dom)]
        
    for edition in game_dict[url].keys():
        # add scrape date
        new_row = pd.DataFrame(game_dict[url][edition])
        new_row['date'] = today
        new_game_prices = pd.concat([new_game_prices, new_row])



new_game_prices = new_game_prices.reset_index().drop(columns=['index'])
new_game_prices = new_game_prices.merge(games[['game_links', 'game_name']], on='game_links', how='left')

print("PTII is complete, prices are saved in new_game_prices dataframe")


##PTIII: Combine with existing 
game_prices = pd.read_csv('/home/ec2-user/ps5-newsletter/game_prices.csv', index_col=0)
game_prices = pd.concat([game_prices, new_game_prices]).reset_index().drop(columns = ['index'])
game_prices.to_csv('/home/ec2-user/ps5-newsletter/game_prices_online.csv')

print("PTIII is complete, prices have been merged.")