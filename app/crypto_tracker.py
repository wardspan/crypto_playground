from datetime import datetime
import requests
import time
from sqlalchemy.orm import Session
from .models import PriceHistory, Portfolio, Holding
from .utils.rate_limiter import RateLimiter

class CryptoPortfolio:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.coingecko.com/api/v3"
        self.rate_limiter = RateLimiter(calls_per_minute=30)
        self.current_prices = {}

    def calculate_coins(self):
        """Calculate number of coins and current values"""
        try:
            portfolio = self.db.query(Portfolio).first()
            if not portfolio:
                print("No portfolio found")
                return False

            print("\n=== Calculating Portfolio Values ===")
            total_value = 0

            for holding in portfolio.holdings:
                # Get latest price
                latest_price = (
                    self.db.query(PriceHistory)
                    .filter_by(coin_id=holding.coin_id)
                    .order_by(PriceHistory.timestamp.desc())
                    .first()
                )
                
                if latest_price:
                    current_price = float(latest_price.price)
                    holding.current_price = current_price
                    holding.coins = holding.amount / current_price if current_price > 0 else 0
                    holding.current_value = holding.coins * current_price
                    total_value += holding.current_value
                    
                    # Calculate profit/loss
                    profit_loss = holding.current_value - holding.amount
                    profit_loss_pct = ((holding.current_value / holding.amount) - 1) * 100 if holding.amount > 0 else 0
                    
                    print(f"\n{holding.coin_id}:")
                    print(f"  Investment: ${holding.amount:.2f}")
                    print(f"  Coins: {holding.coins:.6f}")
                    print(f"  Current Price: ${current_price:.2f}")
                    print(f"  Current Value: ${holding.current_value:.2f}")
                    print(f"  Profit/Loss: ${profit_loss:.2f} ({profit_loss_pct:.1f}%)")

            # Update portfolio total value
            portfolio.current_value = total_value
            profit_loss = total_value - portfolio.initial_investment
            profit_loss_pct = ((total_value / portfolio.initial_investment) - 1) * 100 if portfolio.initial_investment > 0 else 0
            
            print("\nPortfolio Summary:")
            print(f"Initial Investment: ${portfolio.initial_investment:.2f}")
            print(f"Current Value: ${total_value:.2f}")
            print(f"Total Profit/Loss: ${profit_loss:.2f} ({profit_loss_pct:.1f}%)")

            self.db.commit()
            return True

        except Exception as e:
            print(f"Error calculating values: {e}")
            import traceback
            print(traceback.format_exc())
            self.db.rollback()
            return False

    def get_current_prices(self):
        """Get current prices for all coins in portfolio"""
        try:
            portfolio = self.db.query(Portfolio).first()
            if not portfolio:
                return {}

            current_prices = {}
            for holding in portfolio.holdings:
                print(f"\nFetching current price for {holding.coin_id}...")
                
                # Add delay between requests
                self.rate_limiter.wait_if_needed()
                
                response = requests.get(
                    f"{self.base_url}/simple/price",
                    params={
                        'ids': holding.coin_id,
                        'vs_currencies': 'usd'
                    },
                    headers={'accept': 'application/json'}
                )

                if response.status_code == 200:
                    data = response.json()
                    price = data.get(holding.coin_id, {}).get('usd')
                    if price:
                        current_prices[holding.coin_id] = price
                        print(f"{holding.coin_id}: ${price:.2f}")
                    else:
                        print(f"No price data for {holding.coin_id}")
                else:
                    print(f"Error fetching price for {holding.coin_id}: {response.status_code}")
                    print(response.text)

            return current_prices

        except Exception as e:
            print(f"Error fetching prices: {e}")
            return {}

    def get_portfolio_value(self):
        """Calculate current portfolio value"""
        total_value = 0
        prices = self.get_current_prices()
        portfolio = self.db.query(Portfolio).first()
        
        if not portfolio:
            return 0
            
        for holding in portfolio.holdings:
            if holding.coin_id in prices:
                price = prices[holding.coin_id]['usd']
                value = holding.coins * price
                total_value += value
                
        return total_value

    def save_price_history(self):
        """Save current prices to price history"""
        try:
            current_prices = self.get_current_prices()
            if not current_prices:
                return

            timestamp = datetime.now()
            records = []
            
            for coin_id, price in current_prices.items():
                record = PriceHistory(
                    coin_id=coin_id,
                    price=price,
                    timestamp=timestamp
                )
                records.append(record)

            if records:
                self.db.bulk_save_objects(records)
                self.db.commit()
                print(f"Saved {len(records)} price history records")

        except Exception as e:
            print(f"Error saving price history: {e}")
            self.db.rollback()

    def get_remaining_api_calls(self):
        """Get remaining API call limits"""
        return self.rate_limiter.get_remaining_calls()

    def get_historical_prices(self, days=7):
        """Get historical price data for all coins"""
        print("\n=== FETCHING HISTORICAL PRICES ===")
        try:
            portfolio = self.db.query(Portfolio).first()
            if not portfolio:
                print("No portfolio found!")
                return {}

            coin_ids = [holding.coin_id for holding in portfolio.holdings]
            print(f"Fetching data for coins: {coin_ids}")
            historical_data = {}

            for coin_id in coin_ids:
                print(f"\nFetching {coin_id} data...")
                
                url = f"{self.base_url}/coins/{coin_id}/market_chart"
                params = {
                    'vs_currency': 'usd',
                    'days': str(days)
                }
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'accept': 'application/json'
                }
                
                print(f"Making request to: {url}")
                print(f"With params: {params}")
                
                self.rate_limiter.wait_if_needed()
                
                response = requests.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    prices = data.get('prices', [])
                    
                    if prices:
                        print(f"Received {len(prices)} price points")
                        historical_data[coin_id] = []
                        
                        for price_point in prices:
                            timestamp = datetime.fromtimestamp(price_point[0]/1000)
                            price = float(price_point[1])
                            historical_data[coin_id].append({
                                'timestamp': timestamp,
                                'price': price
                            })
                        
                        print(f"First point: Time={historical_data[coin_id][0]['timestamp']}, "
                              f"Price=${historical_data[coin_id][0]['price']:.2f}")
                        print(f"Last point: Time={historical_data[coin_id][-1]['timestamp']}, "
                              f"Price=${historical_data[coin_id][-1]['price']:.2f}")
                    else:
                        print(f"No price data found for {coin_id}")
                else:
                    print(f"Error response: {response.status_code}")
                    print(response.text)
                
                time.sleep(6)

            return historical_data

        except Exception as e:
            print(f"Error in get_historical_prices: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    def initialize_price_history(self):
        """Initialize price history data"""
        print("\n=== INITIALIZING PRICE HISTORY ===")
        try:
            # Clear existing price history
            self.db.query(PriceHistory).delete()
            self.db.commit()
            print("Cleared existing price history")

            # Get historical prices
            historical_data = self.get_historical_prices()
            if not historical_data:
                print("No historical data received")
                return False

            # Save historical prices
            records = []
            for coin_id, prices in historical_data.items():
                print(f"\nProcessing {coin_id}:")
                print(f"Total points to save: {len(prices)}")
                
                for point in prices:
                    record = PriceHistory(
                        coin_id=coin_id,
                        price=point['price'],
                        timestamp=point['timestamp']
                    )
                    records.append(record)

            if records:
                print(f"\nSaving {len(records)} total records...")
                self.db.bulk_save_objects(records)
                self.db.commit()
                print("Save completed")
                return True

            return False

        except Exception as e:
            print(f"Error initializing price history: {e}")
            import traceback
            print(traceback.format_exc())
            self.db.rollback()
            return False
