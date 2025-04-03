import os
import sys
import pandas as pd
from progress import Progress
from scroller import Scroller
from tweet import Tweet
from ipfs_screenshot import screenshot_and_pin

from datetime import datetime
from fake_headers import Headers
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# NEW: Import AI analysis tool for tweet deletion likelihood evaluation
from ai_analysis import analyze_tweet

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"

class Twitter_Scraper:
    def __init__(self, mail, username, password, headlessState, max_tweets=50,
                 scrape_username=None, scrape_hashtag=None, scrape_query=None,
                 scrape_bookmarks=False, scrape_poster_details=False,
                 scrape_latest=True, scrape_top=False, proxy=None):
        print("Initializing Twitter Scraper...")
        logging.info("Initializing Twitter Scraper...")
        self.mail = mail
        self.username = username
        self.password = password
        self.headlessState = headlessState
        self.interrupted = False
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.scraper_details = {
            "type": None,
            "username": None,
            "hashtag": None,
            "bookmarks": False,
            "query": None,
            "tab": None,
            "poster_details": False,
        }
        self.max_tweets = max_tweets
        self.progress = Progress(0, max_tweets)
        self.router = self.go_to_home
        self.driver = self._get_driver(proxy)
        self.actions = ActionChains(self.driver)
        self.scroller = Scroller(self.driver)
        self._config_scraper(max_tweets, scrape_username, scrape_hashtag, scrape_bookmarks,
                             scrape_query, scrape_latest, scrape_top, scrape_poster_details)

    def _config_scraper(self, max_tweets=50, scrape_username=None, scrape_hashtag=None,
                        scrape_bookmarks=False, scrape_query=None, scrape_latest=True,
                        scrape_top=False, scrape_poster_details=False):
        logging.info("Configuring scraper parameters...")
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.max_tweets = max_tweets
        self.progress = Progress(0, max_tweets)
        self.scraper_details = {
            "type": None,
            "username": scrape_username,
            "hashtag": str(scrape_hashtag).replace("#", "") if scrape_hashtag is not None else None,
            "bookmarks": scrape_bookmarks,
            "query": scrape_query,
            "tab": "Latest" if scrape_latest else "Top" if scrape_top else "Latest",
            "poster_details": scrape_poster_details,
        }
        self.router = self.go_to_home
        self.scroller = Scroller(self.driver)
        if scrape_username is not None:
            self.scraper_details["type"] = "Username"
            self.router = self.go_to_profile
        elif scrape_hashtag is not None:
            self.scraper_details["type"] = "Hashtag"
            self.router = self.go_to_hashtag
        elif scrape_bookmarks is not False:
            self.scraper_details["type"] = "Bookmarks"
            self.router = self.go_to_bookmarks
        elif scrape_query is not None:
            self.scraper_details["type"] = "Query"
            self.router = self.go_to_search
        else:
            self.scraper_details["type"] = "Home"
            self.router = self.go_to_home
        logging.info(f"Scraper configuration: {self.scraper_details}")

    def _get_driver(self, proxy=None):
        logging.info("Setting up WebDriver...")
        header = "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.87 Mobile Safari/537.36"
        browser_option = FirefoxOptions()
        browser_option.add_argument("--no-sandbox")
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument("--ignore-certificate-errors")
        browser_option.add_argument("--disable-gpu")
        browser_option.add_argument("--disable-notifications")
        browser_option.add_argument("--disable-popup-blocking")
        browser_option.add_argument("--user-agent={}".format(header))
        if proxy is not None:
            browser_option.add_argument("--proxy-server=%s" % proxy)
        if self.headlessState == 'yes':
            browser_option.add_argument("--headless")
        try:
            print("Initializing FirefoxDriver...")
            logging.info("Initializing FirefoxDriver...")
            driver = webdriver.Firefox(options=browser_option)
            print("WebDriver Setup Complete")
            logging.info("WebDriver Setup Complete")
            return driver
        except WebDriverException:
            try:
                logging.info("Downloading FirefoxDriver...")
                firefoxdriver_path = GeckoDriverManager().install()
                firefox_service = FirefoxService(executable_path=firefoxdriver_path)
                logging.info("Initializing FirefoxDriver with downloaded driver...")
                driver = webdriver.Firefox(service=firefox_service, options=browser_option)
                print("WebDriver Setup Complete")
                logging.info("WebDriver Setup Complete")
                return driver
            except Exception as e:
                print(f"Error setting up WebDriver: {e}")
                logging.error(f"Error setting up WebDriver: {e}")
                sys.exit(1)

    def login(self):
        print("Logging in to Twitter...")
        logging.info("Logging in to Twitter...")
        try:
            self.driver.maximize_window()
            self.driver.execute_script("document.body.style.zoom='150%'")
            self.driver.get(TWITTER_LOGIN_URL)
            sleep(3)
            self._input_username()
            self._input_unusual_activity()
            self._input_password()
            cookies = self.driver.get_cookies()
            auth_token = None
            for cookie in cookies:
                if cookie["name"] == "auth_token":
                    auth_token = cookie["value"]
                    break
            if auth_token is None:
                raise ValueError("Login failed: unstable connection, incorrect username, or incorrect password.")
            print("Login Successful")
            logging.info("Login Successful")
        except Exception as e:
            print(f"Login Failed: {e}")
            logging.error(f"Login Failed: {e}")
            sys.exit(1)

    def _input_username(self):
        input_attempt = 0
        while True:
            try:
                username = self.driver.find_element("xpath", "//input[@autocomplete='username']")
                username.send_keys(self.username)
                username.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    print("Error inputting username after multiple attempts.")
                    logging.error("Error inputting username.")
                    self.driver.quit()
                    sys.exit(1)
                else:
                    sleep(2)

    def _input_unusual_activity(self):
        input_attempt = 0
        while True:
            try:
                unusual_activity = self.driver.find_element("xpath", "//input[@data-testid='ocfEnterTextTextInput']")
                unusual_activity.send_keys(self.username)
                unusual_activity.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    break

    def _input_password(self):
        input_attempt = 0
        while True:
            try:
                password = self.driver.find_element("xpath", "//input[@autocomplete='current-password']")
                password.send_keys(self.password)
                password.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    print("Error inputting password after multiple attempts.")
                    logging.error("Error inputting password.")
                    self.driver.quit()
                    sys.exit(1)
                else:
                    sleep(2)

    def go_to_home(self):
        self.driver.get("https://twitter.com/home")
        sleep(3)

    def go_to_profile(self):
        if not self.scraper_details["username"]:
            print("Username is not set.")
            logging.error("Username is not set.")
            sys.exit(1)
        else:
            self.driver.get(f"https://twitter.com/{self.scraper_details['username']}")
            sleep(3)

    def go_to_hashtag(self):
        if not self.scraper_details["hashtag"]:
            print("Hashtag is not set.")
            logging.error("Hashtag is not set.")
            sys.exit(1)
        else:
            url = f"https://twitter.com/hashtag/{self.scraper_details['hashtag']}?src=hashtag_click"
            if self.scraper_details["tab"] == "Latest":
                url += "&f=live"
            self.driver.get(url)
            sleep(3)

    def go_to_bookmarks(self):
        if not self.scraper_details["bookmarks"]:
            print("Bookmarks is not set.")
            logging.error("Bookmarks is not set.")
            sys.exit(1)
        else:
            url = f"https://twitter..com/i/bookmarks"
            self.driver.get(url)
            sleep(3)

    def go_to_search(self):
        if not self.scraper_details["query"]:
            print("Query is not set.")
            logging.error("Query is not set.")
            sys.exit(1)
        else:
            url = f"https://twitter.com/search?q={self.scraper_details['query']}&src=typed_query"
            if self.scraper_details["tab"] == "Latest":
                url += "&f=live"
            self.driver.get(url)
            sleep(3)

    def get_tweet_cards(self):
        self.tweet_cards = self.driver.find_elements("xpath", '//article[@data-testid="tweet" and not(@disabled)]')

    def remove_hidden_cards(self):
        try:
            hidden_cards = self.driver.find_elements("xpath", '//article[@data-testid="tweet" and @disabled]')
            for card in hidden_cards[1:-2]:
                self.driver.execute_script("arguments[0].parentNode.parentNode.parentNode.remove();", card)
        except Exception:
            return

    def scrape_tweets(self, max_tweets=50, no_tweets_limit=False, scrape_username=None,
                      scrape_hashtag=None, scrape_bookmarks=False, scrape_query=None,
                      scrape_latest=True, scrape_top=False, scrape_poster_details=False, router=None):
        logging.info("Starting tweet scraping process...")
        self._config_scraper(max_tweets, scrape_username, scrape_hashtag, scrape_bookmarks,
                             scrape_query, scrape_latest, scrape_top, scrape_poster_details)
        if router is None:
            router = self.router
        router()
        if self.scraper_details["type"] == "Username":
            print(f"Scraping Tweets from @{self.scraper_details['username']}...")
        elif self.scraper_details["type"] == "Hashtag":
            print(f"Scraping {self.scraper_details['tab']} Tweets from #{self.scraper_details['hashtag']}...")
        elif self.scraper_details["type"] == "Bookmarks":
            print("Scraping Tweets from bookmarks...")
        elif self.scraper_details["type"] == "Query":
            print(f"Scraping {self.scraper_details['tab']} Tweets from {self.scraper_details['query']} search...")
        elif self.scraper_details["type"] == "Home":
            print("Scraping Tweets from Home...")

        try:
            accept_cookies_btn = self.driver.find_element("xpath", "//span[text()='Refuse non-essential cookies']/../../..")
            accept_cookies_btn.click()
        except NoSuchElementException:
            pass

        self.progress.print_progress(0, False, 0, no_tweets_limit)
        refresh_count = 0
        added_tweets = 0
        empty_count = 0
        retry_cnt = 0
        while self.scroller.scrolling:
            try:
                self.get_tweet_cards()
                added_tweets = 0
                for card in self.tweet_cards[-15:]:
                    try:
                        tweet_id = str(card)
                        if tweet_id not in self.tweet_ids:
                            self.tweet_ids.add(tweet_id)
                            if not self.scraper_details["poster_details"]:
                                self.driver.execute_script("arguments[0].scrollIntoView();", card)
                            tweet = Tweet(card=card, driver=self.driver, actions=self.actions,
                                          scrape_poster_details=self.scraper_details["poster_details"])
                            if tweet and not tweet.error and tweet.tweet is not None and not tweet.is_ad:
                                try:
                                    # Capture the screenshot and build the hosted URL.
                                    ipfs_hash = screenshot_and_pin(card)
                                    ipfs_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"
                                    print(f"Tweet screenshot pinned to IPFS: {ipfs_url}")
                                except Exception as e:
                                    print(f"Error pinning tweet screenshot: {e}")
                                    ipfs_url = ""
                                # Append the hosted IPFS URL as the last element.
                                tweet_data = list(tweet.tweet)
                                tweet_data.append(ipfs_url)
                                self.data.append(tuple(tweet_data))
                                added_tweets += 1
                                print(f"Tweet scraped: {tweet.tweet}")
                                self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)
                                if len(self.data) >= self.max_tweets and not no_tweets_limit:
                                    self.scroller.scrolling = False
                                    break
                    except NoSuchElementException:
                        continue
                if len(self.data) >= self.max_tweets and not no_tweets_limit:
                    break
                if added_tweets == 0:
                    try:
                        while retry_cnt < 15:
                            retry_button = self.driver.find_element("xpath", "//span[text()='Retry']/../../..")
                            self.progress.print_progress(len(self.data), True, retry_cnt, no_tweets_limit)
                            sleep(600)
                            retry_button.click()
                            retry_cnt += 1
                            sleep(2)
                    except NoSuchElementException:
                        retry_cnt = 0
                        self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)
                    if empty_count >= 5:
                        if refresh_count >= 3:
                            print("\nNo more tweets to scrape")
                            break
                        refresh_count += 1
                    empty_count += 1
                    sleep(1)
                else:
                    empty_count = 0
                    refresh_count = 0
            except StaleElementReferenceException:
                sleep(2)
                continue
            except KeyboardInterrupt:
                print("\nKeyboard Interrupt")
                self.interrupted = True
                break
            except Exception as e:
                print(f"\nError scraping tweets: {e}")
                break
        print("")
        if len(self.data) >= self.max_tweets or no_tweets_limit:
            print("Scraping Complete")
        else:
            print("Scraping Incomplete")
        if not no_tweets_limit:
            print(f"Tweets: {len(self.data)} out of {self.max_tweets}")

    def save_to_csv(self):
        print("Saving Tweets to CSV...")
        now = datetime.now()
        folder_path = "./tweets/"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created Folder: {folder_path}")
        data = {
            "Name": [tweet[0] for tweet in self.data],
            "Handle": [tweet[1] for tweet in self.data],
            "Timestamp": [tweet[2] for tweet in self.data],
            "Verified": [tweet[3] for tweet in self.data],
            "Content": [tweet[4] for tweet in self.data],
            "Comments": [tweet[5] for tweet in self.data],
            "Retweets": [tweet[6] for tweet in self.data],
            "Likes": [tweet[7] for tweet in self.data],
            "Analytics": [tweet[8] for tweet in self.data],
            "Tags": [tweet[9] for tweet in self.data],
            "Mentions": [tweet[10] for tweet in self.data],
            "Profile Image": [tweet[12] for tweet in self.data],
            "Tweet Link": [tweet[13] for tweet in self.data],
            "Tweet ID": [f"tweet_id:{tweet[14]}" for tweet in self.data],
            "IPFS Screenshot": [tweet[-1] for tweet in self.data]  # Use the last element
        }
        # Analyze tweets for deletion likelihood
        deletion_scores = []
        print("Analyzing tweets for deletion likelihood (this may take a while)...")
        for tweet in self.data:
            content = tweet[4]
            if not content.strip():
                score, analysis = 0.0, "No content provided."
            else:
                score, analysis = analyze_tweet(content)
            print(f"Tweet analysis: {analysis}")
            deletion_scores.append(score)
        data["Deletion Likelihood"] = deletion_scores
        # Build DataFrame without Emojis column
        df = pd.DataFrame(data)
        current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        file_path = f"{folder_path}{current_time}_tweets_1-{len(self.data)}.csv"
        pd.set_option("display.max_colwidth", None)
        df.to_csv(file_path, index=False, encoding="utf-8")
        print(f"CSV Saved: {file_path}")

    def get_tweets(self):
        return self.data
