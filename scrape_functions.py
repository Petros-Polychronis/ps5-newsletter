import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from lxml import etree
import numpy as np
import time
import datetime





def build_game_url(game_title):

    # build search url
    search_url = 'https://store.playstation.com/en-gr/search/' + game_title.replace(" ", "%20")

    webpage = requests.get(search_url)


    # parse requested page.
    soup = BeautifulSoup(webpage.content, "html.parser")
    dom = etree.HTML(str(soup))

    # current idea: try the first links one by one, until you find a link with an edition grid

    i=0
    found = 0
    while (i<5) & (found==0):
        game_link_path = "//div[@data-qa='search#productTile" + str(i) + "']//a/@href"
        game_link = dom.xpath(game_link_path)[0]

        game_link = 'https://store.playstation.com/' + game_link

        # get game dom
        request = requests.get(game_link)
        soup_game = BeautifulSoup(request.content, "html.parser")
        dom_game = etree.HTML(str(soup_game))

        grid_check  = check_grid(dom=dom_game)

        if grid_check!=-1:
            found=1
            release_date = dom_game.xpath('//dd[@data-qa="gameInfo#releaseInformation#releaseDate-value"]')[0].text
            genre = dom_game.xpath('//dd[@data-qa="gameInfo#releaseInformation#genre-value"]//span')[0].text

        else:
            i+=1
    
    # create the full game link.

    if found==0:
        game_link = 'not_found'
        release_date='no_link'
        genre = 'no_link'

    return (game_link, release_date, genre)



def check_grid(game_link=None, dom=None):
    """
    This function tests whether the game link contains a grid with editions. If not, the link is probably wrong, i.e., the first search result is not the game.
    """
    if (game_link is None) & (dom is None):
        raise ValueError('You haven\'t passed any of the neccessary arguments, neither a game_link nor a dom')

    if game_link is None:
        edition_grid = dom.xpath('//div[@class="psw-l-grid"]//article')
        if edition_grid:
            return edition_grid
        else:
            edition_grid = -1
            return edition_grid
    else:
        page = requests.get(game_link)
        soup = BeautifulSoup(page.content, 'html.parser')
        dom = etree.HTML(str(soup))

        edition_grid = dom.xpath('//div[@class="psw-l-grid"]//article')
        if edition_grid:
            return edition_grid
        else:
            edition_grid = -1
            return edition_grid
        


def check_edition(edition, dom):

    s = 0
    # game edition
    game_edition_path = "//h3[@data-qa='mfeUpsell#productEdition" + str(edition) +"#editionName']/text()"
    game_edition_list = dom.xpath(game_edition_path)

    if game_edition_list:
        s+=1
        game_edition = game_edition_list[0]

    # game pics (two pics links should be found, first is thumbnail, second is full pic)
    game_pic_path = "//span[@data-qa='mfeUpsell#productEdition" + str(edition) + "#media']//img/@src"
    game_pic_list = dom.xpath(game_pic_path)

    if len(game_pic_list)>=2:
        s+=1
        game_pic = game_pic_list[1]


    #final price -> if there is only final price, there is no discount!
    final_price_path = "//span[@data-qa='mfeUpsell#productEdition" + str(edition) + "#ctaWithPrice#offer0#finalPrice']"
    final_price_list = dom.xpath(final_price_path)

    if final_price_list:
        final_price = final_price_list[0].text
        try:
            price_test =float(final_price.replace("€","").strip())
            s+=1
        except:
            None
    
    if s==3:
        return (game_edition, game_pic, final_price)
    else:
        return (-1, -1, -1)
    


def get_console_edition(edition, dom):


    # console edition
    # need to check whether it normally exists!
    # need to check whether it includes ps5-ps4 on the same edition (need to add it)
    
    console_edition_path_1  = "//span[@data-qa='mfeUpsell#productEdition" +  str(edition) + "#productTag0']/text()"
    console_edition_path_2  = "//span[@data-qa='mfeUpsell#productEdition" +  str(edition) + "#productTag1']/text()"

    console_edition_1 = dom.xpath(console_edition_path_1)
    console_edition_2 = dom.xpath(console_edition_path_2)

    if (console_edition_1):
        if (console_edition_2):
            console_edition = console_edition_1[0] + '-' + console_edition_2[0]
        else:
            console_edition = console_edition_1[0]
    else:
        return '-'
        
    return console_edition
                