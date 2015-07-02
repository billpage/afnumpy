import numpy
import arrayfire
import numbers
from IPython.core.debugger import Tracer
import private_utils as pu


def fromstring(string, dtype=float, count=-1, sep=''):
    return array(numpy.fromstring(string, dtype, count, sep))

def roll(a, shift, axis=None):
    shape = a.shape
    if(axis is None):
        axis = 0
        a = a.flatten()
    axis = pu.c2f(a.shape, axis)
    if axis == 0:
        s = arrayfire.shift(a.d_array, shift, 0, 0, 0)
    elif axis == 1:
        s = arrayfire.shift(a.d_array, 0, shift, 0, 0)
    elif axis == 2:
        s = arrayfire.shift(a.d_array, 0, 0, shift, 0)
    elif axis == 3:
        s = arrayfire.shift(a.d_array, 0, 0, 0, shift)
    else:
        raise NotImplementedError
    return ndarray(shape, dtype=a.dtype, af_array=s)        

def vdot(a, b):
    s = arrayfire.dot(arrayfire.conjg(a.d_array), b.d_array)
    return ndarray(pu.af_shape(s), dtype=a.dtype, af_array=s)

def zeros(shape, dtype=float, order='C'):
    b = numpy.zeros(shape, dtype, order)
    return ndarray(b.shape, b.dtype, buffer=b,order=order)

def ones(shape, dtype=float, order='C'):
    b = numpy.ones(shape, dtype, order)
    return ndarray(b.shape, b.dtype, buffer=b,order=order)

def array(object, dtype=None, copy=True, order=None, subok=False, ndmin=0):
    if(order is not None):
        raise NotImplementedError
    if(subok is not False):
        raise NotImplementedError
    # If it's not a numpy or afnumpy array first create a numpy array from it
    if(not isinstance(object, ndarray) and
       not isinstance(object, numpy.ndarray)):
        object = numpy.array(object, dtype=dtype, copy=copy, subok=subok, ndmin=ndmin)
#        return ndarray(a.shape, dtype=a.dtype, buffer=a)       

    shape = object.shape
    while(ndmin > len(shape)):
        shape = (1,)+shape
    if(dtype is None):
        dtype = object.dtype
    if(isinstance(object, ndarray)):
        if(copy):
            s = object.d_array.copy().astype(pu.TypeMap[dtype])
        else:
            s = object.d_array.astype(pu.TypeMap[dtype])
        return ndarray(shape, dtype=dtype, af_array=s)
    elif(isinstance(object, numpy.ndarray)):
        return ndarray(shape, dtype=dtype, buffer=object.astype(dtype, copy=False))
    else:
        raise AssertionError
        

def where(condition, x=pu.dummy, y=pu.dummy):
    a = condition
    s = arrayfire.where(a.d_array)
    if(x is pu.dummy and y is pu.dummy):
        return ndarray(pu.af_shape(s), dtype=numpy.uint32, af_array=s)
    elif(x is not pu.dummy and y is not pu.dummy):
        if(x.dtype != y.dtype):
            raise TypeError('x and y must have same dtype')
        if(x.shape != y.shape):
            raise ValueError('x and y must have same shape')
        idx = ndarray(pu.af_shape(s), dtype=numpy.uint32, af_array=s)
        ret = array(y)
        ret[idx] = x[idx]
        return ret;
    else:
        raise ValueError('either both or neither of x and y should be given')

def all(a, axis=None, out=None, keepdims=False):
    if(out is not None):
        raise NotImplementedError
    if(keepdims is not False):
        raise NotImplementedError
    if(axis is None):
        for i in range(len(a.shape)-1,-1,-1):
            s = arrayfire.allTrue(a.d_array, pu.c2f(a.shape, i)) 
            a = ndarray(pu.af_shape(s), dtype=bool, af_array=s)
    else:
        s = arrayfire.allTrue(a.d_array, pu.c2f(a.shape, axis))
    a = ndarray(pu.af_shape(s), dtype=bool, af_array=s)
    if(axis == -1):
        if(keepdims):
            return numpy.array(a)
        else:
            return numpy.array(a)[0]
    else:
        return a

def sum(a, axis=None, dtype=None, out=None, keepdims=False):
    if(out is not None):
        raise NotImplementedError
    if(keepdims is not False):
        raise NotImplementedError
    if(axis is None):
        for i in range(len(a.shape)-1,-1,-1):
            s = arrayfire.sum(a.d_array, pu.c2f(a.shape, i)) 
            a = ndarray(pu.af_shape(s), dtype=a.dtype, af_array=s)
    else:
        s = arrayfire.sum(a.d_array, pu.c2f(a.shape, axis))
    a = ndarray(pu.af_shape(s), dtype=a.dtype, af_array=s)
    if(axis is None):
        if(keepdims):
            return numpy.array(a)
        else:
            return numpy.array(a)[0]
    else:
        return a


