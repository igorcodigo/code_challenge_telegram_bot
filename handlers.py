from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler, ContextTypes, Application
)
from datetime import datetime
import subprocess
import sys


# Defining states for the ConversationHandler
(
    MAIN_MENU, DEPOSIT_AMOUNT, SELECT_DEPOSIT_METHOD, ADD_DEPOSIT_METHOD_TYPE,
    ADD_DEPOSIT_METHOD_DETAILS, CONFIRM_DEPOSIT,
    WITHDRAW_AMOUNT, SELECT_WITHDRAWAL_METHOD, ADD_WITHDRAWAL_METHOD_TYPE,
    ADD_WITHDRAWAL_METHOD_DETAILS, CONFIRM_WITHDRAWAL
) = range(11)


def setup_handlers(application: Application, users_collection, settings_collection):
    # Store the users collection in the application context
    application.bot_data['users_collection'] = users_collection
    application.bot_data['settings_collection'] = settings_collection

    # Define the ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(main_menu)],
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
            SELECT_DEPOSIT_METHOD: [CallbackQueryHandler(select_deposit_method)],
            ADD_DEPOSIT_METHOD_TYPE: [CallbackQueryHandler(add_deposit_method_type)],
            ADD_DEPOSIT_METHOD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_deposit_method_details)],
            CONFIRM_DEPOSIT: [CallbackQueryHandler(confirm_deposit)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            SELECT_WITHDRAWAL_METHOD: [CallbackQueryHandler(select_withdrawal_method)],
            ADD_WITHDRAWAL_METHOD_TYPE: [CallbackQueryHandler(add_withdrawal_method_type)],
            ADD_WITHDRAWAL_METHOD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_withdrawal_method_details)],
            CONFIRM_WITHDRAWAL: [CallbackQueryHandler(confirm_withdrawal)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],
        allow_reentry=True
    )

    # Add the ConversationHandler to the application
    application.add_handler(conv_handler)

    # Add handler for the /debug_uptime command
    application.add_handler(CommandHandler('debug_uptime', debug_uptime))

    # Add handler for the /debug_restart command
    application.add_handler(CommandHandler('debug_restart', debug_restart))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if not user:
        # Initialize user data
        users_collection.insert_one({
            'user_id': user_id,
            'balance': 0,
            'deposit_methods': [],
            'withdrawal_methods': [],
            'state': MAIN_MENU,
            'temp_data': {}
        })
    else:
        # Update the user's document if fields are missing
        update_fields = {}
        if 'deposit_methods' not in user:
            update_fields['deposit_methods'] = []
        if 'withdrawal_methods' not in user:
            update_fields['withdrawal_methods'] = []
        if 'state' not in user:
            update_fields['state'] = MAIN_MENU
        if 'temp_data' not in user:
            update_fields['temp_data'] = {}
        if update_fields:
            users_collection.update_one({'user_id': user_id}, {'$set': update_fields})
            user.update(update_fields)

        # Check if there is a saved state to resume
        state = user.get('state', MAIN_MENU)
        if state != MAIN_MENU:
            await update.message.reply_text('Let\'s resume where we left off.')
            return await resume_flow(update, context, user)

    await show_main_menu(update, context)
    return MAIN_MENU


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("View Balance", callback_data='view_balance')],
        [InlineKeyboardButton("Deposit", callback_data='deposit')],
        [InlineKeyboardButton("Withdraw", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('Please choose an option:', reply_markup=reply_markup)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if query.data == 'view_balance':
        balance = user['balance']
        await query.edit_message_text(f'Your current balance is: ${balance}')
        await show_main_menu(update, context)
        return MAIN_MENU

    elif query.data == 'deposit':
        await query.edit_message_text('How much would you like to deposit? \n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': DEPOSIT_AMOUNT}})
        return DEPOSIT_AMOUNT

    elif query.data == 'withdraw':
        await query.edit_message_text('How much would you like to withdraw? \n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': WITHDRAW_AMOUNT}})
        return WITHDRAW_AMOUNT


