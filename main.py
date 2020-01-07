#!/usr/bin/python

import os
import sys

sys.path.append("./packages")
from oauth2client.tools import argparser
from apiclient.errors import HttpError
from apiclient.discovery import build
import re
import requests
import random
import json

DEVELOPER_KEY = os.environ["DEVELOPER_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
CHANNEL_ID = "UCZx7esGXyW6JXn98byfKEIA"
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

youtube = build(YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                developerKey=DEVELOPER_KEY)

VIDEOS = []


def get_random_video(page_token):
    # チャンネルの情報を取得
    response = (youtube.search().list(part="snippet",
                                      channelId=CHANNEL_ID,
                                      maxResults=50,
                                      pageToken=page_token).execute())

    # 結果から動画IDを配列に格納
    for result in response.get("items", []):
        if result["id"]["kind"] == "youtube#video":
            VIDEOS.append(result["id"]["videoId"])

    # nextPageTokenがある時は再帰的に実行
    try:
        next_page_token = response["nextPageToken"]
        get_random_video(next_page_token)
    except:
        print("VIDEOS:", VIDEOS)
        # ランダムで動画を選択して、IDを返す
        video_id = random.choice(VIDEOS)

        print("CHOICE_VIDEO_ID:", video_id)
        return get_video_info(video_id)


def get_video_info(video_id):
    # 動画の情報を取得
    response = youtube.videos().list(part="snippet, statistics",
                                     id=video_id).execute()

    print("RESPONSE:", response)
    return create_message(response)


def create_message(response):
    snippet = response["items"][0]["snippet"]
    statistics = response["items"][0]["statistics"]

    # メッセージ作成に必要な値を取得
    video_id = response["items"][0]["id"]
    title = snippet["title"]
    day = snippet["publishedAt"]
    day = day[0:10]
    description = snippet["description"]
    member = re.findall(r"(.*?)\n【Twitter】", description)
    member = list(map(lambda x: ({"value": x, "short": True}), member))
    view = "{:,}".format(int(statistics["viewCount"]))
    rate = [statistics["likeCount"], statistics["dislikeCount"]]
    url = "https://www.youtube.com/watch?v=" + video_id
    image = snippet["thumbnails"]["maxres"]["url"]

    # メッセージ作成
    context = {
        "attachments": [
            {
                "pretext": "今日のおすすめ",
                "title": title,
                "title_link": url,
                "text": url,
                "color": "#7CD197",
                "image_url": image,
            },
            {
                "title": "Member",
                "fields": member,
                "color": "#764FA5"
            },
            {
                "fallback":
                f"{title} {url}",
                "text":
                "",
                "fields": [
                    {
                        "title": "投稿日",
                        "value": day,
                        "short": True
                    },
                    {
                        "title": "再生回数",
                        "value": view,
                        "short": True
                    },
                    {
                        "title": "高評価",
                        "value": rate[0],
                        "short": True
                    },
                    {
                        "title": "低評価",
                        "value": rate[1],
                        "short": True
                    },
                ],
            },
        ]
    }

    print("MESSAGE:", context)
    return post_slack(context)


def post_slack(context):
    payload = context
    data = json.dumps(payload)
    # slackに投稿
    response = requests.post(WEBHOOK_URL, data)
    if response.status_code == 200:
        print("投稿完了")
    else:
        print("投稿失敗")


if __name__ == "__main__":
    try:
        get_random_video(page_token="")
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
