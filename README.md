# Telegram Banking Bot

This repository contains the code for a Telegram bot that simulates a basic banking application, utilizing Python and MongoDB as a backend. The aim of this project is to demonstrate functionality, usability, and the integrity of the described operation flow.

## Proposed Future Enhancements
- **Email Validation for PayPal**: Implement validators to ensure that PayPal email addresses are valid before adding them as deposit methods.
- **Crypto Wallet Address Validation**: Add validators for crypto wallet addresses (BTC, ETH, USDT) to ensure they are correct before accepting them as a deposit or withdrawal method.

## Features

### Bot Commands
- `/start`: Initiates interaction with the bot, presenting inline buttons for:
  - **Check Balance**
  - **Deposit**
  - **Withdraw**

#### Check Balance
Displays the user's current balance, starting at 0.

#### Deposit
A multi-step process for depositing money:
1. Asks for the deposit amount and validates it as an integer greater than 0.
2. Choice of deposit method from already added methods or add a new one.
3. Confirmation of the deposit with options to "Confirm" or "Cancel".

#### Withdraw
Operates like deposit, but the amount to be withdrawn must be less than the available balance.

#### Add New Method
Can be selected from the Deposit or Withdrawal menu:
- **Bank Transfer**: Requests the name of the bank.
- **PayPal**: Requests the PayPal email address.
- **Crypto**: Choose between BTC, ETH, or USDT and requests the wallet address.

### Debug Features
- `/debug_restart`: Completely restarts the Python process to test state persistence.
- `/debug_uptime`: Displays the running time of the bot.

## Access the Bot
You can access and interact with the Telegram bot using the following link: [MongoTelegramBot](https://t.me/MongoTelegrambot).

## Repository
The source code for this project can be found at [code_challenge_telegram_bot](https://github.com/igorcodigo/code_challenge_telegram_bot).

## How to Run the Bot
Detailed instructions for setting up and running the bot locally, including setting up the Python environment, installing dependencies, and configuring MongoDB.

### Prerequisites
- Python 3.8+
- MongoDB
- Python Libraries: `pyTelegramBotAPI`, `pymongo`

### Setup
1. Clone the repository: `git clone https://github.com/igorcodigo/code_challenge_telegram_bot`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up the necessary environment variables (Bot TOKEN, MongoDB URI).
4. Run the bot: `python bot.py`

This document serves as an overview and guide for setting up and testing the Telegram banking simulation bot.
