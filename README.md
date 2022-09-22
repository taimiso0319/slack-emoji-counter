This tool helps to collect all chat reactions from all public channels including archived.

## Requirements

Python packages
```
pip install dotenv
pip install slack_sdk
```

Slack permissions
```
channels:history
channels:read
emoji:read
reactions:read
users:read
```

Copy .env.example as .env, thenwrite Slack User OAuth Token to SLACK_API_TOKEN


## Usage
```
python main.py
```
to collect channels and chat reactions.
Channel list will be stored as "channels/channel_list.json".
Chat reactions will be stored as "chats/{id}.json"
Channles that has errors duaring collecting will be stored as "channels/channel_error_list.json"


|Option|Detail|
|----|----|
|-h, --help|Show helps|
|--get-public-channels|Listing up all public channels.|
|-e, --emoji|Outpu all custom emojis as emoji-custom.csv|
|-t, --totalize|Totalize all chat reactions.|
|-l, --limit NUM|Limit API requests (1 - 1000). Default is 200|
|--try-errors|Retry channels that had error and ignored.|