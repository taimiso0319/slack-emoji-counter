import argparse
import csv
import glob
import json
import os
import re
import time

from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

load_dotenv()

SLACK_API_TOKEN = os.getenv('SLACK_API_TOKEN')

CHANNEL_LIST_DIRECTORY = "./channels"
CHANNEL_LIST_FILENAME = "./channel_list.json"
CHANNEL_ERROR_FILENAME = "./channel_error_list.json"
CHAT_REACTION_DIRECTORY = "./chats"
CHAT_FILENAME_FORMAT = "./{}.json"

CHANNEL_LIST_FILE_PATH = os.path.join(
    CHANNEL_LIST_DIRECTORY, CHANNEL_LIST_FILENAME)
CHANNEL_ERROR_LIST_FILE_PATH = os.path.join(
    CHANNEL_LIST_DIRECTORY, CHANNEL_ERROR_FILENAME)

CUSTOM_EMOJI_FILENAME = "./emoji-custom.csv"


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--get-public-channels",
        help="Get all channels again.",
        action="store_true")
    parser.add_argument(
        "-t", "--totalize",
        help="Totalize collected data",
        action="store_true")
    parser.add_argument(
        "--try-errors",
        help="Try to collect data on channel that had error.",
        action="store_true")
    parser.add_argument(
        "-e", "--emoji",
        help="Get all custom emojis",
        action="store_true")
    parser.add_argument(
        "-l", "--limit",
        help="Number of limit for API requests.",
        type=int,
        default=200)
    args = parser.parse_args()
    return (args)


def get_custom_emoji(client: WebClient):
    response = client.emoji_list()
    data = response['emoji']
    with open(CUSTOM_EMOJI_FILENAME, 'w', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'url'])
        for key in data.keys():
            writer.writerow([key, data[key]])
        file.close()
    return


def main():
    args = get_args()

    create_directory()

    client = WebClient(token=SLACK_API_TOKEN, timeout=300)

    if args.totalize:
        totalize()

    if args.emoji:
        get_custom_emoji(client)

    if args.totalize or args.emoji:
        return
    limit = args.limit
    if limit < 1:
        limit = 200
    if 1000 < limit:
        limit = 1000
    error_channels = None
    if os.path.isfile(CHANNEL_ERROR_LIST_FILE_PATH):
        with open(CHANNEL_ERROR_LIST_FILE_PATH, 'r') as file:
            error_channels = []
            error_channel_ids = []
            error_channels = json.load(file)
            for channel in error_channels:
                error_channel_ids.append(channel['id'])
            file.close()

    if not os.path.isfile(CHANNEL_LIST_FILE_PATH):
        channel_data_json = collect_public_channels(client, limit)
    else:
        if args.get_public_channels:
            channel_data_json = collect_public_channels(client, limit)
        else:
            with open(CHANNEL_LIST_FILE_PATH) as file:
                channel_data_json = json.load(file)
                file.close()

    for_count = 0
    if args.try_errors:
        os.remove(CHANNEL_ERROR_LIST_FILE_PATH)
    for channel in channel_data_json:
        if not args.try_errors:
            if error_channels is not None:
                if channel['id'] in error_channel_ids:
                    continue
        file_path = os.path.join(CHAT_REACTION_DIRECTORY,
                                 CHAT_FILENAME_FORMAT.format(channel["id"]))
        if not os.path.isfile(file_path):
            collect_chat_reactions(client, channel, limit)
            for_count = for_count + 1
        if for_count > 10:
            for_count = 0
            time.sleep(5)

    return


def totalize():
    paths = glob.glob(os.path.join(CHAT_REACTION_DIRECTORY, "*"))
    total = {}
    for path in paths:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for datum in data:
                d = datum[0]
                name = re.sub("::.*", "", d['name'])
                if name not in total:
                    total[name] = d['count']
                else:
                    total[name] += d['count']
        file.close()

    with open('result.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(['index', 'name', 'count'])
        for index, key in enumerate(total.keys()):
            writer.writerow([index + 1, key, total[key]])
        file.close()
    return


def record_error(channel):
    write_data = [channel]
    if os.path.isfile(CHANNEL_ERROR_LIST_FILE_PATH):
        with open(CHANNEL_ERROR_LIST_FILE_PATH, 'r') as file:
            json_data = []
            json_data = json.load(file)
            if channel['id'] in json_data[0].values():
                file.close()
                return
            json_data.append(channel)
            write_data = json_data
            file.close()

    with open(CHANNEL_ERROR_LIST_FILE_PATH, 'w') as file:
        json.dump(write_data, file, indent=4, ensure_ascii=False)
        file.close()


def create_directory():
    if not os.path.isdir(CHANNEL_LIST_DIRECTORY):
        os.makedirs(CHANNEL_LIST_DIRECTORY)
    if not os.path.isdir(CHAT_REACTION_DIRECTORY):
        os.makedirs(CHAT_REACTION_DIRECTORY)


def collect_public_channels(slack_web_client: WebClient, limit):
    cursor = ''
    channel_list = []
    loop_count = 0
    while True:
        print("Channel collection part: "+str(loop_count))
        print("Channel cursor: "+str(cursor))
        response = slack_web_client.conversations_list(
            limit=limit, cursor=cursor, types="public_channel")
        for index, row in enumerate(response['channels']):
            dict = {
                'name': row['name'],
                'id': row['id'],
                'is_archived': row['is_archived']
            }
            channel_list.append(dict)
        cursor = response['response_metadata']['next_cursor']
        if cursor == '':
            print('Channel collection end.')
            break
        loop_count += 1
        time.sleep(5)
    json_data = json.dumps(
        channel_list, indent=4).encode().decode('unicode-escape')
    with open(CHANNEL_LIST_FILE_PATH, 'w', encoding='utf-8') as file:
        file.write(json_data)
        file.close()
    return (json_data)


def collect_chat_reactions(slack_web_client: WebClient, channel: dict, limit):
    loop_count = 0
    cursor = ''
    print("Start collection on : " + channel['name'] + " ("+channel['id']+")")
    reaction_list = []
    while True:
        print("Chat collection part: "+str(loop_count))
        print("Chat cursor: "+str(cursor))
        try:
            response = slack_web_client.conversations_history(
                limit=limit, channel=channel['id'], cursor=cursor)
        except SlackApiError as e:
            print(f"An error has occured: {e.response}")
            record_error(channel)
            return

        for index, post in enumerate(response['messages']):
            if 'reactions' in post.keys():
                reaction_list.append(post['reactions'])
        if response['response_metadata'] is None:
            print("Chat collection end.")
            time.sleep(5)
            break
        else:
            cursor = response['response_metadata']['next_cursor']
        loop_count += 1
        time.sleep(5)

    json_data = json.dumps(
        reaction_list, indent=4).encode().decode('unicode-escape')
    file_path = os.path.join(CHAT_REACTION_DIRECTORY,
                             CHAT_FILENAME_FORMAT.format(channel["id"]))
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(json_data)
        file.close()
    return


if __name__ == "__main__":
    main()
