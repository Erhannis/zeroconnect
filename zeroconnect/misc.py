# Contains (2^n)-1 maps.  Addressed by tuples.  Get can contain Nones, Set cannot.  Get with Nones returns a set of matching entries.  Get without Nones returns exact match.
# fm[()]
class FilterMap:
    def __init__(self, size):
        """Warning: creates (2^size)-1 internal maps"""
        self.maps = []
        self.size = size
        for i in range((1<<size)-1):
            self.maps.append({})
    
    def __len__(self):
        return len(self.maps[len(self.maps)-1]) # The map with all filters
    
    def exactGet(self, key):
        """Can be used to retrieve entries that have None in them.  Not generally recommended."""
        return self.maps[len(self.maps)-1][key]

    def __getitem__(self, key):
        j = 0
        for i in range(self.size):
            if key[i] != None:
                j = j + (1<<i)
        if j == 0:
            return {self.exactGet(key)}
        return self.maps[j-1][key]

    def __getSetIndices(self, key):
        m = 0
        for i in range(self.size):
            if key[i] != None:
                m = m | (1<<i)
        indices = set()
        for i in range(1, (1<<self.size)):
            if i & m == i:
                indices.add(i-1)
        return indices

    def __setitem__(self, key, value):
        indices = self.__getSetIndices(key)
        for iMap in indices:
            k = list(key)
            for bit in range(self.size):
                if not ((iMap+1) & (1<<bit)):
                    k[bit] = None
            k = tuple(k)
            if iMap == (len(self.maps)-1):
                self.maps[iMap][k] = value #TODO Wait, heck.  If this overwrites something, st st unknown map removals
            else:
                if k not in self.maps[iMap]:
                    self.maps[iMap][k] = set()
                self.maps[iMap][k].add(value)

    def __delitem__(self, key):
        pass

    def __iter__(self):
        return self.maps[len(self.maps)-1].__iter__()
"""
size = 3
[
    {(S, 0, 0)}, 0
    {(0, N, 0)}, 1
    {(S, N, 0)}, 2
    {(0, 0, P)}, 3
    {(S, 0, P)}, 4
    {(0, N, P)}, 5
    {(S, N, P)}, 6
]

gi 0b100101
   0b000001
   0b000100
   0b000101
   0b100000
   0b100001
   0b100100
   0b100101

fm = FilterMap(2) # service, node

fm[("nails","bob")] = "connection1"
fm[("nails",None)]
"""