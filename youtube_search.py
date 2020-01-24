#!/usr/bin/python

# Copyright (c) 2020, Andrei Buhaiu
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The name of the Andrei Buhaiu may not be used to endorse or promote
#       products derived from this software without specific prior written
#       permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL ANDREI BUHAIU BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
from parse import *
from datetime import datetime, date, time
import subprocess
import time
import re


p_apikey = subprocess.Popen(["xmlstarlet", "sel", "-T", "-t",
        "-m", "/config/youtube_api_data/developer_key", "-v", ".", "-n",
        "config.xml"],
        stdout = subprocess.PIPE)
# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = p_apikey.communicate()[0][:-1]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
  developerKey=DEVELOPER_KEY)

def BuildBGGGeeklistItem(videoId, videoTitle, videoDate):
    print "----------------------------------------"
    print videoTitle
    print "----------------------------------------"
    print "[size=18][b][u]Added %s[/u][/b][/size]\n" % videoDate
    print "[youtube=%s]" % videoId
    print "----------------------------------------\n"


def GetYoutubeUploadsPlaylistByUsername(username):

  results = youtube.channels().list(
    part = "contentDetails",
    forUsername = username,
  ).execute()

  uploadsPlaylist = results["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

  print "Uploads playlist is '%s'" % (uploadsPlaylist)
  return uploadsPlaylist

def GetYoutubeUploadsPlaylistByChannelId(channelId):

  results = youtube.channels().list(
    part = "contentDetails",
    id = channelId,
  ).execute()

  uploadsPlaylist = results["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

  print "Uploads playlist is '%s'" % (uploadsPlaylist)
  return uploadsPlaylist


def GetYoutubeVideosFromPlaylist(playlistId, headerEntriesMax,
    stripTitle = False):

    results = youtube.playlistItems().list(
            part = "contentDetails",
            playlistId = playlistId,
            maxResults = 50,
    ).execute()

    headerLastAdded = ""
    headerEntries = 0

    uploads = results["items"]
    uploadsDict = {}

    # Create a dictionary that contains the information in the youtube video
    # feed. The key is a pair comprising the title of the video and the video
    # id, the value is the date the video was published on.
    for uploadItem in uploads:
        videoId = uploadItem["contentDetails"]["videoId"]
        upload = youtube.videos().list(
                part = "snippet",
                id = videoId,
            ).execute()
        title = unicode(upload["items"][0]["snippet"]["title"]).encode("utf8")
        if stripTitle :
            match = re.match(r'(Daily Game Unboxing *- *)(.*)$', title)
            if match :
                title = match.group(2)
        date = upload["items"][0]["snippet"]["publishedAt"]
        videoDate = parse('{:ti}', date)[0]
        key = (title, videoId)
        uploadsDict[key] = videoDate

    # Ask the user which of the videos in the video feed he wants to add to
    # the geeklist.
    for entry in sorted(uploadsDict.items(), key=lambda x: x[1], reverse=True):
        (title, videoId), date = entry
        USVideoDate = date.strftime("%m/%d/%y")
        BuildBGGGeeklistItem(videoId, title, USVideoDate)
        try:
            cont=raw_input('Add current video?[(A)dd/(s)kip/(e)xit]')
        except ValueError:
                print "Not a character"
        if cont == "e":
            # Done adding entries
            break
        if cont != "s":
            # Add the current entry if the use didn't select 's' for skip
            headerLastAdded += "[listitem=]{0}[/listitem] - {1}\n\n".format(title,
                USVideoDate)
            headerEntries += 1
            print "Header entries left ", headerEntriesMax - headerEntries
            # If we reached the maximum number of allowed header entries exit
            if headerEntries == headerEntriesMax:
                break

    return (headerEntries, headerLastAdded)

if __name__ == "__main__":

    p_user = subprocess.Popen(["xmlstarlet", "sel", "-T", "-t",
            "-m", "/config/default_youtube_channel_user", "-v", ".", "-n",
            "config.xml"],
            stdout = subprocess.PIPE)

    p_geeklistid = subprocess.Popen(["xmlstarlet", "sel", "-T", "-t",
            "-m", "/config/default_geeklistid", "-v", ".", "-n",
            "config.xml"],
            stdout = subprocess.PIPE)

    # The username of the channel is used if not channel id is passed by the
    # user as a parameter.
    argparser.add_argument("-u", help="Youtube user",
        default = p_user.communicate()[0][:-1])
    argparser.add_argument("-c", help="Youtube channel id", default="")
    argparser.add_argument("-p", help="Youtube playlist id", default="")

    argparser.add_argument("-g", help="boardgamegeek geeklist id",
            default = p_geeklistid.communicate()[0][:-1])
    argparser.add_argument("--max-header-entries",
        help="Maximum header entries", default=20)
    argparser.add_argument("--append",
        help="Append instead of replacing entries",
        action='store_true')
    argparser.add_argument("-s",
        help="Strip title",
        action='store_true')
    argparser.add_argument("--autoretry",
        help="Auto retry fetching geeklist when it fails",
        action='store_true')
    args = argparser.parse_args()
    channelId = args.c
    userId = args.u
    playlistId = args.p
    geeklistId = args.g

    print args
    if playlistId:
        try:
            (nr_entries, header_entries) = GetYoutubeVideosFromPlaylist(playlistId,
                args.max_header_entries, args.s)
        except HttpError, e:
            print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
    else :
        if not channelId:
            try:
                uploadsPlaylist = GetYoutubeUploadsPlaylistByUsername(userId)
            except HttpError, e:
                print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
        else:
            try:
                uploadsPlaylist = GetYoutubeUploadsPlaylistByChannelId(channelId)
            except HttpError, e:
                print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

        try:
            (nr_entries, header_entries) = GetYoutubeVideosFromPlaylist(uploadsPlaylist,
                args.max_header_entries, args.s)
        except HttpError, e:
            print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

    # Fetch geeklist from boardgamegeek.com
    count = 0
    while True:
        subprocess.call(["rm", "-f", "geeklist.xml"])
        subprocess.call(["wget", "-O", "geeklist.xml",
             "https://www.boardgamegeek.com/xmlapi2/geeklist/" +
                geeklistId + "?comments=0"])
        if not 'Please try again later for access.' in \
            open('geeklist.xml').read():
            break
        count += 1
        print "Try #" + str(count) + " failed"
        if args.autoretry is False:
            try:
                cont=raw_input('Retry fetching geeklist?[(Y)es/(n)o]')
            except ValueError:
                    print "Not a character"
            if cont == "n":
                # Abandon all hope, quit trying to fetch the geeklist
                quit()

    subprocess.call(["dos2unix", "geeklist.xml"])

    # Extract description from geeklist.xml
    p_description = subprocess.Popen(["xmlstarlet", "sel", "-T", "-t",
            "-m", "/geeklist/description", "-v", ".", "-n", "geeklist.xml"],
            stdout = subprocess.PIPE)

    if args.append is False:
        # If we don't have to append we eliminate nr_entries entries from the
        # top of the list of 20 most recent videos to make room for the new
        # entries.
        p_head = subprocess.Popen(["head", "-n", "-" + str(nr_entries * 2)],
                stdin = p_description.stdout, stdout = subprocess.PIPE)
        p_description.stdout.close()
        description = p_head.communicate()[0]
    else:
        # If we want to append to the list of most recent videos do not remove
        # anything from the description.
        description = p_description.communicate()[0]

    # Extract all the geeklist items ids from the geeklist
    ids = subprocess.check_output(["xmlstarlet", "sel", "-T", "-t",
            "-m", "/geeklist/item/@id", "-v", ".", "-n", "geeklist.xml"])

    # Extract only last nr_entries geeklist items ids
    p_ids = subprocess.Popen(["echo", "-n", ids], stdout = subprocess.PIPE)
    p_tail = subprocess.Popen(["tail", "-n", str(nr_entries)], stdin = p_ids.stdout,
        stdout = subprocess.PIPE)
    p_ids.stdout.close()
    last_ids = p_tail.communicate()[0]
    # Remove extra newline entry
    last_ids = last_ids[:-1]

    # Create new set of header entries to be added to the description
    for geeklistitem_id in reversed(last_ids.split("\n")):
        insert_pos = header_entries.find("[listitem=]")
        header_entries = header_entries[:insert_pos + 10] + geeklistitem_id + header_entries[insert_pos + 10:]

    # Insert the new set at the top of the latest 20 videos list in the header
    insert_pos = description.find("\n\n\n") + 3
    print description[:insert_pos:] + header_entries + description[insert_pos:]
