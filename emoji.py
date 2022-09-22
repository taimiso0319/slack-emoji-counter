import csv
import json

EMOJI_URL_APPLE_FORMAT = "https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{}"
EMOJI_URL_GOOGLE_FORMAT = "https://raw.githubusercontent.com/iamcal/emoji-data/master/img-google-136/{}"


def main():
    with open('emoji-all.json', 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        file.close()
    with open('emoji-all.csv', 'w', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'url'])
        for d in json_data:
            url = EMOJI_URL_APPLE_FORMAT.format(d['image'])
            if not d['has_img_apple']:
                url = EMOJI_URL_GOOGLE_FORMAT.format(d['image'])
            writer.writerow([d['short_name'], url])
        file.close()
    return


if __name__ == "__main__":
    main()
