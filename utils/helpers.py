def get_tg_payload(chat_id, message_text, buttons: [{str: str}] = None):
    payload = {'chat_id': chat_id,
               'text': message_text, }
    if buttons:
        keyboard_buttons = []
        for button in buttons:
            for text, url in button.items():
                keyboard_buttons.append({
                    "text": text,
                    "url": url
                })
        payload['reply_markup'] = {'inline_keyboard': [keyboard_buttons]}
    return payload
