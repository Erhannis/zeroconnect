#TODO Export
class FilterMap:
    def __init__(self, size):
        """
        Addressed by tuples.  `size` is size of tuple. 
        Get can contain Nones.
        Set *can* contain Nones, but it's not recommended - I suspect it'll be a little messy.
        getExact returns a single entry, or throws.
        getFilter returns a list of matching entries.
        Get performs getExact or getFilter, depending on whether the key contains Nones.

        fm = FilterMap(3)
        fm[(0,0,0)] = 0
        fm[(0,0,1)] = 1
        fm[(0,1,0)] = 2
        fm[(0,1,1)] = 3
        fm[(1,0,0)] = 4
        fm[(1,0,1)] = 5
        fm[(1,1,0)] = 6
        fm[(1,1,1)] = 7

        fm[(1,1,1)]    # = 7
        fm[(1,1,None)] # = [6, 7]

        I abandoned fast-lookup; now if the key contains Nones it iterates the map.  Sigh.
        ...I probably shouldn't put commentary in my documentation.
        """
        self.map = {}
        self.size = size
    
    def __len__(self):
        return len(self.map)
    
    def getExact(self, key):
        """
        Can be used to retrieve entries that have None in them.
        """
        return self.map[key]

    def getFilter(self, key):
        results = []
        for k in self.map:
            bad = False
            for i in range(self.size):
                if key[i] != None and k[i] != key[i]:
                    bad = True
                    break
            if bad:
                continue
            results.append(self.map[k])
        return results

    def __getitem__(self, key):
        hasNone = False
        for i in range(self.size):
            if key[i] == None:
                hasNone = True
                break
        if hasNone:
            return self.getFilter(key)
        else:
            return self.getExact(key)

    def __setitem__(self, key, value):
        self.map[key] = value

    def __delitem__(self, key):
        """
        Deletes key.  Exact match.  See `delFilter`.
        """
        del self.map[key]

    def delFilter(self, key):
        keys = []
        for k in self.map:
            bad = False
            for i in range(self.size):
                if key[i] != None and k[i] != key[i]:
                    bad = True
                    break
            if bad:
                continue
            keys.append(k)
        for k in keys:
            del self.map[k]

    def filterKeys(self, key):
        """
        Like getFilter, but returns a list of keys instead of values.
        """
        results = []
        for k in self.map:
            bad = False
            for i in range(self.size):
                if key[i] != None and k[i] != key[i]:
                    bad = True
                    break
            if bad:
                continue
            results.append(k)
        return results

    def __iter__(self):
        return self.map.__iter__()
