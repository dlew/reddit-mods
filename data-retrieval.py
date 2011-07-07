import urllib
import re
import os
import time
from BeautifulSoup import BeautifulSoup
import cookielib, urllib2
import operator
import json

cj = cookielib.CookieJar()
ck = cookielib.Cookie(version=0, name='over18', value='90607813b305e784a6771b1e328a4c1449f16366', port=None, port_specified=False, domain='www.reddit.com', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
cj.set_cookie(ck)
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

def get_subreddits():
	if os.path.exists("tmp.json"):
		return json.load(open("tmp.json", "r"))

	numFinder = re.compile("(\d+)")

	subreddits = []
	pageNum = 1
	while True:
		f = urllib.urlopen("http://metareddit.com/reddits/biggest/list?page=%d" % pageNum)
		soup = BeautifulSoup(f)
		subreddit_links = soup.findAll("a", {'class': 'subreddit'})

		if len(subreddit_links) == 0:
			break

		for subreddit_link in subreddit_links:
			m = numFinder.search(subreddit_link['title'])
			subreddit = {
				"name": str(subreddit_link.contents[0]),
				"subscribers": int(m.group(0))
			}
			subreddits.append(subreddit)

		pageNum += 1

	json.dump(subreddits, open('tmp.json', 'w'), indent=2)

	return subreddits

def get_all_moderators(subreddits):
	if os.path.exists("subreddits.json"):
		return json.load(open("subreddits.json", "r"))

	x = 0
	for subreddit in subreddits:
		get_moderators(subreddit)
		time.sleep(5) # Be nice, don't crash reddit

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

def print_mod_subreddit_counts(subreddits):
	mods = {}
	for subreddit in subreddits:
		for mod in subreddit["moderators"]:
			if mod not in mods:
				mods[mod] = 1
			else:
				mods[mod] += 1

	for mod in sorted(mods.iteritems(), key=operator.itemgetter(1), reverse=True):
		print mod

def check_for_locks(subreddits):
	hierarchy = {}
	for subreddit in subreddits:
		mods = subreddit["moderators"]
		for i in range(len(mods)):
			mod = mods[i]
			
			if mod not in hierarchy:
				hierarchy[mod] = {}
			
			empowered = hierarchy[mod]
			
			for j in range(i + 1, len(mods)):
				empowered[mods[j]] = None

	checked = {}
	locked = []
	for mod in hierarchy:
		checked[mod] = None
		for slave in hierarchy[mod]:
			if slave not in checked and mod in hierarchy[slave]:
				print "LOCK: %s and %s" % (mod, slave)
				locked.append((mod, slave))

	pain = []
	for subreddit in subreddits:
		mods = subreddit["moderators"]
		locked_in_subreddit = []
		for lock in locked:
			if lock[0] in mods and lock[1] in mods:
				if lock[0] not in locked_in_subreddit:
					locked_in_subreddit.append(lock[0])
				if lock[1] not in locked_in_subreddit:
					locked_in_subreddit.append(lock[1])
		
		num_locked = len(locked_in_subreddit)
		if num_locked > 0:
			lowest_unlocked = 0
			for i in range(len(mods)):
				lowest_unlocked = i
				if mods[i] not in locked_in_subreddit:
					break
			
			pain.append({
				'name': subreddit["name"],
				'locked': num_locked,
				'unlocked': len(mods) - num_locked,
				'total': len(mods),
				'percent': float(num_locked) / len(mods) * 100,
				'lowest': lowest_unlocked
			})

	def cmp_pain(a, b):
		if a['unlocked'] == b['unlocked']:
			if a['total'] == b['total']:
				return b['lowest'] - a['lowest']
			return b['total'] - a['total']
		return a['unlocked'] - b['unlocked']

	for subreddit in sorted(pain, cmp=cmp_pain):
		print "r/%s: %d out of %d (%d unlocked).  Lowest unlocked position: %d" % (subreddit["name"], subreddit["locked"], subreddit["total"], subreddit["unlocked"], subreddit["lowest"])

if __name__ == "__main__":
	subreddits = get_subreddits()
	subreddits = get_all_moderators(subreddits)
	#print_mod_subreddit_counts(subreddits)
	check_for_locks(subreddits)