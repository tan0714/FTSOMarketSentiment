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

# NEW: Import FTSO & price helpers
from ftso_push import push_aggregated_score
from ftso_price import get_price_for
from ai_coin_identifier import identify_coin

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
        header = "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/109.0.5414.87 Mobile Safari/537.36"
        browser_option = FirefoxOptions()
        browser_option.add_argument("--no-sandbox")
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument("--ignore-certificate-errors")
        browser_option.add_argument("--disable-gpu")
        browser_option.add_argument("--disable-notifications")
        browser_option.add_argument("--disable-popup-blocking")
        browser_option.add_argument(f"--user-agent={header}")
        if proxy:
            browser_option.add_argument(f"--proxy-server={proxy}")
        if self.headlessState.lower() == 'yes':
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
                path = GeckoDriverManager().install()
                service = FirefoxService(executable_path=path)
                logging.info("Initializing FirefoxDriver with downloaded driver...")
                driver = webdriver.Firefox(service=service, options=browser_option)
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
            auth_token = next((c['value'] for c in cookies if c['name']=='auth_token'), None)
            if auth_token is None:
                raise ValueError("Login failed: unstable connection, incorrect username, or incorrect password.")
            print("Login Successful")
            logging.info("Login Successful")
        except Exception as e:
            print(f"Login Failed: {e}")
            logging.error(f"Login Failed: {e}")
            sys.exit(1)

    def _input_username(self):
        attempt = 0
        while True:
            try:
                inp = self.driver.find_element("xpath", "//input[@autocomplete='username']")
                inp.send_keys(self.username, Keys.RETURN)
                sleep(3)
                return
            except NoSuchElementException:
                attempt += 1
                if attempt >= 3:
                    print("Error inputting username after multiple attempts.")
                    logging.error("Error inputting username.")
                    self.driver.quit()
                    sys.exit(1)
                sleep(2)

    def _input_unusual_activity(self):
        attempt = 0
        while True:
            try:
                ua = self.driver.find_element("xpath", "//input[@data-testid='ocfEnterTextTextInput']")
                ua.send_keys(self.username, Keys.RETURN)
                sleep(3)
                return
            except NoSuchElementException:
                attempt += 1
                if attempt >= 3:
                    return

    def _input_password(self):
        attempt = 0
        while True:
            try:
                pwd = self.driver.find_element("xpath", "//input[@autocomplete='current-password']")
                pwd.send_keys(self.password, Keys.RETURN)
                sleep(3)
                return
            except NoSuchElementException:
                attempt += 1
                if attempt >= 3:
                    print("Error inputting password after multiple attempts.")
                    logging.error("Error inputting password.")
                    self.driver.quit()
                    sys.exit(1)
                sleep(2)

    def go_to_home(self):
        self.driver.get("https://twitter.com/home")
        sleep(3)

    def go_to_profile(self):
        if not self.scraper_details["username"]:
            print("Username is not set.")
            logging.error("Username is not set.")
            sys.exit(1)
        self.driver.get(f"https://twitter.com/{self.scraper_details['username']}")
        sleep(3)

    def go_to_hashtag(self):
        if not self.scraper_details["hashtag"]:
            print("Hashtag is not set.")
            logging.error("Hashtag is not set.")
            sys.exit(1)
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
        self.driver.get("https://twitter.com/i/bookmarks")
        sleep(3)

    def go_to_search(self):
        if not self.scraper_details["query"]:
            print("Query is not set.")
            logging.error("Query is not set.")
            sys.exit(1)
        url = f"https://twitter.com/search?q={self.scraper_details['query']}&src=typed_query"
        if self.scraper_details["tab"] == "Latest":
            url += "&f=live"
        self.driver.get(url)
        sleep(3)

    def get_tweet_cards(self):
        self.tweet_cards = self.driver.find_elements(
            "xpath", '//article[@data-testid="tweet" and not(@disabled)]'
        )

    def remove_hidden_cards(self):
        try:
            hidden = self.driver.find_elements(
                "xpath", '//article[@data-testid="tweet" and @disabled]'
            )
            for card in hidden[1:-2]:
                self.driver.execute_script(
                    "arguments[0].parentNode.parentNode.parentNode.remove();", card
                )
        except Exception:
            pass

    def scrape_tweets(self, max_tweets=50, no_tweets_limit=False, scrape_username=None,
                      scrape_hashtag=None, scrape_bookmarks=False, scrape_query=None,
                      scrape_latest=True, scrape_top=False, scrape_poster_details=False, router=None):
        logging.info("Starting tweet scraping process...")
        self._config_scraper(max_tweets, scrape_username, scrape_hashtag, scrape_bookmarks,
                             scrape_query, scrape_latest, scrape_top, scrape_poster_details)
        if router is None:
            router = self.router
        router()
        d = self.scraper_details
        if d["type"] == "Username":
            print(f"Scraping Tweets from @{d['username']}...")
        elif d["type"] == "Hashtag":
            print(f"Scraping {d['tab']} Tweets from #{d['hashtag']}...")
        elif d["type"] == "Bookmarks":
            print("Scraping Tweets from bookmarks...")
        elif d["type"] == "Query":
            print(f"Scraping {d['tab']} Tweets from {d['query']} search...")
        else:
            print("Scraping Tweets from Home...")

        try:
            btn = self.driver.find_element(
                "xpath", "//span[text()='Refuse non-essential cookies']/../../.."
            )
            btn.click()
        except NoSuchElementException:
            pass

        self.progress.print_progress(0, False, 0, no_tweets_limit)
        refresh_count = added = empty = retry = 0
        while self.scroller.scrolling:
            try:
                self.get_tweet_cards()
                added = 0
                for card in self.tweet_cards[-15:]:
                    try:
                        cid = str(card)
                        if cid not in self.tweet_ids:
                            self.tweet_ids.add(cid)
                            if not d["poster_details"]:
                                self.driver.execute_script("arguments[0].scrollIntoView();", card)
                            tw = Tweet(card=card, driver=self.driver,
                                       actions=self.actions,
                                       scrape_poster_details=d["poster_details"])
                            if tw and not tw.error and tw.tweet and not tw.is_ad:
                                try:
                                    ipfs = screenshot_and_pin(card)
                                    ipfs_url = f"https://gateway.pinata.cloud/ipfs/{ipfs}"
                                    print(f"Tweet screenshot pinned to IPFS: {ipfs_url}")
                                except Exception as e:
                                    print(f"Error pinning tweet screenshot: {e}")
                                    ipfs_url = ""
                                row = list(tw.tweet) + [ipfs_url]
                                self.data.append(tuple(row))
                                added += 1
                                print(f"Tweet scraped: {tw.tweet}")
                                self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)
                                if len(self.data) >= self.max_tweets and not no_tweets_limit:
                                    self.scroller.scrolling = False
                                    break
                    except NoSuchElementException:
                        continue
                if len(self.data) >= self.max_tweets and not no_tweets_limit:
                    break
                if added == 0:
                    try:
                        while retry < 15:
                            rb = self.driver.find_element("xpath", "//span[text()='Retry']/../../..")
                            self.progress.print_progress(len(self.data), True, retry, no_tweets_limit)
                            sleep(600)
                            rb.click()
                            retry += 1
                            sleep(2)
                    except NoSuchElementException:
                        retry = 0
                        self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)
                    if empty >= 5:
                        if refresh_count >= 3:
                            print("\nNo more tweets to scrape")
                            break
                        refresh_count += 1
                    empty += 1
                    sleep(1)
                else:
                    empty = refresh_count = 0
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
        folder = "./tweets/"
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created Folder: {folder}")

        data = {
            "Name": [t[0] for t in self.data],
            "Handle": [t[1] for t in self.data],
            "Timestamp": [t[2] for t in self.data],
            "Verified": [t[3] for t in self.data],
            "Content": [t[4] for t in self.data],
            "Comments": [t[5] for t in self.data],
            "Retweets": [t[6] for t in self.data],
            "Likes": [t[7] for t in self.data],
            "Analytics": [t[8] for t in self.data],
            "Tags": [t[9] for t in self.data],
            "Mentions": [t[10] for t in self.data],
            "Profile Image": [t[12] for t in self.data],
            "Tweet Link": [t[13] for t in self.data],
            "Tweet ID": [f"tweet_id:{t[14]}" for t in self.data],
            "IPFS Screenshot": [t[-1] for t in self.data],
        }

        # Analyze tweets for deletion likelihood
        deletion_scores = []
        print("Analyzing tweets for deletion likelihood (this may take a while)...")
        for t in self.data:
            content = t[4]
            if not content.strip():
                score = 0.0
                analysis = "No content provided."
            else:
                score, analysis = analyze_tweet(content)
            print(f"Tweet analysis: {analysis}")
            deletion_scores.append(score)
        data["Deletion Likelihood"] = deletion_scores

        # Build DataFrame & save
        df = pd.DataFrame(data)
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        path = f"{folder}{timestamp}_tweets_1-{len(self.data)}.csv"
        pd.set_option("display.max_colwidth", None)
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"CSV Saved: {path}")

        # --- Filecoin pipeline ---
        import store
        logging.info("➡️ Beginning Filecoin pipeline…")
        root_cid = store.pin_to_pinata(path)
        root, car_cid, car_path, car_size = store.make_car(path)
        store.upload_car(root, car_cid, car_path, car_size)
        deal_resp = store.create_deal(root, car_cid)
        try:
            deal_id = deal_resp[0]["p"]["out"]["dealId"]
        except:
            logging.warning("⚠️ Could not parse dealId; defaulting to 0")
            deal_id = 0
        title = f"Twitter dump {os.path.basename(path)}"
        desc = f"{len(self.data)} tweets @ {datetime.now().isoformat()}"
        price = int(os.getenv("DATASET_PRICE_WEI", "0"))
        preview = df.head(2).to_json(orient="records")
        store.register_on_chain(root_cid, car_size, deal_id, title, desc, price, preview)
        print(f"✅ Pipeline done: rootCID={root_cid}, deal={deal_id}")

        # --- Aggregated overall score → FTSO push ---
        avg = sum(deletion_scores) / len(deletion_scores) if deletion_scores else 0.0
        norm = int(avg * 100)
        print(f"Normalized aggregated tweet deletion-likelihood score: {norm}")
        tx = push_aggregated_score(norm)
        print(f"Pushed aggregated score {norm}, tx hash {tx}")

        # ------------- Multi-coin grouping & output ----------------
        import csv
        ts_run = datetime.utcnow().isoformat() + "Z"
        pairs = list(zip(self.data, deletion_scores))
        groups = {}
        for td, sc in pairs:
            coin = identify_coin([td[4]])
            groups.setdefault(coin, []).append((td, sc))

        for coin, items in groups.items():
            # sentiment
            scores = [s for (_td, s) in items]
            avg_sc = sum(scores) / len(scores) if scores else 0.0
            norm_sc = int(avg_sc * 100)
            # price
            try:
                price_ftso, ts_ftso = get_price_for(coin)
            except KeyError:
                print(f"⚠️ {coin} not in feed; skipping")
                continue
            # strength = (# tweets) * (sum followers)
            num = len(items)
            total_followers = sum(int(td[17]) if td[17].isdigit() else 0 for (td, _s) in items)
            strength = num * total_followers
            # write CSV
            fname = f"./FINAL_{coin}.csv"
            need_hdr = not os.path.exists(fname)
            with open(fname, "a", newline="") as cf:
                w = csv.writer(cf)
                if need_hdr:
                    w.writerow(["timestamp", "score", "price", "strength"])
                w.writerow([ts_run, norm_sc, price_ftso, strength])
            print(f"→ Wrote {coin}: {ts_run}, {norm_sc}, {price_ftso}, {strength}")
        # -------------------------------------------------------------

    def get_tweets(self):
        return self.data
