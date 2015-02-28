from utils import read_multi, write_multi, utilrandom as random
from math import log
from monsterrandomizer import monsterdict

fsetdict = None
formdict = None


class Formation():
    def __init__(self, formid):
        self.formid = formid
        self.pointer = 0xf6200 + (formid*15)
        self.auxpointer = 0xf5900 + (formid*4)

    def __repr__(self):
        return self.description()

    def description(self, renamed=False):
        counter = {}
        for e in self.present_enemies:
            if renamed:
                name = e.display_name
            else:
                name = e.name
            if name not in counter:
                counter[name] = 0
            counter[name] += 1
        s = ""
        for name, count in sorted(counter.items()):
            s = ', '.join([s, "%s x%s" % (name, count)])
        s = s[2:]
        s = "%s (%x)" % (s, self.formid)
        #s += " " + " ".join(["%x" % e.id for e in self.present_enemies])
        return s

    @property
    def has_boss(self):
        return any([e.is_boss or e.boss_death for e in self.present_enemies])

    def get_guaranteed_drop_value(self, value=0):
        if len(self.present_enemies) == 0:
            return False

        values = []
        for e in self.present_enemies:
            for d in e.drops:
                value = 1000000
                if d is None:
                    value = 0
                else:
                    value = min(value, d.rank())
            values.append(value)
        return max(values)

    @property
    def veldty(self):
        return self.formid <= 0x1af

    @property
    def pincer_prohibited(self):
        return self.misc1 & 0x40

    @property
    def back_prohibited(self):
        return self.misc1 & 0x20

    @property
    def battle_event(self):
        return any([m.battle_event for m in self.present_enemies])

    def read_data(self, filename):
        f = open(filename, 'r+b')
        f.seek(self.pointer)
        self.mouldbyte = ord(f.read(1))
        self.mould = self.mouldbyte >> 4
        self.enemies_present = ord(f.read(1))
        self.enemy_ids = map(ord, f.read(6))
        self.enemy_pos = map(ord, f.read(6))
        self.bosses = ord(f.read(1))

        f.seek(self.auxpointer)
        self.misc1 = ord(f.read(1))
        self.misc2 = ord(f.read(1))
        self.eventscript = ord(f.read(1))
        self.misc3 = ord(f.read(1))

        appointer = 0x1fb400 + self.formid
        if appointer < 0x1fb600:
            f.seek(0x1fb400 + self.formid)
            self.ap = ord(f.read(1))
        else:
            self.ap = None

        f.close()

    @property
    def mould(self):
        return self.mouldbyte >> 4

    @property
    def has_event(self):
        return bool(self.misc2 & 0x80)

    @property
    def present_enemies(self):
        return [e for e in self.enemies if e]

    @property
    def ambusher(self):
        return any([e.ambusher for e in self.present_enemies])

    @property
    def inescapable(self):
        return any([e.inescapable for e in self.present_enemies])

    def set_attack_type(self, normal=True, back=False,
                        pincer=False, side=False):
        self.misc1 &= 0x0F
        self.misc1 |= 0x10 if not normal else 0
        self.misc1 |= 0x20 if not back else 0
        self.misc1 |= 0x40 if not pincer else 0
        self.misc1 |= 0x80 if not side else 0

    def get_music(self):
        return (self.misc3 >> 3) & 0b111

    def set_music(self, value):
        # BATTLE THEMES
        # 0 regular
        # 1 boss
        # 2 atmaweapon
        # 3 returners theme
        # 4 minecart
        # 5 dancing mad
        # 6-7 no change
        self.misc3 &= 0b11000111
        self.misc3 |= (value << 3)

    def set_continuous_music(self):
        self.misc3 |= 0x80
        self.misc2 |= 0x02

    def set_music_appropriate(self):
        music = random.randint(1, 5) if self.rank() > 35 else random.choice([1, 3, 4])
        self.set_music(music)

    def set_fanfare(self, value=False):
        if value:
            self.misc1 &= 0xFE
        else:
            self.misc1 |= 1

    def set_event(self, value=False):
        if value:
            self.misc2 |= 0x80
        else:
            self.misc2 &= 0x7F
            self.eventscript = 0

    def set_windows(self, value=True):
        if value:
            self.misc3 |= 0x04
        else:
            self.misc3 &= 0xFB

    def set_appearing(self, value):
        # 0 none
        # 1 smoke
        # 2 dropdown
        # 3 from left
        # 4 splash from below
        # 5 float down
        # 6 splash from below (sand?)
        # 7 from left (fast?)
        # 8 fade in (top-bottom)
        # 9 fade in (bottom-top)
        # 10 fade in (wavey)
        # 11 fade in (slicey)
        # 12 none
        # 13 blink in
        # 14 stay below screen
        # 15 slowly fall, play Dancing Mad
        self.misc1 &= 0xF0
        self.misc1 |= value
        if value == 15:
            self.set_music(6)

    def write_data(self, filename):
        f = open(filename, 'r+b')
        f.seek(self.pointer)
        f.write(chr(self.mouldbyte))
        f.write(chr(self.enemies_present))
        f.write("".join(map(chr, self.enemy_ids)))
        f.write("".join(map(chr, self.enemy_pos)))
        f.write(chr(self.bosses))

        f.seek(self.auxpointer)
        f.write(chr(self.misc1))
        f.write(chr(self.misc2))
        f.write(chr(self.eventscript))
        f.write(chr(self.misc3))

        if self.ap is not None:
            f.seek(0x1fb400 + self.formid)
            f.write(chr(self.ap))

        f.close()

    def lookup_enemies(self):
        self.enemies = []
        self.big_enemy_ids = []
        for i, eid in enumerate(self.enemy_ids):
            if eid == 0xFF and not self.enemies_present & (1 << i):
                self.enemies.append(None)
                continue
            if self.enemies_present & (1 << i) and self.bosses & (1 << i):
                eid += 0x100
            self.big_enemy_ids.append(eid)
            self.enemies.append(monsterdict[eid])
            enemy_pos = self.enemy_pos[i]
            x, y = enemy_pos >> 4, enemy_pos & 0xF
            self.enemies[i].update_pos(x, y)
        for e in self.enemies:
            if not e:
                continue
            e.add_mould(self.mould)

    def set_big_enemy_ids(self, eids):
        self.bosses = 0
        self.enemy_ids = []
        for n, eid in enumerate(eids):
            if eid & 0x100:
                self.bosses |= (1 << n)
            if not self.enemies_present & (1 << n):
                self.bosses |= (1 << n)
            self.enemy_ids.append(eid & 0xFF)

    def read_mould(self, filename):
        mouldspecsptrs = 0x2D01A
        f = open(filename, 'r+b')
        pointer = mouldspecsptrs + (2*self.mould)
        f.seek(pointer)
        pointer = read_multi(f, length=2) | 0x20000
        for i in xrange(6):
            f.seek(pointer + (i*4))
            a, b = tuple(map(ord, f.read(2)))
            width = ord(f.read(1))
            height = ord(f.read(1))
            enemy = self.enemies[i]
            if enemy:
                enemy.update_size(width, height)

    def copy_data(self, other):
        attributes = [
            "mouldbyte", "enemies_present", "enemy_ids",
            "enemy_pos", "bosses", "misc1", "misc2", "eventscript",
            "misc3"]
        for attribute in attributes:
            value = getattr(other, attribute)
            value = type(value)(value)
            setattr(self, attribute, value)

    def rank(self, levels=None):
        if levels is None:
            levels = [e.stats['level'] for e in self.present_enemies if e]
        if len(levels) == 0:
            return 0
        balance = sum(levels) / (log(len(levels))+1)
        average = sum(levels) / len(levels)
        score = (max(levels) + balance + average) / 3.0
        return score

    @property
    def exp(self):
        return sum(e.stats['xp'] for e in self.present_enemies)

    def mutate(self, ap=False):
        if ap and self.ap is not None:
            while random.choice([True, False]):
                self.ap += random.randint(-1, 1)
                self.ap = min(100, max(self.ap, 0))
        if self.ambusher:
            if not (self.pincer_prohibited and self.back_prohibited):
                self.misc1 |= 0x90

    def get_special_ap(self):
        levels = [e.stats['level'] for e in self.present_enemies if e]
        ap = int(sum(levels) / len(levels))
        low = ap / 2
        ap = low + random.randint(0, low) + random.randint(0, low)
        ap = random.randint(0, ap)
        self.ap = min(100, max(ap, 0))


