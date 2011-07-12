import urllib
import os
import time
from BeautifulSoup import BeautifulSoup
import cookielib, urllib2
import operator
import json
import locale

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

def print_mod_subreddit_counts(subreddits):
	mods = {}
	for subreddit in subreddits:
		for mod in subreddit["moderators"]:
			if mod not in mods:
				mods[mod] = 1
			else:
				mods[mod] += 1

	for mod in sorted(mods.iteritems(), key=operator.itemgetter(1), reverse=True):
		if mod[1] > 1:
			print "%s mods %d subreddits" % mod
		else:
			print "%s mods %d subreddit" % mod
	print

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
	print

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
		if subreddit["unlocked"] > 0:
			print "r/%s: %d out of %d (%d unlocked).  Lowest unlocked position: %d" % (subreddit["name"], subreddit["locked"], subreddit["total"], subreddit["unlocked"], subreddit["lowest"])
		else:
			print "r/%s: %d out of %d (completely locked)." % (subreddit["name"], subreddit["locked"], subreddit["total"])
	print

# "Despot" is defined as a person who is the single mod of a subreddit
# "Leader" is defined as a person who is the topmost mod of a subreddit
def print_despots(subreddits):
	despots = {}
	leaders = {}
	for subreddit in subreddits:
		mods = subreddit["moderators"]
		
		if len(mods) == 0:
			continue

		leader = mods[0]
		
		if leader not in leaders:
			leaders[leader] = 1
		else:
			leaders[leader] += 1

		if len(mods) == 1:
			if leader not in despots:
				despots[leader] = 1
			else:
				despots[leader] += 1
	
	for mod in sorted(leaders.iteritems(), key=operator.itemgetter(1), reverse=True):
		leader = mod[0]
		despot_count = 0
		if leader in despots:
			despot_count = despots[leader]
		print "%s is a leader of %d subreddits (and despot of %d of them)" % (leader, mod[1], despot_count)
	print

def print_sway(subreddits):
	mods = {}
	total = 0
	for subreddit in subreddits:
		subscribers = subreddit["subscribers"]
		total += subscribers
		for mod in subreddit["moderators"]:
			if mod not in mods:
				mods[mod] = 0
			mods[mod] += subscribers

	for mod in sorted(mods.iteritems(), key=operator.itemgetter(1), reverse=True):
		print "%s mods %s users (%.2f%% of total)" % (mod[0], locale.format("%d", mod[1], True), float(mod[1]) / total * 100)

if __name__ == "__main__":
	subreddits = get_subreddits()
	subreddits = get_all_moderators(subreddits)
	print_mod_subreddit_counts(subreddits)
	print_despots(subreddits)
	check_for_locks(subreddits)
	print_sway(subreddits)