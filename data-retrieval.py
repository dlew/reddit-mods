# This program gathers data on subreddits and their mods.
#
# This is a VERY quick-and-dirty analysis tool.  If you're
# looking for robust, elegant code then you've stumbled into
# the wrong file.

import urllib
import os
import time
from BeautifulSoup import BeautifulSoup
import cookielib, urllib2
import operator
import json
import locale
import csv

locale.setlocale(locale.LC_ALL, "")

cj = cookielib.CookieJar()
ck = cookielib.Cookie(version=0, name='over18', value='90607813b305e784a6771b1e328a4c1449f16366', port=None, port_specified=False, domain='www.reddit.com', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
cj.set_cookie(ck)
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

def get_subreddits():
	if os.path.exists("tmp.json"):
		return json.load(open("tmp.json", "r"))

	subreddits = []

	# Kick start things
	data = json.load(urllib.urlopen("http://www.reddit.com/reddits/.json"))
	subreddits, after = parse_subreddits(data)

	while len(subreddits) < 5000:
		print("Loaded %d subreddits" % len(subreddits))
		time.sleep(2) # Be nice, don't crash reddit
		data = json.load(urllib.urlopen("http://www.reddit.com/reddits/.json?after=%s" % after))
		new_subreddits, after = parse_subreddits(data)
		subreddits.extend(new_subreddits)

	json.dump(subreddits, open('tmp.json', 'w'), indent=2)

	return subreddits

def parse_subreddits(data):
	subreddits = []
	for listing in data["data"]["children"]:
		listing_data = listing["data"]
		subreddit = {
			"name": listing_data["display_name"],
			"subscribers": listing_data["subscribers"]
		}
		subreddits.append(subreddit)
	return subreddits, data["data"]["after"]

def get_all_moderators(subreddits):
	if os.path.exists("subreddits.json"):
		return json.load(open("subreddits.json", "r"))

	x = 0
	for subreddit in subreddits:
		get_moderators(subreddit)
		time.sleep(2) # Be nice, don't crash reddit

	json.dump(subreddits, open("subreddits.json", 'w'), indent=2)
	return subreddits

def get_moderators(subreddit):
	print("Loading moderator data for r/%s" % subreddit["name"])

	f = opener.open("http://www.reddit.com/r/%s/about/moderators" % subreddit['name'])
	soup = BeautifulSoup(f)
	mod_table = soup.findAll(id='moderator-table')[0]
	mods = mod_table.findAll('span', {'class': 'user'})
	modlist = []
	for mod in mods:
		modlist.append(str(mod.find('a').contents[0]))
	subreddit['moderators'] = modlist

def gather_data(subreddits):
	# Gather data on each moderator
	mods = {}
	hierarchy = {}
	for subreddit in subreddits:
		subscribers = subreddit["subscribers"]
		modlist = subreddit["moderators"]
		num_mods = len(modlist)
		for a in range(num_mods):
			mod = modlist[a]
			if mod not in mods:
				mods[mod] = {
					"subreddits": 0,
					"leader": 0,
					"despot": 0,
					"users": 0,
					"locked": 0
				}
			
			mod_data = mods[mod]
			mod_data["subreddits"] += 1
			if a == 0:
				mod_data["leader"] += 1
			if num_mods == 1:
				mod_data["despot"] += 1
			mod_data["users"] += subscribers

			# Gather hierarchy data
			if mod not in hierarchy:
				hierarchy[mod] = {}
			
			empowered = hierarchy[mod]
			
			for b in range(a + 1, num_mods):
				empowered[modlist[b]] = None

	# Gather lock data on each moderator
	checked = {}
	locked = []
	for mod in hierarchy:
		checked[mod] = None
		for slave in hierarchy[mod]:
			if slave not in checked and mod in hierarchy[slave]:
				mods[mod]["locked"] += 1
				mods[slave]["locked"] += 1
				locked.append((mod, slave))

	# Add more data to subreddits
	for subreddit in subreddits:
		modlist = subreddit["moderators"]
		locked_in_subreddit = []
		for lock in locked:
			if lock[0] in modlist and lock[1] in modlist:
				if lock[0] not in locked_in_subreddit:
					locked_in_subreddit.append(lock[0])
				if lock[1] not in locked_in_subreddit:
					locked_in_subreddit.append(lock[1])
		
		num_locked = len(locked_in_subreddit)
		subreddit["locked"] = num_locked
		for i in range(len(modlist)):
			lowest_unlocked = i
			if modlist[i] not in locked_in_subreddit:
				break
		subreddit["lowest"] = lowest_unlocked
		
		if num_locked > 0:
			lowest_unlocked = 0
			for i in range(len(modlist)):
				lowest_unlocked = i
				if modlist[i] not in locked_in_subreddit:
					break
	
	return subreddits, mods

def write_subreddit_csv(subreddits, out="subreddits.csv"):
	writer = csv.writer(open(out, 'w'))
	for subreddit in subreddits:
		num_mods = len(subreddit["moderators"])
		locked = subreddit["locked"]
		writer.writerow([subreddit["name"], subreddit["subscribers"], num_mods, locked, num_mods - locked, subreddit["lowest"]])

def write_mods_csv(mods, out="mods.csv"):
	writer = csv.writer(open(out, 'w'))
	for mod in mods.keys():
		mod_data = mods[mod]
		writer.writerow([mod, mod_data["subreddits"], mod_data["leader"], mod_data["despot"], mod_data["users"], mod_data["locked"]])

if __name__ == "__main__":
	subreddits = get_subreddits()
	subreddits = get_all_moderators(subreddits)
	
	subreddits, mods = gather_data(subreddits)
	write_subreddit_csv(subreddits)
	write_mods_csv(mods)
