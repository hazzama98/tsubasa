import os
import json
import time
import logging
import requests
from urllib.parse import unquote
import sys
import random
import base64
import threading
import itertools

logging.basicConfig(
    level=logging.INFO,
    format='[⚔] |  %(message)s',
)
logger = logging.getLogger(__name__)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')
        
def key_bot():
    url = base64.b64decode("aHR0cDovL2l0YmFhcnRzLmNvbS9hcGkuanNvbg==").decode('utf-8')
    try:
        response = requests.get(url)
        response.raise_for_status()
        try:
            data = response.json()
            header = data['header']
            print(header)
        except json.JSONDecodeError:
            print(response.text)
    except requests.RequestException as e:
        print_(f"Failed to load header")

def header():
    print("")
    print("╔════════════════════════════════════════════╗")
    print("║               Captain Tsubasa              ║") 
    print("╚════════════════════════════════════════════╝")
    print("")

API_CONFIG = {
    "BASE_URL": "https://api.app.ton.tsubasa-rivals.com/api",
    "ENDPOINTS": {
        "START": "/start",
        "TAP": "/tap",
        "ENERGY_RECOVERY": "/energy/recovery",
        "TAP_LEVELUP": "/tap/levelup",
        "ENERGY_LEVELUP": "/energy/levelup",
        "DAILY_REWARD": "/daily_reward/claim",
        "CARD_LEVELUP": "/card/levelup",
        "TASK_EXECUTE": "/task/execute",
        "TASK_ACHIEVEMENT": "/task/achievement"
    }
}

GAME_CONSTANTS = {
    "MAX_FAILED_ATTEMPTS": 3,
    "RETRY_DELAY": 2,
    "CYCLE_DELAY": 1,
    "COOLDOWN_WAIT": 20
}

def loading_animation(message="Processing", stop_event=None):
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for char in itertools.cycle(chars):
        if stop_event.is_set():
            break
        print(f"\r[{char}] {message}...", end='', flush=True)
        time.sleep(0.1)
    print("\r" + " " * (len(message) + 15) + "\r", end='', flush=True)

def process_with_loading(func, message="Processing"):
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=loading_animation, args=(message, stop_event))
    
    try:
        spinner_thread.start()
        
        result = func()
        
        stop_event.set()
        spinner_thread.join()
        print("\r" + " " * (len(message) + 15) + "\r", end='', flush=True)
        
        return result
        
    except Exception as e:
        stop_event.set()
        spinner_thread.join()
        print("\r" + " " * (len(message) + 15) + "\r", end='', flush=True)
        raise e