# ------------------ Deposit-Related Functions ------------------

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    value_text = update.message.text.strip().lower()
    users_collection = context.application.bot_data['users_collection']

    # Check if the user wants to cancel
    if value_text == 'cancel' or value_text == '0':
        await update.message.reply_text('Deposit canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    if value_text.isdigit() and int(value_text) > 0:
        value = int(value_text)
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.transaction_value': value}})

        # Retrieve user's deposit methods
        user = users_collection.find_one({'user_id': user_id})
        methods = user['deposit_methods']

        keyboard = [[InlineKeyboardButton(m['description'], callback_data=f"deposit_method_{idx}")] for idx, m in enumerate(methods)]
        keyboard.append([InlineKeyboardButton("Add New Method", callback_data='add_deposit_method')])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text('Select a deposit method:', reply_markup=reply_markup)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': SELECT_DEPOSIT_METHOD}})
        return SELECT_DEPOSIT_METHOD
    else:
        await update.message.reply_text('Please enter a valid amount greater than zero or "cancel" to cancel.')
        return DEPOSIT_AMOUNT


async def select_deposit_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if query.data == 'cancel':
        await query.edit_message_text('Deposit canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    if query.data.startswith('deposit_method_'):
        idx = int(query.data.split('_')[-1])
        method = user['deposit_methods'][idx]
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.selected_method': method}})
        value = user['temp_data']['transaction_value']
        await query.edit_message_text(f"Confirm the deposit of ${value} via {method['description']}.")

        keyboard = [
            [InlineKeyboardButton("Confirm", callback_data='confirm_deposit')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': CONFIRM_DEPOSIT}})
        return CONFIRM_DEPOSIT

    elif query.data == 'add_deposit_method':
        await query.edit_message_text('Select the type of method you wish to add:')
        keyboard = [
            [InlineKeyboardButton("Bank Transfer", callback_data='type_bank_deposit')],
            [InlineKeyboardButton("Paypal", callback_data='type_paypal_deposit')],
            [InlineKeyboardButton("Crypto", callback_data='type_crypto_deposit')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_deposit_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_DEPOSIT_METHOD_TYPE}})
        await query.message.reply_text('Choose the method type:', reply_markup=reply_markup)
        return ADD_DEPOSIT_METHOD_TYPE


async def add_deposit_method_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']

    if query.data == 'cancel_add_deposit_method':
        await query.edit_message_text('Adding method canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': SELECT_DEPOSIT_METHOD}})
        # Return to method selection
        await resume_flow(update, context, users_collection.find_one({'user_id': user_id}))
        return SELECT_DEPOSIT_METHOD

    if query.data == 'type_bank_deposit':
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': 'Bank'}})
        await query.message.reply_text('Please provide the bank name:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_DEPOSIT_METHOD_DETAILS}})
        return ADD_DEPOSIT_METHOD_DETAILS

    elif query.data == 'type_paypal_deposit':
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': 'Paypal'}})
        await query.message.reply_text('Please provide your Paypal email:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_DEPOSIT_METHOD_DETAILS}})
        return ADD_DEPOSIT_METHOD_DETAILS

    elif query.data == 'type_crypto_deposit':
        keyboard = [
            [InlineKeyboardButton("BTC", callback_data='crypto_BTC_deposit')],
            [InlineKeyboardButton("ETH", callback_data='crypto_ETH_deposit')],
            [InlineKeyboardButton("USDT", callback_data='crypto_USDT_deposit')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_deposit_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Select the cryptocurrency:', reply_markup=reply_markup)
        return ADD_DEPOSIT_METHOD_TYPE

    elif query.data.startswith('crypto_') and query.data.endswith('_deposit'):
        crypto = query.data.split('_')[1]
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': f'Crypto ({crypto})'}})
        await query.message.reply_text(f'Please provide your {crypto} address:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_DEPOSIT_METHOD_DETAILS}})
        return ADD_DEPOSIT_METHOD_DETAILS


async def add_deposit_method_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    detail = update.message.text.strip().lower()
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})
    method_type = user['temp_data']['new_method_type']

    if detail == 'cancel' or detail == '0':
        await update.message.reply_text('Adding method canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    new_method = {
        'type': method_type,
        'detail': detail,
        'description': f"{method_type}: {detail}"
    }

    users_collection.update_one({'user_id': user_id}, {'$push': {'deposit_methods': new_method}})
    await update.message.reply_text(f"Method {method_type} added successfully!")

    # Continue the deposit flow
    users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.selected_method': new_method}})
    value = user['temp_data']['transaction_value']
    await update.message.reply_text(f"Confirm the deposit of ${value} via {new_method['description']}.")

    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data='confirm_deposit')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    users_collection.update_one({'user_id': user_id}, {'$set': {'state': CONFIRM_DEPOSIT}})
    await update.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
    return CONFIRM_DEPOSIT


async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if query.data == 'confirm_deposit':
        value = user['temp_data']['transaction_value']
        users_collection.update_one({'user_id': user_id}, {'$inc': {'balance': value}})
        await query.edit_message_text(f"Deposit of ${value} completed successfully!")
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    elif query.data == 'cancel':
        await query.edit_message_text("Deposit canceled.")
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU


# ------------------ Withdrawal-Related Functions ------------------

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    value_text = update.message.text.strip().lower()
    users_collection = context.application.bot_data['users_collection']

    # Check if the user wants to cancel
    if value_text == 'cancel' or value_text == '0':
        await update.message.reply_text('Withdrawal canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    if value_text.isdigit() and int(value_text) > 0:
        value = int(value_text)
        user = users_collection.find_one({'user_id': user_id})
        balance = user['balance']

        if value > balance:
            await update.message.reply_text(
                f"You don't have sufficient balance. Your current balance is ${balance}.\n\n"
                'Please enter an amount less than or equal to your balance or type "cancel" or "0" to cancel.'
            )
            return WITHDRAW_AMOUNT

        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.transaction_value': value}})

        # Retrieve user's withdrawal methods
        methods = user.get('withdrawal_methods', [])

        keyboard = [[InlineKeyboardButton(m['description'], callback_data=f"withdrawal_method_{idx}")] for idx, m in enumerate(methods)]
        keyboard.append([InlineKeyboardButton("Add New Method", callback_data='add_withdrawal_method')])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text('Select a withdrawal method:', reply_markup=reply_markup)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': SELECT_WITHDRAWAL_METHOD}})
        return SELECT_WITHDRAWAL_METHOD
    else:
        await update.message.reply_text(
            'Please enter a valid amount greater than zero or "cancel" to cancel.'
        )
        return WITHDRAW_AMOUNT


async def select_withdrawal_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if query.data == 'cancel':
        await query.edit_message_text('Withdrawal canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    if query.data.startswith('withdrawal_method_'):
        idx = int(query.data.split('_')[-1])
        method = user['withdrawal_methods'][idx]
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.selected_method': method}})
        value = user['temp_data']['transaction_value']
        await query.edit_message_text(f"Confirm the withdrawal of ${value} via {method['description']}.")

        keyboard = [
            [InlineKeyboardButton("Confirm", callback_data='confirm_withdrawal')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': CONFIRM_WITHDRAWAL}})
        return CONFIRM_WITHDRAWAL

    elif query.data == 'add_withdrawal_method':
        await query.edit_message_text('Select the type of method you wish to add:')
        keyboard = [
            [InlineKeyboardButton("Bank Transfer", callback_data='type_bank_withdrawal')],
            [InlineKeyboardButton("Paypal", callback_data='type_paypal_withdrawal')],
            [InlineKeyboardButton("Crypto", callback_data='type_crypto_withdrawal')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_withdrawal_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_WITHDRAWAL_METHOD_TYPE}})
        await query.message.reply_text('Choose the method type:', reply_markup=reply_markup)
        return ADD_WITHDRAWAL_METHOD_TYPE


async def add_withdrawal_method_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']

    if query.data == 'cancel_add_withdrawal_method':
        await query.edit_message_text('Adding method canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': SELECT_WITHDRAWAL_METHOD}})
        # Return to method selection
        await resume_flow(update, context, users_collection.find_one({'user_id': user_id}))
        return SELECT_WITHDRAWAL_METHOD

    if query.data == 'type_bank_withdrawal':
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': 'Bank'}})
        await query.message.reply_text('Please provide the bank name for withdrawal:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_WITHDRAWAL_METHOD_DETAILS}})
        return ADD_WITHDRAWAL_METHOD_DETAILS

    elif query.data == 'type_paypal_withdrawal':
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': 'Paypal'}})
        await query.message.reply_text('Please provide your Paypal email for withdrawal:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_WITHDRAWAL_METHOD_DETAILS}})
        return ADD_WITHDRAWAL_METHOD_DETAILS

    elif query.data == 'type_crypto_withdrawal':
        keyboard = [
            [InlineKeyboardButton("BTC", callback_data='crypto_BTC_withdrawal')],
            [InlineKeyboardButton("ETH", callback_data='crypto_ETH_withdrawal')],
            [InlineKeyboardButton("USDT", callback_data='crypto_USDT_withdrawal')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_withdrawal_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Select the cryptocurrency:', reply_markup=reply_markup)
        return ADD_WITHDRAWAL_METHOD_TYPE

    elif query.data.startswith('crypto_') and query.data.endswith('_withdrawal'):
        crypto = query.data.split('_')[1]
        users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.new_method_type': f'Crypto ({crypto})'}})
        await query.message.reply_text(f'Please provide your {crypto} address for withdrawal:\n(Type "cancel" or "0" to cancel)')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': ADD_WITHDRAWAL_METHOD_DETAILS}})
        return ADD_WITHDRAWAL_METHOD_DETAILS


async def add_withdrawal_method_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    detail = update.message.text.strip().lower()
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})
    method_type = user['temp_data']['new_method_type']

    if detail == 'cancel' or detail == '0':
        await update.message.reply_text('Adding method canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    new_method = {
        'type': method_type,
        'detail': detail,
        'description': f"{method_type}: {detail}"
    }

    users_collection.update_one({'user_id': user_id}, {'$push': {'withdrawal_methods': new_method}})
    await update.message.reply_text(f"Method {method_type} added successfully!")

    # Continue the withdrawal flow
    users_collection.update_one({'user_id': user_id}, {'$set': {'temp_data.selected_method': new_method}})
    value = user['temp_data']['transaction_value']
    await update.message.reply_text(f"Confirm the withdrawal of ${value} via {new_method['description']}.")

    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data='confirm_withdrawal')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    users_collection.update_one({'user_id': user_id}, {'$set': {'state': CONFIRM_WITHDRAWAL}})
    await update.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
    return CONFIRM_WITHDRAWAL


async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})

    if query.data == 'confirm_withdrawal':
        value = user['temp_data']['transaction_value']
        users_collection.update_one({'user_id': user_id}, {'$inc': {'balance': -value}})
        await query.edit_message_text(f"Withdrawal of ${value} completed successfully!")
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    elif query.data == 'cancel':
        await query.edit_message_text("Withdrawal canceled.")
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU


# ------------------ Common Functions ------------------

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_collection = context.application.bot_data['users_collection']
    user = users_collection.find_one({'user_id': user_id})
    state = user.get('state', MAIN_MENU)

    # Check if the user typed 'cancel' at any stage
    if update.message.text.strip().lower() == 'cancel':
        await update.message.reply_text('Operation canceled.')
        users_collection.update_one({'user_id': user_id}, {'$set': {'state': MAIN_MENU, 'temp_data': {}}})
        await show_main_menu(update, context)
        return MAIN_MENU

    if state == DEPOSIT_AMOUNT:
        return await deposit_amount(update, context)
    elif state == ADD_DEPOSIT_METHOD_DETAILS:
        return await add_deposit_method_details(update, context)
    elif state == WITHDRAW_AMOUNT:
        return await withdraw_amount(update, context)
    elif state == ADD_WITHDRAWAL_METHOD_DETAILS:
        return await add_withdrawal_method_details(update, context)
    else:
        await update.message.reply_text("Let's resume where we left off.")
        return await resume_flow(update, context, user)


async def resume_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    state = user.get('state', MAIN_MENU)
    user_id = user['user_id']
    users_collection = context.application.bot_data['users_collection']

    if state == MAIN_MENU:
        await show_main_menu(update, context)
        return MAIN_MENU

    elif state == DEPOSIT_AMOUNT:
        await update.message.reply_text('How much would you like to deposit? \n(Type "cancel" or "0" to cancel)')
        return DEPOSIT_AMOUNT

    elif state == SELECT_DEPOSIT_METHOD:
        methods = user['deposit_methods']
        keyboard = [[InlineKeyboardButton(m['description'], callback_data=f"deposit_method_{idx}")] for idx, m in enumerate(methods)]
        keyboard.append([InlineKeyboardButton("Add New Method", callback_data='add_deposit_method')])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Select a deposit method:', reply_markup=reply_markup)
        return SELECT_DEPOSIT_METHOD

    elif state == ADD_DEPOSIT_METHOD_TYPE:
        keyboard = [
            [InlineKeyboardButton("Bank Transfer", callback_data='type_bank_deposit')],
            [InlineKeyboardButton("Paypal", callback_data='type_paypal_deposit')],
            [InlineKeyboardButton("Crypto", callback_data='type_crypto_deposit')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_deposit_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Choose the method type:', reply_markup=reply_markup)
        return ADD_DEPOSIT_METHOD_TYPE

    elif state == ADD_DEPOSIT_METHOD_DETAILS:
        method_type = user['temp_data']['new_method_type']
        if 'Crypto' in method_type:
            crypto = method_type.split('(')[1].strip(')')
            await update.message.reply_text(f'Please provide your {crypto} address:')
        elif method_type == 'Paypal':
            await update.message.reply_text('Please provide your Paypal email:')
        elif method_type == 'Bank':
            await update.message.reply_text('Please provide the bank name:')
        return ADD_DEPOSIT_METHOD_DETAILS

    elif state == CONFIRM_DEPOSIT:
        value = user['temp_data']['transaction_value']
        method = user['temp_data']['selected_method']
        await update.message.reply_text(f"Confirm the deposit of ${value} via {method['description']}.")

        keyboard = [
            [InlineKeyboardButton("Confirm", callback_data='confirm_deposit')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
        return CONFIRM_DEPOSIT

    elif state == WITHDRAW_AMOUNT:
        await update.message.reply_text('How much would you like to withdraw? \n(Type "cancel" or "0" to cancel)')
        return WITHDRAW_AMOUNT

    elif state == SELECT_WITHDRAWAL_METHOD:
        methods = user['withdrawal_methods']
        keyboard = [[InlineKeyboardButton(m['description'], callback_data=f"withdrawal_method_{idx}")] for idx, m in enumerate(methods)]
        keyboard.append([InlineKeyboardButton("Add New Method", callback_data='add_withdrawal_method')])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Select a withdrawal method:', reply_markup=reply_markup)
        return SELECT_WITHDRAWAL_METHOD

    elif state == ADD_WITHDRAWAL_METHOD_TYPE:
        keyboard = [
            [InlineKeyboardButton("Bank Transfer", callback_data='type_bank_withdrawal')],
            [InlineKeyboardButton("Paypal", callback_data='type_paypal_withdrawal')],
            [InlineKeyboardButton("Crypto", callback_data='type_crypto_withdrawal')],
            [InlineKeyboardButton("Cancel", callback_data='cancel_add_withdrawal_method')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Choose the method type:', reply_markup=reply_markup)
        return ADD_WITHDRAWAL_METHOD_TYPE

    elif state == ADD_WITHDRAWAL_METHOD_DETAILS:
        method_type = user['temp_data']['new_method_type']
        if 'Crypto' in method_type:
            crypto = method_type.split('(')[1].strip(')')
            await update.message.reply_text(f'Please provide your {crypto} address for withdrawal:')
        elif method_type == 'Paypal':
            await update.message.reply_text('Please provide your Paypal email for withdrawal:')
        elif method_type == 'Bank':
            await update.message.reply_text('Please provide the bank name for withdrawal:')
        return ADD_WITHDRAWAL_METHOD_DETAILS

    elif state == CONFIRM_WITHDRAWAL:
        value = user['temp_data']['transaction_value']
        method = user['temp_data']['selected_method']
        await update.message.reply_text(f"Confirm the withdrawal of ${value} via {method['description']}.")

        keyboard = [
            [InlineKeyboardButton("Confirm", callback_data='confirm_withdrawal')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Do you wish to confirm?', reply_markup=reply_markup)
        return CONFIRM_WITHDRAWAL


async def debug_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds with the uptime of the bot."""
    start_time = context.application.bot_data.get('start_time')
    if start_time:
        uptime = datetime.now() - start_time
        uptime_seconds = int(uptime.total_seconds())
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours} hours, {minutes} minutes, and {seconds} seconds"
        await update.message.reply_text(f"The bot has been running for {uptime_str}.")
    else:
        await update.message.reply_text("Unable to determine the bot's uptime.")

async def debug_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restarts the bot by executing an external script."""

    await update.message.reply_text("Restarting the bot...")

    # Stores the chat ID to send a message after restarting
    chat_id = update.effective_chat.id
    context.application.bot_data['restart_chat_id'] = chat_id
    print(chat_id)

    # Accesses the settings_collection from bot_data
    settings_collection = context.bot_data['settings_collection']

    # Stores the chat ID in MongoDB to send a message after restarting
    chat_id = update.effective_chat.id
    settings_collection.update_one(
        {'key': 'restart_chat_id'},
        {'$set': {'value': chat_id}},
        upsert=True
    )

    # Executes the external script to restart the bot
    script_path = 'reload.py'

    def restart_bot():
        subprocess.Popen([sys.executable, script_path])
        print(chat_id)
        # Terminates the current process
        sys.exit(0)

    # Calls the restart function
    restart_bot()