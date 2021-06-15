'''
Long term buy and hold strategy using MACD

BUY:
1. Weekly MACD is bullish
2. Daily MACD is bullish
ACTION: Buy at market price

SELL BY SETTING STOP LOSS:
1. Weekly MACD is bullish
2. Daily MACD is bearish
ACTION:
- Get close price of last daily candle stick
- Set that price as the SL if that price is less than the current price.

SELL AT MARKET PRICE:
1. Weekly MACD is bullish
2. Daily MACD is bearish and last daily candle price is greater than the current price
OR:
1. Weekly MACD is bearish
2. Daily MACD is bearish
ACTION: Sell at Market Price
'''
# Available indicators here: https://python-tradingview-ta.readthedocs.io/en/latest/usage.html#retrieving-the-analysis

from tradingview_ta import TA_Handler, Interval, Exchange
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob
import time
import threading
import json

# indicator
OSC_INDICATORS = ['MACD'] # Indicators to use in Oscillator analysis
# intervals
DAILY_INTERVAL = Interval.INTERVAL_1_DAY # Daily check
WEEKLY_INTERVAL = Interval.INTERVAL_1_WEEK # Weekly check

EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'
PAIR_WITH = 'USDT'
TICKERS = 'allcoins.txt'
TEST_MODE = True
TIME_TO_WAIT = 1 # Minutes to wait between analysis
FULL_LOG = False # Display analysis result to console

def set_stop_loss(pair, stop_loss):
  # load testmode of mainnet
  coins_bought = {}
  coins_bought_file_path = 'coins_bought.json'
  if TEST_MODE:
    coins_bought_file_path = 'test_' + coins_bought_file_path
    
  # if saved coins_bought json file exists and it's not empty then load it
  if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
    with open(coins_bought_file_path) as file:
      # coin already exist in file
      coins_bought = json.load(file)
      if pair in coins_bought:
        coins_bought[pair]['stop_loss'] = stop_loss
    # write to file
    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=2)
        
# write to file
def write_failed_coins(pairs):
  failed_coins_file_path = 'failed_coins.txt'
  failed_coins = ''
  for pair in pairs:
    failed_coins += pair + '\n'
  with open(failed_coins_file_path,'w') as f:
    f.write(failed_coins + '\n')

def analyze(pairs):
  buy_signal_coins = {}
  sell_signal_coins = {}
  sl_signal_coins = {}
  daily_analysis = {}
  weekly_analysis = {}
  daily_handler = {}
  weekly_handler = {}
  failed_coins = []
  
  if os.path.exists('signals/signalmacd.exs'):
    os.remove('signals/signalmacd.exs')

  for pair in pairs:
    # daily chart check
    daily_handler[pair] = TA_Handler(
      symbol=pair,
      exchange=EXCHANGE,
      screener=SCREENER,
      interval=DAILY_INTERVAL,
      timeout= 10
    )
    # weekly chart check
    weekly_handler[pair] = TA_Handler(
      symbol=pair,
      exchange=EXCHANGE,
      screener=SCREENER,
      interval=WEEKLY_INTERVAL,
      timeout= 10
    )
      
  for pair in pairs:
    try:
      daily_analysis = daily_handler[pair].get_analysis()
      weekly_analysis = weekly_handler[pair].get_analysis()
    except Exception as e:
      print(f'SignalMACD: Weekly analysis error: {pair}')
      failed_coins.append(pair)
    oscBuyCheck = 0
    oscSellCheck = 0
    oscSLCheck = 0
    for indicator in OSC_INDICATORS:
      if indicator in daily_analysis.oscillators['COMPUTE']:
        daily_signal = daily_analysis.oscillators['COMPUTE'][indicator]
      else:
        # MACD is not present. Do not buy coin
        daily_signal = "SELL"
      if FULL_LOG:
        print('... ... ... ... ... ... ... ... ... ... ...')
        print(f'Daily signals for {pair} is {daily_signal}')
      if indicator in weekly_analysis.oscillators['COMPUTE']:
        weekly_signal = weekly_analysis.oscillators['COMPUTE'][indicator]
      else:
        # MACD is not present. Do not buy coin
        weekly_signal = "SELL"
      if FULL_LOG:
        print(f'Weekly signals for {pair} is {weekly_signal}')
        print('... ... ... ... ... ... ... ... ... ... ...')
      # If bullish
      if 'BUY' in daily_signal and 'BUY' in weekly_signal: 
        buy_signal_coins[pair] = pair
        print(f'SignalMACD: Buy signal detected on {pair}')
        oscBuyCheck += 1
      elif 'SELL' in daily_signal and 'BUY' in weekly_signal: 
        sl_signal_coins[pair] = pair
        # Set stop loss
        sl_signal_coins['daily_close_price'] = daily_analysis.indicators['close']
        set_stop_loss(pair, daily_analysis.indicators['close'])
        if FULL_LOG:
          print(f'SignalMACD: Daily signal is bearish for coin {pair}')
          print(f"SignalMACD: Stop loss price for {pair} is {daily_analysis.indicators['close']}")
        # Set stop loss or sell at market price
        oscSLCheck += 1
      elif 'SELL' in weekly_signal: 
        sell_signal_coins[pair] = pair
        if FULL_LOG:
          print(f'SignalMACD: Both weekly and daily signals for coin {pair} are bearish. Sell immediately!')
        oscSellCheck += 1

    if oscBuyCheck > 0:
      if FULL_LOG:
        print(f'SignalMACD:{pair} Buy signals: {oscBuyCheck}')
      with open('signals/signalmacd.exs','a+') as f:
        f.write(pair + '\n')
    elif oscSellCheck > 0:
      if FULL_LOG:
        print(f'SignalMACD:{pair} Sell signals: {oscSellCheck}')
    elif oscSLCheck > 0:
      if FULL_LOG:
        print(f'SignalMACD:{pair} Set stop loss signals: {oscSLCheck}') 

  return buy_signal_coins, sell_signal_coins, sl_signal_coins, failed_coins

def do_work():
  buy_signal_coins, sell_signal_coins, sl_signal_coins = {}, {}, {}
  pairs = {}

  pairs=[line.strip() for line in open(TICKERS)]
  for line in open(TICKERS):
    pairs=[line.strip() + PAIR_WITH for line in open(TICKERS)] 
  
  while True:
    print(f'SignalMACD: Analyzing {len(pairs)} coins')
    buy_signal_coins, sell_signal_coins, sl_signal_coins, failed_coins = analyze(pairs)
    
    # record all coins that failed weekly macd
    write_failed_coins(failed_coins)
    if FULL_LOG:
      print(f'SignalMACD: Num buy signals {buy_signal_coins}')
      print(f'SignalMACD: Num sell signals {sell_signal_coins}')
      print(f'SignalMACD: Num stop loss signals {sl_signal_coins}')
    time.sleep((TIME_TO_WAIT*60))