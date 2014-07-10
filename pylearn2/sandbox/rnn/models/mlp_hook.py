"""
Code to hook into the MLP framework
"""
import functools

from pylearn2.sandbox.rnn.space import SequenceSpace
from pylearn2.utils.track_version import MetaLibVersion


class RNNWrapper(MetaLibVersion):
    """
    This metaclass wraps the MLP class by intercepting the class
    creation. Properties can be wrapped by defining `get_`, `set_`,
    and `del_` methods. Methods can be wrapped by defining a
    `_wrapper` method.

    Parameters
    ----------
    See https://docs.python.org/2/reference/datamodel.html#object.__new__
    """
    def __new__(cls, name, bases, dct):
        wrappers = [attr[:-8] for attr in cls.__dict__.keys()
                    if attr.endswith('_wrapper')]
        for wrapper in wrappers:
            if wrapper not in dct:
                for base in bases:
                    method = getattr(base, wrapper, None)
                    if method is not None:
                        break
            else:
                method = dct[wrapper]
            dct[wrapper] = getattr(cls, wrapper + '_wrapper')(method)

        # By default layers are not RNN friendly and don't have
        # a SequenceSpace as input or output
        dct['rnn_friendly'] = False
        dct['_sequence_space'] = False
        return type.__new__(cls, name, bases, dct)

    @classmethod
    def fprop_wrapper(cls, fprop):
        """
        If this was a non-RNN friendly layer, the sequence property
        might have been set, which means we apply this layer element-
        wise over the time axis using scan.

        Parameters
        ----------
        fprop : method
            The fprop method to be wrapped
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

        Parameters
        ----------
        set_input_space : method
            The set_input_space method to be wrapped
        """
        @functools.wraps(set_input_space)
        def outer(self, space):
            if isinstance(space, SequenceSpace) and not self.rnn_friendly:
                self._sequence_space = True
                set_input_space(self, space.space)
            else:
                set_input_space(self, space)
        return outer

    @classmethod
    def get_output_space_wrapper(cls, get_output_space):
        """
        Same thing as set_input_space_wrapper.

        Parameters
        ----------
        get_output_space : method
            The get_output_space method to be wrapped
        """
        @functools.wraps(get_output_space)
        def outer(self):
            if (self._sequence_space and
                    not isinstance(get_output_space(self), SequenceSpace)):
                # Since not only this class, but also the Layer class gets
                # wrapped, we need to make sure we don't wrape the space
                # in a SequenceSpace twice
                return SequenceSpace(get_output_space(self))
            else:
                return get_output_space(self)
        return outer
