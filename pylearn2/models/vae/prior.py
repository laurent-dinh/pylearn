"""
Classes implementing logic related to the prior distribution
:math:`p_\\theta(\\mathbf{z})` in the VAE framework
"""
__authors__ = "Vincent Dumoulin"
__copyright__ = "Copyright 2014, Universite de Montreal"
__credits__ = ["Vincent Dumoulin"]
__license__ = "3-clause BSD"
__maintainer__ = "Vincent Dumoulin"
__email__ = "pylearn-dev@googlegroups"

import numpy
import warnings
import theano
import theano.tensor as T
from theano.compat.python2x import OrderedDict
from pylearn2.models import Model
from pylearn2.models.mlp import Linear, CompositeLayer
from pylearn2.utils.rng import make_theano_rng
from pylearn2.utils import sharedX, wraps
from pylearn2.space import VectorSpace, CompositeSpace

pi = sharedX(numpy.pi)


class Prior(Model):
    """
    Abstract class implementing methods related to the prior distribution
    :math:`p_\\theta(\\mathbf{z})` for the VAE framework

    Parameters
    ----------
    learn_prior : bool, optional
        Whether to learn the prior distribution on z. Defaults to `True`.
    """
    def __init__(self, learn_prior=True):
        super(Prior, self).__init__()
        self.learn_prior = learn_prior

    def get_vae(self):
        """
        Returns the VAE that this `Prior` instance belongs to, or None
        if it has not been assigned to a VAE yet.
        """
        if hasattr(self, 'vae'):
            return self.vae
        else:
            return None

    def set_vae(self, vae):
        """
        Assigns this `Prior` instance to a VAE.

        Parameters
        ----------
        vae : pylearn2.models.vae.VAE
            VAE to assign to
        """
        if self.get_vae() is not None:
            raise RuntimeError("this `Prior` instance already belongs to "
                               "another VAE")
        self.vae = vae
        self.rng = self.vae.rng
        self.theano_rng = make_theano_rng(int(self.rng.randint(2 ** 30)),
                                          which_method=["normal", "uniform"])
        self.batch_size = vae.batch_size

    def initialize_parameters(self, nhid):
        """
        Initialize model parameters.

        Parameters
        ----------
        nhid : int
            Number of latent units for z
        """
        raise NotImplementedError(str(self.__class__) + " does not implement "
                                  "initialize_parameters")

    def get_prior_theta(self):
        """
        Returns parameters of the prior distribution
        :math:`p_\\theta(\\mathbf{z})`
        """
        raise NotImplementedError(str(self.__class__) + " does not implement "
                                  "get_prior_theta")

    def sample_from_p_z(self, num_samples, **kwargs):
        """
        Samples from the prior distribution :math:`p_\\theta(\\mathbf{z})`

        Parameters
        ----------
        num_samples : int
            Number of samples

        Returns
        -------
        z : tensor_like
            Sample from the prior distribution
        """
        raise NotImplementedError(str(self.__class__) + " does not implement "
                                  "sample_from_p_z.")

    def log_p_z(self, z):
        """
        Computes the log-prior probabilities of `z`

        Parameters
        ----------
        z : tensor_like
            Posterior samples

        Returns
        -------
        log_p_z : tensor_like
            Log-prior probabilities
        """
        raise NotImplementedError(str(self.__class__) + " does not implement "
                                  "log_p_z.")


class DiagonalGaussianPrior(Prior):
    """
    Implements a gaussian prior diagonal covariance matrix, i.e.

    .. math::
        p_\\theta(\\mathbf{z})
        = \\prod_i \\exp(-(z_i - \\mu_i)^2 / (2\\sigma_i^2 ) /
                   (\\sqrt{2 \\pi} \\sigma_i)
    """
    @wraps(Prior.initialize_parameters)
    def initialize_parameters(self, nhid):
        self.nhid = nhid
        self.prior_mu = sharedX(numpy.zeros(self.nhid), name="prior_mu")
        self.log_prior_sigma = sharedX(numpy.zeros(self.nhid),
                                       name="prior_log_sigma")
        self._params = []
        if self.learn_prior:
            self._params += [self.prior_mu, self.log_prior_sigma]

    @wraps(Prior.get_prior_theta)
    def get_prior_theta(self):
        return (self.prior_mu, self.log_prior_sigma)

    @wraps(Prior.sample_from_p_z)
    def sample_from_p_z(self, num_samples):
        return self.theano_rng.normal(size=(num_samples, self.nhid),
                                      avg=self.prior_mu,
                                      std=T.exp(self.log_prior_sigma),
                                      dtype=theano.config.floatX)

    @wraps(Prior.log_p_z)
    def log_p_z(self, z):
        return -0.5 * (
            T.log(2 * pi * T.exp(2 * self.log_prior_sigma)) +
            ((z - self.prior_mu) / T.exp(self.log_prior_sigma)) ** 2
        ).sum(axis=2)