class TsubasaAPI:
    def __init__(self):
        self.mobile_user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
        ]

        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://app.ton.tsubasa-rivals.com",
            "Referer": "https://app.ton.tsubasa-rivals.com/",
            "User-Agent": random.choice(self.mobile_user_agents),
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def prompt_config(self):
        print("Please configure the following settings:")
        
        self.config = {
            "enableCardUpgrades": input("Enable card upgrades? (y/n): ").lower() == "y",
            "enableTapUpgrades": input("Enable tap upgrades? (y/n): ").lower() == "y",
            "enableEnergyUpgrades": input("Enable energy upgrades? (y/n): ").lower() == "y",
            "maxUpgradeCost": int(input("Maximum upgrade cost: ")),
            "maxTapUpgradeLevel": int(input("Maximum tap upgrade level: ")),
            "maxEnergyUpgradeLevel": int(input("Maximum energy upgrade level: "))
        }

        logger.info("Configuration completed.")

    def make_api_call(self, endpoint, payload, context):
        try:
            if random.random() < 0.3: 
                self.session.headers["User-Agent"] = random.choice(self.mobile_user_agents)
                
            time.sleep(random.uniform(0.8, 2.5))
            
            url = f"{API_CONFIG['BASE_URL']}{endpoint}"
            
            if "initData" in payload:
                user_data = json.loads(unquote(payload["initData"].split("user=")[1].split("&")[0]))
                self.session.headers["X-Player-Id"] = str(user_data["id"])
                
                payload["timestamp"] = int(time.time() * 1000)
                payload["client_token"] = base64.b64encode(os.urandom(16)).decode('utf-8')

            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            time.sleep(random.uniform(0.3, 1.0))
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            
            return {
                "success": False,
                "error": f"Unexpected response | Status: {response.status_code}"
            }

        except requests.exceptions.RequestException as error:
            return self.handle_api_error(error, context)

    def handle_api_error(self, error, context):
        if hasattr(error, "response") and error.response.status_code == 400:
            error_message = error.response.json().get("message", "No specific error message")

            if "Invalid id" in error_message:
                return {"success": False, "error": "invalid_id"}

            if "Wait for cooldown" in error_message:
                logger.warning(f"Cooldown period active for {context}")
                return {"success": False, "error": "cooldown", "message": error_message}

            if "Insufficient funds" in error_message:
                logger.warning(f"Insufficient funds for {context}")
                return {"success": False, "error": "insufficient_funds", "message": error_message}

            if "Invalid initData" in error_message:
                logger.error(f"Invalid initData for {context}")
                return {"success": False, "error": "invalid_initdata", "message": error_message}

            return {"success": False, "error": "Bad Request", "message": error_message}

        logger.error(f"Error in {context} | {str(error)}")
        return {"success": False, "error": "unknown", "message": str(error)}

    def process_daily(self, init_data):
        def claim_daily():
            result = self.call_daily_reward_api(init_data)
            return result

        daily_reward_result = process_with_loading(
            claim_daily,
            "Claiming daily rewards"
        )
        
        print("\r" + " " * 50 + "\r", end='', flush=True)
        logger.info(daily_reward_result.get("message"))

    def handle_energy_recovery(self, init_data, max_energy):
        time.sleep(1) 

        recovery_result = self.call_energy_recovery_api(init_data)

        if not recovery_result.get("success"):
            error_msg = recovery_result.get("error", "").lower()
            if "no energy recovery yet" in error_msg:
                logger.info("No energy recovery available, continuing with next feature...")
                return {"success": True, "skip_recovery": True}
            
            logger.warning(recovery_result.get("error") or "Energy recovery failed")
            return {"success": False}

        if recovery_result["energy"] == max_energy:
            logger.info(
                f"Energy recovery successful | Current energy: {recovery_result['energy']}/{max_energy}"
            )
            return {"success": True, "energy": recovery_result["energy"]}
        else:
            logger.warning(
                f"Incomplete energy recovery | Current energy: {recovery_result['energy']}/{max_energy}"
            )
            return {"success": False}

    def verify_energy_state(self, init_data, expected_energy, tolerance=0):
        verify_result = self.call_start_api(init_data)
        if not verify_result.get("success"):
            return {"success": False, "error": "Failed to verify energy state"}

        actual_energy = verify_result["energy"]
        energy_diff = abs(actual_energy - expected_energy)

        if energy_diff <= tolerance:
            return {"success": True, "energy": actual_energy}
        else:
            return {
                "success": False,
                "error": f"Energy mismatch | Expected: {expected_energy} | Actual: {actual_energy}",
                "energy": actual_energy
            }

    def format_number(self, num):
        return "{:,}".format(num)

    def get_card_info(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["START"],
            {"lang_code": "en", "initData": init_data},
            "getCardInfo"
        )

        if not result.get("success") or not result.get("data", {}).get("card_info"):
            logger.warning("Card information not found!")
            return None

        cards = []
        for category in result["data"]["card_info"]:
            for card in category["card_list"]:
                cards.append({
                    "categoryId": card["category"],
                    "cardId": card["id"],
                    "level": card["level"],
                    "cost": card["cost"],
                    "unlocked": card["unlocked"],
                    "name": card["name"],
                    "profitPerHour": card["profit_per_hour"],
                    "nextProfitPerHour": card["next_profit_per_hour"],
                    "end_datetime": card.get("end_datetime")
                })
        return cards

    def level_up_card(self, card, init_data):
        level_up_payload = {
            "category_id": card["categoryId"],
            "card_id": card["cardId"],
            "initData": init_data
        }

        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["CARD_LEVELUP"],
            level_up_payload,
            f"levelUpCard-{card['cardId']}"
        )

        return result

    def level_up_cards(self, init_data, total_coins):
        if not self.config["features"]["cardUpgrades"]:
            logger.info("Card upgrades are disabled in config")
            return total_coins

        updated_total_coins = total_coins
        leveled_up = False
        cooldown_cards = set()

        while True:
            leveled_up = False
            card_info = self.get_card_info(init_data)

            if not card_info:
                logger.warning("Unable to get card information")
                break

            sorted_cards = sorted(
                card_info,
                # key=lambda x: x["nextProfitPerHour"],
                key=lambda x: x["level"],
                reverse=True
            )

            result = self.process_card_upgrades(
                sorted_cards,
                updated_total_coins,
                init_data,
                cooldown_cards
            )

            leveled_up = result["leveledUp"]
            updated_total_coins = result["updatedTotalCoins"]

            if not leveled_up:
                break

            time.sleep(random.uniform(1.5, 4.0))

        return updated_total_coins

    def sort_cards_by_profitability(self, cards):
        return sorted(cards, key=lambda x: x["nextProfitPerHour"], reverse=True)

    def process_card_upgrades(self, sorted_cards, total_coins, init_data, cooldown_cards):
        current_time = int(time.time())
        leveled_up = False
        updated_total_coins = total_coins

        for card in sorted_cards:
            if self.should_skip_card(card, current_time, cooldown_cards):
                continue

            if self.can_upgrade_card(card, updated_total_coins):
                upgrade_result = self.attempt_card_upgrade(
                    card,
                    init_data,
                    updated_total_coins,
                    cooldown_cards
                )

                if upgrade_result["success"]:
                    updated_total_coins = upgrade_result["updatedTotalCoins"]
                    leveled_up = True
                    break

        return {"leveledUp": leveled_up, "updatedTotalCoins": updated_total_coins}

    def should_skip_card(self, card, current_time, cooldown_cards):
        if card["cardId"] in cooldown_cards:
            return True

        if card.get("end_datetime") and current_time > card["end_datetime"]:
            return True

        return False

    def can_upgrade_card(self, card, total_coins):
        return (
            card["unlocked"] and
            total_coins >= card["cost"] and
            card["cost"] <= self.config["upgrades"]["maxCardUpgradeCost"] and
            card["level"] < self.config["upgrades"]["maxCardLevel"]
        )

    def attempt_card_upgrade(self, card, init_data, total_coins, cooldown_cards):
        try:
            upgrade_result = self.level_up_card(card, init_data)

            if upgrade_result["success"]:
                updated_total_coins = total_coins - card["cost"]
                print("\r" + " " * 50 + "\r", end='', flush=True)
                logger.info(
                    f"Successfully upgraded card | {card['name']} | "
                    f"Level: {card['level']} → {card['level'] + 1} | "
                    f"Cost: {self.format_number(card['cost'])} | "
                    f"Profit/hour: {self.format_number(card['profitPerHour'])} → {self.format_number(card['nextProfitPerHour'])} | "
                    f"Remaining balance: {self.format_number(updated_total_coins)}"
                )
                return {"success": True, "updatedTotalCoins": updated_total_coins}

            return {"success": False}
        except Exception as error:
            return self.handle_card_upgrade_error(error, card, cooldown_cards)

    def handle_card_upgrade_error(self, error, card, cooldown_cards):
        if hasattr(error, "response") and error.response.status_code == 400:
            error_message = error.response.json().get("message")

            if "Wait for cooldown" in error_message:
                logger.warning(f"Cooldown for card {card['name']} ({card['cardId']}). Skipping for now.")
                cooldown_cards.add(card["cardId"])
            elif "Insufficient funds" in error_message:
                logger.warning(f"Not enough coins to upgrade {card['name']} ({card['cardId']}). Stopping upgrades.")
            else:
                logger.error(f"Failed to upgrade card {card['name']} ({card['cardId']}): {error_message}")

        return {"success": False}

    def log_account_status(self, start_result):
        if "total_coins" in start_result:
            logger.info(f"Balance: {start_result['total_coins']}")
            logger.info(f"Energy: {start_result['energy']}/{start_result['max_energy']}")
            logger.info(f"Multi Tap Count: {start_result['multi_tap_count']}")
            logger.info(f"Profit per second: {start_result['profit_per_second']}")

    def countdown(self, seconds):
        for i in range(seconds, -1, -1):
            print(f"\rWait {i} seconds to continue the loop", end="")
            time.sleep(1)
        print("\r" + " " * 50 + "\r", end="")

    def process_account(self, init_data):
        def start_process():
            return self.call_start_api(init_data)
            
        start_result = process_with_loading(
            start_process,
            "Loading account data"
        )
        
        if not start_result.get("success"):
            if start_result.get("skipAccount"):
                return
            return

        self.log_account_status(start_result)

        if self.config["features"]["tapUpgrades"]:
            def upgrade_process():
                return self.upgrade_game_stats(init_data)
            process_with_loading(
                upgrade_process,
                "Upgrading statistics"
            )
        
        if self.config["features"]["taskExecution"]:
            def task_process():
                return self.process_tasks(init_data, start_result.get("tasks", []))
            process_with_loading(
                task_process,
                "Executing tasks"
            )

        if self.config["features"]["autoTap"]:
            def tap_process():
                return self.tap_and_recover(init_data)
            total_taps = process_with_loading(
                tap_process,
                "Performing auto tap"
            )
            if total_taps > 0:
                pass

        if self.config["features"]["dailyRewards"]:
            def daily_process():
                return self.process_daily(init_data)
            process_with_loading(
                daily_process,
                "Claiming daily rewards"
            )

        if self.config["features"]["cardUpgrades"]:
            def card_process():
                return self.level_up_cards(init_data, start_result["total_coins"])
            updated_total_coins = process_with_loading(
                card_process,
                "Upgrading cards"
            )
            logger.info(f"All eligible cards have been upgraded")

    def main(self):
        data_file = os.path.join(os.path.dirname(__file__), "query.txt")
        with open(data_file, "r", encoding="utf-8") as f:
            data = [line.strip() for line in f if line.strip()]

        while True:
            try:
                clear_terminal()
                key_bot()
                header()
                
                for i, init_data in enumerate(data):
                    try:
                        logger.info("═" * 35)
                        
                        user_data = json.loads(unquote(init_data.split("user=")[1].split("&")[0]))
                        first_name = user_data["first_name"]
                        logger.info(f"Account {i + 1} | {first_name}")

                        self.process_account(init_data)

                    except Exception as e:
                        logger.error(f"Error processing account {i + 1} | {str(e)}")
                        continue 

                logger.info("═" * 35)  
                cooldown_time = self.config['delays']['cooldownWait'] * 60  
                logger.info(f"All accounts processed. Starting cooldown period ({cooldown_time//60} minutes)...")
                
                for remaining in range(cooldown_time, 0, -1):
                    minutes = remaining // 60
                    seconds = remaining % 60
                    print(f"\rNext cycle in: {minutes:02d}:{seconds:02d}", end="")
                    time.sleep(1)
                print("\r" + " " * 50 + "\r", end="")  

                clear_terminal()
                key_bot()
                header()

            except Exception as e:
                logger.error(f"Main loop error: {str(e)}")
                time.sleep(60) 

    def call_start_api(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["START"],
            {"lang_code": "en", "initData": init_data},
            "callStartAPI"
        )

        if not result.get("success"):
            if result.get("error") == "invalid_initdata":
                return {"success": False, "skipAccount": True}
            return {"success": False, "error": result.get("message", "Unknown error")}

        game_data = result.get("data", {}).get("game_data", {})
        user_data = game_data.get("user", {})

        return {
            "success": True,
            "total_coins": user_data.get("total_coins", 0),
            "energy": user_data.get("energy", 0),
            "max_energy": user_data.get("max_energy", 0),
            "multi_tap_count": user_data.get("multi_tap_count", 0),
            "profit_per_second": user_data.get("profit_per_second", 0),
            "tasks": result.get("data", {}).get("task_info", [])
        }

    def call_daily_reward_api(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["DAILY_REWARD"],
            {"initData": init_data},
            "callDailyRewardAPI"
        )

        if result.get("success"):
            return {"success": True, "message": "Daily check-in successful"}
        
        if result.get("error") == "cooldown":
            return {"success": False, "message": "You have already checked in today"}
        
        return {"success": False, "message": result.get("error", "Failed to check in")}

    def call_energy_recovery_api(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["ENERGY_RECOVERY"],
            {"initData": init_data},
            "energyRecoveryAPI"
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("message", "Energy recovery failed")}

        game_data = result.get("data", {}).get("game_data", {})
        user_data = game_data.get("user", {})

        return {
            "success": True,
            "energy": user_data.get("energy", 0),
            "max_energy": user_data.get("max_energy", 0)
        }

    def upgrade_game_stats(self, init_data):
        tap_result = self.call_tap_api(init_data, 1)
        if not tap_result.get("success"):
            logger.error(tap_result.get("error"))
            return

        required_props = [
            "total_coins",
            "energy",
            "max_energy", 
            "multi_tap_count",
            "profit_per_second",
            "tap_level",
            "energy_level"
        ]

        missing_props = [prop for prop in required_props if tap_result.get(prop) is None]
        if missing_props:
            logger.error(f"Missing required properties | {', '.join(missing_props)}")
            return

        total_coins = tap_result["total_coins"]
        tap_level = tap_result["tap_level"]
        energy_level = tap_result["energy_level"]

        if self.config["features"]["tapUpgrades"]:
            tap_upgrade_result = self.upgrade_tap_level(
                init_data,
                tap_level,
                total_coins
            )
            if tap_upgrade_result.get("success"):
                total_coins = tap_upgrade_result["total_coins"]

        if self.config["features"]["energyUpgrades"]:
            energy_upgrade_result = self.upgrade_energy_level(
                init_data,
                energy_level,
                total_coins
            )
            if energy_upgrade_result.get("success"):
                total_coins = energy_upgrade_result["total_coins"]

        return total_coins

    def calculate_tap_level_up_cost(self, current_level):
        return 1000 * current_level

    def calculate_energy_level_up_cost(self, current_level):
        return 1000 * current_level

    def upgrade_tap_level(self, init_data, current_tap_level, available_coins):
        total_coins = available_coins
        tap_level = current_tap_level
        tap_level_up_cost = self.calculate_tap_level_up_cost(tap_level)

        while (
            tap_level < self.config["upgrades"]["maxTapUpgradeLevel"] and
            total_coins >= tap_level_up_cost
        ):
            tap_upgrade_result = self.call_tap_level_up_api(init_data)

            if not tap_upgrade_result.get("success"):
                break

            tap_level = tap_upgrade_result["tap_level"]
            total_coins = tap_upgrade_result["total_coins"]
            tap_level_up_cost = self.calculate_tap_level_up_cost(tap_level)

            logger.info(
                f"Tap upgrade successful | Level: {tap_level} | Cost: {tap_level_up_cost} | Balance: {total_coins}"
            )

        return {"success": True, "total_coins": total_coins}

    def upgrade_energy_level(self, init_data, current_energy_level, available_coins):
        total_coins = available_coins
        energy_level = current_energy_level
        energy_level_up_cost = self.calculate_energy_level_up_cost(energy_level)

        while (
            energy_level < self.config["upgrades"]["maxEnergyUpgradeLevel"] and
            total_coins >= energy_level_up_cost
        ):
            energy_upgrade_result = self.call_energy_level_up_api(init_data)

            if not energy_upgrade_result.get("success"):
                break

            energy_level = energy_upgrade_result["energy_level"]
            total_coins = energy_upgrade_result["total_coins"]
            energy_level_up_cost = self.calculate_energy_level_up_cost(energy_level)

            logger.info(
                f"Energy upgrade successful | Level: {energy_level} | Cost: {energy_level_up_cost} | Balance: {total_coins}"
            )

        return {"success": True, "total_coins": total_coins}

    def call_tap_api(self, init_data, tap_count):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["TAP"],
            {"tapCount": tap_count, "initData": init_data},
            "callTapAPI"
        )

        if not result.get("success"):
            return result

        game_data = result.get("data", {}).get("game_data", {})
        user_data = game_data.get("user", {})

        return {
            "success": True,
            **user_data
        }

    def call_tap_level_up_api(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["TAP_LEVELUP"],
            {"initData": init_data},
            "tapLevelUpAPI"
        )

        if not result.get("success"):
            return result

        game_data = result.get("data", {}).get("game_data", {})
        user_data = game_data.get("user", {})

        return {
            "success": True,
            "tap_level": user_data.get("tap_level"),
            "tap_level_up_cost": user_data.get("tap_level_up_cost"),
            "multi_tap_count": user_data.get("multi_tap_count"),
            "total_coins": user_data.get("total_coins")
        }

    def call_energy_level_up_api(self, init_data):
        result = self.make_api_call(
            API_CONFIG["ENDPOINTS"]["ENERGY_LEVELUP"],
            {"initData": init_data},
            "energyLevelUpAPI"
        )

        if not result.get("success"):
            return result

        game_data = result.get("data", {}).get("game_data", {})
        user_data = game_data.get("user", {})

        return {
            "success": True,
            "energy_level": user_data.get("energy_level"),
            "energy_level_up_cost": user_data.get("energy_level_up_cost"),
            "max_energy": user_data.get("max_energy"),
            "total_coins": user_data.get("total_coins")
        }

    def tap_and_recover(self, init_data):
        total_taps = 0
        failed_attempts = 0
        max_attempts = GAME_CONSTANTS["MAX_FAILED_ATTEMPTS"]
        
        try:
            def get_initial_status():
                start_result = self.call_start_api(init_data)
                
                if not start_result.get("success"):
                    raise Exception("Failed to get initial status")

                current_energy = start_result["energy"]
                max_energy = start_result["max_energy"]
                multi_tap_count = start_result["multi_tap_count"]

                if not multi_tap_count:
                    raise Exception("Multi tap count not available")

                return current_energy, max_energy, multi_tap_count

            initial_status = process_with_loading(
                get_initial_status,
                "Checking energy status"
            )
            
            current_energy, max_energy, multi_tap_count = initial_status
            possible_taps = current_energy // multi_tap_count
            
            logger.info(f"Energy available: {current_energy}/{max_energy} | Target taps: {possible_taps}x")

            if possible_taps > 0:
                def do_tap():
                    tap_result = self.call_tap_api(init_data, possible_taps)
                    if not tap_result.get("success"):
                        raise Exception("Failed to perform tap")
                    return tap_result

                tap_result = process_with_loading(
                    do_tap,
                    "Performing tap"
                )
                
                total_taps = possible_taps
                formatted_balance = self.format_number(tap_result["total_coins"])
                logger.info(
                    f"Tap completed | {total_taps}x | "
                    f"Energy: {tap_result['energy']}/{max_energy} | "
                    f"Balance: {formatted_balance}"
                )

        except Exception as error:
            logger.error(f"Error in tap_and_recover: {str(error)}")
            
        return total_taps

    def process_tasks(self, init_data, tasks):
        if not tasks or len(tasks) == 0:
            return

        for task in tasks:
            try:
                if not task.get("id") or task.get("status") == 2:
                    continue

                execute_result = self.execute_task(init_data, task["id"])
                if execute_result.get("success"):
                    achievement_result = self.check_task_achievement(init_data, task["id"])
                    if achievement_result.get("success"):
                        logger.info(
                            f"Task | {achievement_result['title']} | "
                            f"Completed | {achievement_result['reward']}"
                        )
                time.sleep(1)  

            except Exception:
                continue 
            
    def execute_task(self, init_data, task_id):
        try:
            result = self.make_api_call(
                API_CONFIG["ENDPOINTS"]["TASK_EXECUTE"],
                {
                    "task_id": task_id, 
                    "initData": init_data,
                    "lang_code": "en"
                },
                f"executeTask - {task_id}"
            )
            return {"success": result.get("success", False)}

        except Exception:
            return {"success": False}  

    def check_task_achievement(self, init_data, task_id):
        try:
            result = self.make_api_call(
                API_CONFIG["ENDPOINTS"]["TASK_ACHIEVEMENT"],
                {
                    "task_id": task_id, 
                    "initData": init_data,
                    "lang_code": "en"
                },
                f"checkTaskAchievement - {task_id}"
            )

            if not result.get("success"):
                return {"success": False}

            task_info = result.get("data", {}).get("task_info", [])
            if not task_info:
                return {"success": False}

            updated_task = next(
                (task for task in task_info if task["id"] == task_id),
                None
            )

            if not updated_task:
                return {"success": False}

            if updated_task.get("status") == 2:
                return {
                    "success": True,
                    "title": updated_task.get("title", "Unknown Task"),
                    "reward": updated_task.get("reward", "No reward info")
                }

            return {"success": False}

        except Exception as e:
            logger.error(f"Error checking task achievement {task_id}: {str(e)}")
            return {"success": False}

if __name__ == "__main__":
    clear_terminal()
    key_bot()
    header()
    client = TsubasaAPI()
    try:
        client.main()
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    except Exception as e:
        logger.error(f"Program error: {str(e)}")
        sys.exit(1)