def reshape(a, newshape, order='C'):
    if(order is not 'C'):
        raise NotImplementedError
    newshape = numpy.array(pu.c2f(newshape), dtype=pu.dim_t)
    ret, handle = arrayfire.af_moddims(a.d_array.get(), newshape.size, newshape.ctypes.data)
    s = arrayfire.array_from_handle(handle)
    a = ndarray(pu.af_shape(s), dtype=a.dtype, af_array=s)
    return a

class ndarray(object):
    def __init__(self, shape, dtype=float, buffer=None, offset=0, strides=None, order=None, af_array=None):
        if(offset != 0):
            raise NotImplementedError('offset must be 0')
        if(strides is not None):
            raise NotImplementedError('strides must be None')
        if(order is not None and order != 'C'):
            raise NotImplementedError('order must be None')
        self.shape = shape
        self.dtype = dtype
        s_a = numpy.array(pu.c2f(shape),dtype=pu.dim_t)
        if(s_a.size < 1):
            raise NotImplementedError('0 dimension arrays are not yet supported')
        elif(s_a.size <= 4):
            if(af_array is not None):
                self.handle = af_array.get()
                # We need to make sure to keep a copy of af_array
                # Otherwise python will free it and havoc ensues
                self.d_array = af_array
            else:
                if(buffer is not None):
                    ret, self.handle = arrayfire.af_create_array(buffer.ctypes.data, s_a.size, s_a.ctypes.data, pu.TypeMap[dtype])
                else:
                    ret, self.handle = arrayfire.af_create_handle(s_a.size, s_a.ctypes.data, pu.TypeMap[dtype])
                self.d_array = arrayfire.array_from_handle(self.handle)
        else:
            raise NotImplementedError('Only up to 4 dimensions are supported')
        self.h_array = numpy.ndarray(shape,dtype,buffer,offset,strides,order)
        
    def __repr__(self):
        self.d_array.host(self.h_array.ctypes.data)
        return self.h_array.__repr__()        

    def __str__(self):
        self.d_array.host(self.h_array.ctypes.data)
        return self.h_array.__str__()        

    def __add__(self, other):
        s = arrayfire.__add__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __iadd__(self, other):
        self[:] = self[:] + pu.raw(other)
        return self

    def __radd__(self, other):
        s = arrayfire.__add__(pu.raw(other), self.d_array)
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __sub__(self, other):
        s = arrayfire.__sub__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __isub__(self, other):
        self[:] = self[:] - pu.raw(other)
        return self

    def __rsub__(self, other):
        s = arrayfire.__sub__(pu.raw(other), self.d_array)
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __mul__(self, other):
        s = arrayfire.__mul__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __imul__(self, other):
        self[:] = self[:] * pu.raw(other)
        return self

    def __rmul__(self, other):
        s = arrayfire.__mul__(pu.raw(other), self.d_array)
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __div__(self, other):
        s = arrayfire.__div__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __idiv__(self, other):
        self[:] = self[:] / pu.raw(other)
        return self

    def __rdiv__(self, other):
        s = arrayfire.__div__(pu.raw(other), self.d_array)
        return ndarray(self.shape, dtype=self.dtype, af_array=s)
        
    def __pow__(self, other):
        s = arrayfire.pow(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __rpow__(self, other):
        s = arrayfire.pow(pu.raw(other), self.d_array)
        return ndarray(self.shape, dtype=self.dtype, af_array=s)

    def __lt__(self, other):
        s = arrayfire.__lt__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __le__(self, other):
        s = arrayfire.__le__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __gt__(self, other):
        s = arrayfire.__gt__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __ge__(self, other):
        s = arrayfire.__ge__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __eq__(self, other):
        s = arrayfire.__eq__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __ne__(self, other):
        s = arrayfire.__ne__(self.d_array, pu.raw(other))
        return ndarray(self.shape, dtype=numpy.bool, af_array=s)

    def __abs__(self):
        s = arrayfire.abs(self.d_array)
        # dtype is wrong for complex types
        return ndarray(self.shape, dtype=pu.InvTypeMap[s.type()], af_array=s)

    def __nonzero__(self):
        return numpy.array(self).__nonzero__()

    def __len__(self):
        return len(h_array)

    @property
    def size(self):
        return numpy.prod(self.shape)

    def __getitem__(self, args):
        idx = self.__convert_dim__(args)
        if(isinstance(idx,list)):
            # There must be a better way to do this!
            if(len(idx) == 1):
                s = self.d_array.__getitem__(idx[0])
            if(len(idx) == 2):
                s = self.d_array.__getitem__(idx[0],idx[1])
            if(len(idx) == 3):
                s = self.d_array.__getitem__(idx[0],idx[1],idx[2])
            if(len(idx) == 4):
                s = self.d_array.__getitem__(idx[0],idx[1],idx[2],idx[3])
        else:
            s = self.d_array.__getitem__(idx)

        shape = pu.af_shape(s)
        array = ndarray(shape, dtype=self.dtype, af_array=s)
        shape = list(shape)
        if isinstance(args, tuple):
            while(len(shape) < len(args)):
                shape = [1]+shape


        # ISSUE: Looks like afnumpy contracts dimensions in certain
        # cases and not in others. This should be checked out
        
        # Remove dimensions corresponding to non slices
        if(isinstance(args, tuple)):
            new_shape = []
            for axis in range(0,len(args)):
                if(isinstance(args[axis], slice)):
                    new_shape.append(shape[axis])
            if(new_shape != list(shape)):
                array = array.reshape(new_shape)
        return array

    def __slice_to_seq__(self, idx, axis):
        maxlen = self.shape[axis]
        if(isinstance(idx, numbers.Number)):
            if idx < 0:
                idx = maxlen + idx
            if(idx >= maxlen):
                raise IndexError('index %d is out of bounds for axis %d with size %d' % (idx, axis, maxlen))
            return arrayfire.seq(float(idx), float(idx), float(1))

        if idx.step is None:
            step = 1
        else:
            step = idx.step
        if idx.start is None:
            if step < 0:
                start = maxlen-1
            else:
                start = 0
        else:
            start = idx.start
            if(start < 0):
                start += maxlen
        if idx.stop is None:
            if step < 0:
                end = 0
            else:
                end = maxlen-1
        else:
            end = idx.stop
            if(end < 0):
                end += maxlen-1
            if step < 0:
                end += 1
        # arrayfire doesn't like other steps in this case
        if(start == end):
            step = 1
        sl = slice(start,end,step)
        return  arrayfire.seq(float(sl.start),
                              float(sl.stop),
                              float(sl.step))

    def __convert_dim__(self, idx):
        maxlen = self.shape[0]
        if(isinstance(idx, ndarray)):
            return arrayfire.index(idx.d_array)
        if(isinstance(idx, slice)):
            if(len(self.shape) == 1):
                return arrayfire.index(self.__slice_to_seq__(idx,0))               
            else:
                idx = (idx,)
        if(isinstance(idx, numbers.Number)):
            return arrayfire.index(self.__slice_to_seq__(idx,0))               
        if(isinstance(idx, tuple)):
            idx = list(idx)
            while len(idx) < len(self.shape):
                idx.append(slice(None,None,None))
            ret = [0]*len(self.shape)
            for axis in range(0,len(self.shape)):
                ret[pu.c2f(self.shape,axis)] = arrayfire.index(self.__slice_to_seq__(idx[axis],axis))
            return ret
        raise NotImplementedError('indexing with %s not implemented' % (type(idx)))

    def __setitem__(self, idx, value):
        idx = self.__convert_dim__(idx)
        # Here is what I tried
        # ====================
        #if(isinstance(idx,list)):
        #    # There must be a better way to do this!
        #    if(len(idx) == 1):
        #        s = self.d_array.__getitem__(idx[0])
        #    if(len(idx) == 2):
        #        s = self.d_array.__getitem__(idx[0],idx[1])
        #    if(len(idx) == 3):
        #        s = self.d_array.__getitem__(idx[0],idx[1],idx[2])
        #    if(len(idx) == 4):
        #        s = self.d_array.__getitem__(idx[0],idx[1],idx[2],idx[3])
        #else:
        #    s = self.d_array.__getitem__(idx)        
        if(isinstance(value, ndarray)):
            if(value.dtype != self.dtype):
                raise TypeError('left hand side must have same dtype as right hand side')
            if(isinstance(idx,list)):
                # There must be a better way to do this!
                if(len(idx) == 1):
                    self.d_array.setValue(idx[0], value.d_array)
                if(len(idx) == 2):
                    self.d_array.setValue(idx[0], idx[1], value.d_array)
                if(len(idx) == 3):
                    self.d_array.setValue(idx[0], idx[1], idx[2], value.d_array)
                if(len(idx) == 4):
                    self.d_array.setValue(idx[0], idx[1], idx[2], idx[3], value.d_array)
            else:
                self.d_array.setValue(idx, value.d_array)
        elif(isinstance(value, numbers.Number)):
            self.d_array.setValue(idx, value)
        else:
            raise NotImplementedError('values must be a afnumpy.ndarray')

    def __array__(self):
        self.d_array.host(self.h_array.ctypes.data)
        return numpy.copy(self.h_array)

    def transpose(self, *axes):
        s = arrayfire.transpose(self.d_array)
        return ndarray(pu.af_shape(s), dtype=self.dtype, af_array=s)

    def reshape(self, shape, order = 'C'):
        return reshape(self, shape, order)

    def flatten(self):
        return reshape(self, self.size)

    def max(self):
        type_max = getattr(arrayfire, 'max_'+pu.TypeToString[self.d_array.type()])
        return type_max(self.d_array)

    def min(self):
        type_max = getattr(arrayfire, 'min_'+pu.TypeToString[self.d_array.type()])
        return type_max(self.d_array)

#    def __getattr__(self,name):
#        print name
#        raise AttributeError
        

    
