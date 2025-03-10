#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import html
import json
import requests
import json, re
from dateutil import parser as dateparser
from time import sleep

# for rotating IPs and proxy services
from lxml.html import fromstring
from itertools import cycle
import traceback

def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            # Grabbing IP and corresponding PORT
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return proxies

def ParseReviews(asin):
  amazon_url  = 'http://www.amazon.com/dp/' + asin

  proxies = get_proxies()
  proxy_pool = cycle(proxies)
  #Get a proxy from the pool
  proxy = next(proxy_pool)

  # Add some recent user agent to prevent amazon from blocking the request
  # Find some chrome user agent strings  here https://udger.com/resources/ua-list/browser-detail?browser=Chrome
  headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19'}

  page = requests.get(amazon_url, headers = headers, verify=False, proxies={"http": proxy, "https": proxy})
  page_response = page.text

  parser = html.fromstring(page_response)
  XPATH_AGGREGATE = '//span[@id="acrCustomerReviewText"]'
  XPATH_REVIEW_SECTION_1 = '//div[contains(@id,"reviews-summary")]'
  XPATH_REVIEW_SECTION_2 = '//div[@data-hook="review"]'
  XPATH_AGGREGATE_RATING = '//table[@id="histogramTable"]//tr'
  XPATH_PRODUCT_NAME = '//h1//span[@id="productTitle"]//text()'
  XPATH_PRODUCT_PRICE  = '//span[@id="priceblock_ourprice"]/text()'

  raw_product_price = parser.xpath(XPATH_PRODUCT_PRICE)
  product_price = ''.join(raw_product_price).replace(',', '')

  raw_product_name = parser.xpath(XPATH_PRODUCT_NAME)
  product_name = ''.join(raw_product_name).strip()
  total_ratings  = parser.xpath(XPATH_AGGREGATE_RATING)
  reviews = parser.xpath(XPATH_REVIEW_SECTION_1)
  if not reviews:
    reviews = parser.xpath(XPATH_REVIEW_SECTION_2)
  ratings_dict = {}
  reviews_list = []

  if not reviews:
    raise ValueError('Unable to find reviews in page')

  # Grabing the rating section in product page
  for ratings in total_ratings:
    extracted_rating = ratings.xpath('./td//a//text()')
    if extracted_rating:
      rating_key = extracted_rating[0]
      raw_raing_value = extracted_rating[1]
      rating_value = raw_raing_value
      if rating_key:
        ratings_dict.update({rating_key:rating_value})

  # Parsing individual reviews
  for review in reviews:
    XPATH_RATING  = './/i[@data-hook="review-star-rating"]//text()'
    XPATH_REVIEW_HEADER = './/a[@data-hook="review-title"]//text()'
    XPATH_REVIEW_POSTED_DATE = './/span[@data-hook="review-date"]//text()'
    XPATH_REVIEW_TEXT_1 = './/div[@data-hook="review-collapsed"]//text()'
    XPATH_REVIEW_TEXT_2 = './/div//span[@data-action="columnbalancing-showfullreview"]/@data-columnbalancing-showfullreview'
    XPATH_REVIEW_COMMENTS = './/span[@data-hook="review-comment"]//text()'
    XPATH_AUTHOR  = './/span[contains(@class,"profile-name")]//text()'
    XPATH_REVIEW_TEXT_3  = './/div[contains(@id,"dpReviews")]/div/text()'

    raw_review_author = review.xpath(XPATH_AUTHOR)
    raw_review_rating = review.xpath(XPATH_RATING)
    raw_review_header = review.xpath(XPATH_REVIEW_HEADER)
    raw_review_posted_date = review.xpath(XPATH_REVIEW_POSTED_DATE)
    raw_review_text1 = review.xpath(XPATH_REVIEW_TEXT_1)
    raw_review_text2 = review.xpath(XPATH_REVIEW_TEXT_2)
    raw_review_text3 = review.xpath(XPATH_REVIEW_TEXT_3)

    # Cleaning data
    author = ' '.join(' '.join(raw_review_author).split())
    review_rating = ''.join(raw_review_rating).replace('out of 5 stars', '')
    review_header = ' '.join(' '.join(raw_review_header).split())

    try:
      review_posted_date = dateparser.parse(''.join(raw_review_posted_date)).strftime('%d %b %Y')
    except:
      review_posted_date = None
    review_text = ' '.join(' '.join(raw_review_text1).split())

    # Fetching hidden comments if present
    if raw_review_text2:
      json_loaded_review_data = json.loads(raw_review_text2[0])
      json_loaded_review_data_text = json_loaded_review_data['rest']
      cleaned_json_loaded_review_data_text = re.sub('<.*?>', '', json_loaded_review_data_text)
      full_review_text = review_text+cleaned_json_loaded_review_data_text
    else:
      full_review_text = review_text
    if not raw_review_text1:
      full_review_text = ' '.join(' '.join(raw_review_text3).split())

    raw_review_comments = review.xpath(XPATH_REVIEW_COMMENTS)
    review_comments = ''.join(raw_review_comments)
    review_comments = re.sub('[A-Za-z]', '', review_comments).strip()
    review_dict = {
              'review_comment_count':review_comments,
              'review_text':full_review_text,
              'review_posted_date':review_posted_date,
              'review_header':review_header,
              'review_rating':review_rating,
              'review_author':author

            }
    reviews_list.append(review_dict)

  data = {
        'ratings':ratings_dict,
        'reviews':reviews_list,
        'url':amazon_url,
        'price':product_price,
        'name':product_name
      }
  return data
  # 	except ValueError:
  # 		print("Retrying to get the correct response")

  # return {"error":"failed to process the page","asin":asin}

def ReadAsin():
  user_input = raw_input("Enter amazon ASIN in one line using commas:\n")
  input_list = user_input.split(',')
  AsinList = [x.strip() for x in input_list]
  extracted_data = []
  for asin in AsinList:
    print("Downloading and processing page http://www.amazon.com/dp/" + asin)
    extracted_data.append(ParseReviews(asin))
    sleep(5)
  f = open('data.json', 'w')
  json.dump(extracted_data, f, indent=4)

if __name__ == '__main__':
  ReadAsin()
