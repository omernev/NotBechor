from collections import defaultdict
import pandas as pd
import datetime
import random
import sys
import time
import glob

HISTORY_FILENAME = 'history.txt'
PROGRESS_DRAMATIC_DELAY = 4
EATEN_YESTERDAY_PENALY = 0.75
STILL_HUNGRY_THRESHOLD = 2
MIN_FUN_PARTY_SIZE = 2
PEOPLE_PATH = "People\\"

class Person(object):
    def __init__(self, name):
        self.name = name
        self.preferences = defaultdict(lambda : 4)
        self.table = pd.read_excel('{0}{1}.xlsx'.format(PEOPLE_PATH, self.name), header=None)
        for i in range(len(self.table[0])):
            self.preferences[self.table[0][i]] = self.into_range(self.table[1][i])

    def __repr__(self):
        return "<Person: {0}>".format(self.name)

    def score(self, place, penalty = 1):
        return self.preferences[place]*penalty

    def into_range(self, num):
        if num < 1:
            return 1
        if num > 6:
            return 6
        return num
        
        

class NotBechor(object):
    def __init__(self, names, verbose = False):
        self.people = []
        self.penalties = defaultdict(lambda : 1)
        self.options = set()
        for name in names:
            person = Person(name)
            self.people.append(person)
            for place in person.preferences.keys():
                self.options.add(place)
        self.update_people()
        self.hungry_people = list(self.people)
        self.parties = defaultdict( lambda : [] )
        self.verbose = verbose

    def update_people(self):
        all_not_scored = set()
        for person in self.people:
            not_scored = [place for place in self.options if not(place in person.preferences.keys())]
            all_not_scored = all_not_scored.union(set(not_scored))
            if len(not_scored):
                person.table = person.table.append([[x,4] for x in not_scored])
                person.table.to_excel('{0}{1}.xlsx'.format(PEOPLE_PATH, person.name), header=False, index=False)
                print("{0} Doesn't have scores for {1} - updating to be 4!".format(person.name, not_scored))
        print()
        self.options = self.options.difference(all_not_scored)

    def read_history(self):
        raw = open(HISTORY_FILENAME).read()
        rows = [x.split(",") for x in raw.split("\n") if len(x) > 0]
        for row in rows:
            place = row[0]
            date = datetime.date(int(row[1]),int(row[2]),int(row[3]))
            self.penalties[place] = self._calc_penalty(date)

    def write_history(self, places):
        today = datetime.date.today()
        to_write = ''.join([self.place_to_str(place, today) for place in places])
        file = open(HISTORY_FILENAME, mode='a')
        file.write(to_write)
        file.close()

    def place_to_str(self, place, day):
        return "{0},{1},{2},{3}\n".format(place, day.year, day.month, day.day)

    def _calc_penalty(self, date):
        today = datetime.date.today()
        diff = max(1, (today-date).days)
        return 1 - (EATEN_YESTERDAY_PENALY ** diff)
    
    def _calc_place_score(self, place, people):
        PREF_STRENGTH_FACTOR = 2
        people_scores = [self.get_score(person, place) for person in people]
        base_score = sum(people_scores) / len(people_scores)
        return base_score ** PREF_STRENGTH_FACTOR

    def get_score(self, person, place):
        return person.score(place, self.penalties[place])

    def print_progress(self, secs = PROGRESS_DRAMATIC_DELAY):
        for i in range(secs*5):
            print ('* ',end='')
            sys.stdout.flush()
            time.sleep(0.2)
        print()

    def print_add_status(self):
        print ("New Place: {0}\n".format(self.places[-1]))
        self.print_status()

    def print_remove_status(self, removed_place):
        print ("Removed Place: {0}\n".format(removed_place))
        self.print_status()

    def print_status(self):
        time.sleep(1)
        print ("Current Groups:")
        time.sleep(1)
        for place in self.places:
            print ("{0}: ".format(place), end = '')
            for person in self.parties[place]:
                print ("{0} ({1}), ".format(person.name, round(self.get_score(person, place)),2),end='')
                sys.stdout.flush()
                time.sleep(0.5)
            print()
            time.sleep(1)
        print("\nStill Hungry: ")
        time.sleep(1)
        if len(self.parties['HUNGRY']):
            for person in self.parties['HUNGRY']:
                print ("{0}, ".format(person.name),end='')
                sys.stdout.flush()
                time.sleep(0.5)
        else:
            print("Nobody! :-)")
        print("\n\n")

    def update_parties(self):
        self.parties = defaultdict (lambda : [])
        for person in self.people:
            scores = {place: self.get_score(person, place)for place in self.places}
            best = max(self.places, key = lambda x : scores[x])
            if scores[best] >= STILL_HUNGRY_THRESHOLD:
                self.parties[best].append(person)
            else:
                self.parties['HUNGRY'].append(person)

    def decide_place(self, people):
        options_list = list(self.options)
        scores = [self._calc_place_score(place, people) for place in options_list]
        sum_scores = sum(scores)
        probs = [x / sum_scores for x in scores]
        if self.verbose:
            print(people)
            print(options_list)
            print(probs)
        self.print_before_choice()
        new_place = random.choices(options_list, probs)[0]
        self.places.append(new_place)
        self.options.remove(new_place)
        self.update_parties()
        self.print_add_status()

    def get_smallest_party(self):
        return min([len(self.parties[place]) for place in self.places])

    def remove_unpopular_places(self):
        smallest_party = self.get_smallest_party()
        while (len(self.places) > 1) and (smallest_party < MIN_FUN_PARTY_SIZE):
            worst_place = min(self.places, key = lambda x: len(self.parties[x]))
            del self.places[self.places.index(worst_place)]
            self.update_parties()
            smallest_party = self.get_smallest_party()
            self.print_remove_status(worst_place)

    def print_before_choice(self):
        print("Choosing new place...")
        self.print_progress()

    def choose_lunch(self):
        self.places = []
        while len(self.hungry_people) > 0:
            self.decide_place(self.hungry_people)
            self.remove_unpopular_places()
            self.hungry_people = self.parties['HUNGRY']

    def go(self):
        self.read_history()
        self.choose_lunch()
        self.write_history(self.places)

def get_names(path = PEOPLE_PATH):
    files = glob.glob(path+"*")
    return [x[len(path):x.index('.')] for x in files if x[-4:]=='xlsx']

def go(names):
    nb = NotBechor(names)
    nb.go()
    
