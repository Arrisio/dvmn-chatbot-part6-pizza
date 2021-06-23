### Курс "Чат-боты на Python"
https://dvmn.org/modules/chat-bots/lesson/devman-bot/

## Урок 6
[Урок 6. Принимаем платежи за пиццу ](https://dvmn.org/modules/chat-bots/lesson/pizza-bot)  


## Установка

1. Клонировать репозиторий:
```
https://github.com/Arrisio/dvmn-chatbot-part6-pizza.git
```

2. Для работы клиентов нужен Python версии не ниже 3.9 и пакетный менеджер [poetry](https://python-poetry.org/docs/)
```bash
poetry install
```

3. Требуется определить следующие переменные окружения:
- `TG_BOT_TOKEN`=`Ваш токен`.
- `TG_BOT_ADMIN_ID`=`UserId админа бота в Telegram. Можно узнать у этого бота @userinfobot`
- `COURIER_TG_ID`=`UserId курьера, для отправки ему оповещений @userinfobot`
- `YANDEX_GEOCODER_APIKEY`=`API Ключ к геокодеру Яндекса`
- `PAYMENT_PROVIDER_TOKEN`=`API Ключ сервиса обработчика платежей`

Учетные данные CMS Molten(elasticpath)
- `MOLTEN_STORE_ID`
- `MOLTEN_CLIENT_ID`
- `MOLTEN_CLIENT_SECRET`


Следующие переменные окружения опциональны:
- `REDIS_HOST` - IP или hostname базы redis. По умолчанию - `localhost`.  
- `REDIS_PORT` - порт базы redis. По умолчанию - `6379`.  
- `REDIS_DB` - Индекс базы redis. По умолчанию None.
- `REDIS_PASSWORD` - Пароль к редису. По умолчанию не требуется  
  

## Запуск
```
python3 main.py
```

