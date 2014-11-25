import functools

from theano import tensor
from theano.compat.python2x import OrderedDict

from pylearn2.sandbox.rnn.space import SequenceSpace
from pylearn2.utils.track_version import MetaLibVersion


class RNNWrapper(MetaLibVersion):
    def __new__(cls, name, bases, dct):
        # Allow for methods to be wrapped
        for attr in dct:
            wrapper_name = attr + '_wrapper'
            if hasattr(cls, wrapper_name):
                dct[attr] = getattr(cls, wrapper_name)(dct[attr])

        # Allow for properties to be wrapped; all three methods need
        # to be defined
        accessors = {}
        prefixes = ['get_', 'set_', 'del_']
        for attr in dir(cls):
            for i, prefix in enumerate(prefixes):
                if attr.startswith(prefix):
                    accessors.setdefault(attr[4:],
                                         [None, None, None])[i] = getattr(cls,
                                                                          attr)
        for attr, methods in accessors.iteritems():
            if None not in methods:
                dct[attr] = property(*methods)

        # By default layers are not RNN friendly and don't have
        # a SequenceSpace as input or output
        dct['_rnn_friendly'] = False
        dct['_sequence_space'] = False
        dct['_scan_updates'] = OrderedDict()
        return type.__new__(cls, name, bases, dct)

    @classmethod
    def fprop_wrapper(cls, fprop):
        """
        If this was a non-RNN friendly layer, the sequence property
        might have been set, which means we apply this layer element-
        wise over the time axis using scan.
        """
        @functools.wraps(fprop)
        def outer(self, state_below):
            if self._sequence_space:
                input_shape = ([state_below.shape[0] * state_below.shape[1]] +
                               [state_below.shape[i]
                                for i in xrange(2, state_below.ndim)])
                reshaped_state_below = state_below.reshape(input_shape)
                state = fprop(self, reshaped_state_below)
                output_shape = ([state_below.shape[0], state_below.shape[1]] +
                                [state.shape[i]
                                 for i in xrange(1, state.ndim)])
                reshaped_state = state.reshape(output_shape)
                return reshaped_state
            else:
                return fprop(self, state_below)
        return outer

    @classmethod
    def set_input_space_wrapper(cls, set_input_space):
        """
        If this layer is not RNN-adapted, we intercept the call to the
        set_input_space method and set the space to a non-sequence space.
        However, when output space is set, we set it to the
        SequenceSpace version again.
        """
        @functools.wraps(set_input_space)
        def outer(self, space):
            if isinstance(space, SequenceSpace) and not self._rnn_friendly:
                self._sequence_space = True
                set_input_space(self, space.space)
            else:
                set_input_space(self, space)
        return outer

    @classmethod
    def get_output_space(cls, self):
        return self._output_space

    @classmethod
    def set_output_space(cls, self, output_space):
        if self._sequence_space:
            self._output_space = SequenceSpace(output_space)
        else:
            self._output_space = output_space

    @classmethod
    def del_output_space(cls, self):
        del self._output_space