class FormationSet():
    def __init__(self, setid):
        baseptr = 0xf4800
        self.setid = setid
        if self.setid <= 0xFF:
            self.pointer = baseptr + (setid * 8)
        else:
            self.pointer = baseptr + (0x100 * 8) + ((setid - 0x100) * 4)

    def __repr__(self):
        s = ""
        s += "SET ID %x\n" % self.setid
        for f in self.formations:
            s += "%s " % f.formid
            for i in range(8):
                    s += '* ' if f.misc1 & (1 << i) else '  '
            s += str([e.name for e in f.present_enemies]) + "\n"
        return s.strip()

    @property
    def formations(self):
        return [formdict[i & 0x7FFF] for i in self.formids]

    @property
    def unused(self):
        if self.setid == 0x100:
            return False
        return all([f.formid == 0 for f in self.formations])

    @property
    def has_boss(self):
        return any([f.has_boss for f in self.formations])

    @property
    def veldty(self):
        return all([f.veldty for f in self.formations])

    def read_data(self, filename):
        f = open(filename, 'r+b')
        f.seek(self.pointer)
        self.formids = []
        if self.setid <= 0xFF:
            num_encounters = 4
        else:
            num_encounters = 2
        for i in xrange(num_encounters):
            self.formids.append(read_multi(f, length=2))
        f.close()

    def write_data(self, filename):
        f = open(filename, 'r+b')
        f.seek(self.pointer)
        for value in self.formids:
            write_multi(f, value, length=2)
        f.close()

    def mutate_formations(self, candidates, verbose=False, test=False):
        if test:
            for i in range(4):
                chosen = random.choice(candidates)
                self.formids[i] = chosen.formid
            return self.formations

        low = max(fo.rank() for fo in self.formations) * 1.0
        high = low * 1.5
        while random.randint(1, 3) == 3:
            high = high * 1.25

        candidates = filter(lambda c: low <= c.rank() <= high, candidates)
        candidates = sorted(candidates, key=lambda c: c.rank())
        if not candidates:
            return []

        slots = [3]
        chosens = []
        for i in slots:
            halfway = max(0, len(candidates)/2)
            index = random.randint(0, halfway) + random.randint(0, halfway)
            index = min(index, len(candidates)-1)
            chosen = candidates[index]
            candidates.remove(chosen)
            self.formids[i] = chosen.formid
            chosens.append(chosen)
            if not candidates:
                break

        if verbose:
            print "%x" % self.setid
            for fo in self.formations:
                print "%x" % fo.formid,
                print [e.name for e in fo.present_enemies]
            print

        return chosens

    @property
    def swappable(self):
        if len(self.formids) < 4 or len(set(self.formids)) == 1:
            return False
        return True

    def swap_formations(self, other):
        if not (self.swappable and other.swappable):
            return

        highself = max(self.formations, key=lambda f: f.rank())
        highother = max(other.formations, key=lambda f: f.rank())
        candidates = self.formations + other.formations
        if random.randint(1, 7) != 7:
            candidates.remove(highself)
            candidates.remove(highother)
        random.shuffle(candidates)
        formids = [f.formid for f in candidates]
        self.formids = formids[:len(formids)/2]
        other.formids = formids[len(formids)/2:]
        if len(formids) == 6:
            self.formids.append(highself.formid)
            other.formids.append(highother.formid)
        self.shuffle_formations()
        other.shuffle_formations()

    def shuffle_formations(self):
        random.shuffle(self.formids)

    def rank(self):
        return sum(f.rank() for f in self.formations) / 4.0


def get_formation(formid):
    global formdict
    return formdict[formid]


def get_formations(filename=None):
    global formdict
    if formdict:
        return [f for (_, f) in sorted(formdict.items())]

    formdict = {}
    for i in xrange(576):
        f = Formation(i)
        f.read_data(filename)
        f.lookup_enemies()
        f.read_mould(filename)
        formdict[i] = f

    return get_formations()


def get_fsets(filename=None):
    global fsetdict
    if filename is None or fsetdict:
        fsets = [fs for (_, fs) in sorted(fsetdict.items())]
        return fsets
    else:
        fsetdict = {}
        for i in xrange(512):
            fs = FormationSet(setid=i)
            fs.read_data(filename)
            fsetdict[i] = fs
        return get_fsets()


def get_fset(setid):
    return fsetdict[setid]


if __name__ == "__main__":
    from sys import argv
    from monsterrandomizer import get_monsters
    filename = argv[1]
    monsters = get_monsters(filename)
    for m in monsters:
        m.read_stats(filename)
    fsets = get_fsets(filename=filename)
    formations = get_formations(filename=filename)
    for f in formations:
        print f, f.get_music()

    for f in fsets:
        print f
