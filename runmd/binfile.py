import numpy as np


class Binfile:

    def __init__(self, fn=None):
        self.nitem = 0
        self.ndim = 0
        self.dtype = 5
        self.info = []
        self.hash = None
        self.data = np.array([])
        if fn:
            self.read(fn)

    def read(self, fn):
        from struct import unpack
        finp = open(fn, 'rb')
        self.nitem,self.ndim,self.dtype = unpack('III', finp.read(3*4))
        self.info=[]
        for i in range(self.nitem):
          size, = unpack('I', finp.read(4))
          self.info.append(finp.read(size).rstrip('\0'))
        offset = finp.tell()
        finp.seek(0,2)

        if self.dtype == 5:
            self.nframe = (finp.tell()-offset)/self.nitem/self.ndim/4
            self.data = np.memmap(finp,
                                  dtype='float32',
                                  mode='r',
                                  offset=offset,
                                  shape=(self.nframe,self.nitem,self.ndim))
        elif self.dtype == 6:
            self.nframe = (finp.tell()-offset)/self.nitem/self.ndim/8
            self.data = np.memmap(finp,
                                  dtype='float64',
                                  mode='r',
                                  offset=offset,
                                  shape=(self.nframe,self.nitem,self.ndim))
        elif self.dtype == 2:
            self.nframe = (finp.tell()-offset)/self.nitem/self.ndim/1
            self.data = np.memmap(finp,
                                  dtype='uint8',
                                  mode='r',
                                  offset=offset,
                                  shape=(self.nframe,self.nitem,self.ndim))
        else:
            self.nframe = None
            self.data = None

        finp.close()

    def writehead(self, fn, info=None, ndim=None, dtype=None):
        """
        Write header info into a Binfile specified by fn. This method works in
        cooperation with self.writedata. NB: make sure you have already set
        self.info, self.ndim, self.dtype!!!
        Note that self.nitem will be set to len(self.info).
        """
        from struct import pack
        if info is not None:
            self.info = info
        if ndim is not None:
            self.ndim = ndim
        if dtype is not None:
            if isinstance(dtype, str):
                if dtype in ('float32', 'float'):
                    dtype = 5
                elif dtype in ('float64', 'double'):
                    dtype = 6
                elif dtype in ('uint8', 'char'):
                    dtype = 2
                else:
                    print('Unrecognized dtype. Aborted!')
                    exit(1)
            self.dtype = dtype

        if len(self.info) == 0:
            print('No items are defined. Aborted!')
            exit(1)
        self.nitem = len(self.info)

        fout = open(fn, 'wb')
        fout.write(pack('III', self.nitem, self.ndim, self.dtype))
        for inf in self.info:
            n = len(inf)
            n = (n/4+(1 if n%4 else 0)) * 4
            fout.write(pack('I', n))
            inf += '\00'*(n-len(inf))
            fout.write(inf)
        fout.close()

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def writedata(self, fn, data):
        """
        Write data into a Binfile specified by fn. If fn does not exit, it will
        create it and write header into the file first before writing data;
        if fn exists, it will append data into the file.

        input:   fn -- output filename
               data -- An numpy array containing i*nitem*ndim elements
        """
        import os
        if not os.path.exists(fn):
            print('Please run self.writehead() to creat header. Aborted!')
            exit(1)

        # change big-endian into little-endian if applicable
        if data.dtype.byteorder == '>':
            data = data.byteswap().newbyteorder()
        # write data into fn
        fout = open(fn, 'ab')
        fout.write(data.tostring())
        fout.close()

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def write(self, fn):
        self.writehead(fn)
        self.writedata(fn, self.data)

    def putmat(self, frame, atoms):
        assert self.data[frame].shape[0] == len(atoms), 'ERROR: the matrix (%d) does not match atoms (%d)!'%(self.data[frame].shape[0], len(atoms))
        for i, at in enumerate(atoms):
            at.r = np.array(self.data[frame][i, :])
            at.r.shape = (3,1)

    def get_hash(self):
        if self.hash is None:
            import hashlib
            import re
            m = hashlib.md5()
            r = re.compile("\s+")
            for l in self.info:
                s = r.split(l.strip())
                m.update(s[-3].lstrip("0"))  # rId
                m.update(s[-2])              # rName
                m.update(s[-1].strip())      # aName
            self.hash = m.hexdigest()
        return self.hash

# class Trajectory:
#
#     def __init__(self, pattern):
#         self.pattern = pattern
#
#     def putFrame(self, atoms, step, frame):
#         binfile = Binfile(self.pattern%step)
#         assert binfile.get_hash()==atoms.get_hash(), "Atoms does not match to binfile "
#         binfile.putmat(frame, atoms)
