"""
VAE-related costs
"""
__authors__ = "Vincent Dumoulin"
__copyright__ = "Copyright 2014, Universite de Montreal"
__credits__ = ["Vincent Dumoulin"]
__license__ = "3-clause BSD"
__maintainer__ = "Vincent Dumoulin"
__email__ = "pylearn-dev@googlegroups"

from pylearn2.costs.cost import Cost, DefaultDataSpecsMixin
from pylearn2.utils import wraps
from theano.compat.python2x import OrderedDict


class VAECriterion(DefaultDataSpecsMixin, Cost):
    """
    Variational autoencoder criterion

    Parameters
    ----------
    num_samples : int
        Number of posterior samples
    """
    supervised = False

    def __init__(self, num_samples):
        assert num_samples >= 1
        self.num_samples = int(num_samples)

    @wraps(Cost.expr)
    def expr(self, model, data, **kwargs):
        space, sources = self.get_data_specs(model)
        space.validate(data)
        return -model.log_likelihood_lower_bound(data, self.num_samples).mean()

    def get_monitoring_channels(self, model, data, **kwargs):
        space, sources = self.get_data_specs(model)
        space.validate(data)
        kl, expectation_term = model.log_likelihood_lower_bound(data, self.num_samples, separate=True)
        rval = OrderedDict()
        rval["kl_divergence"] = kl.mean()
        rval["expectation_term"] = expectation_term.mean()

        return rval

class ImportanceSamplingCriterion(DefaultDataSpecsMixin, Cost):
    """
    Importance sampling criterion

    Parameters
    ----------
    num_samples : int
        Number of importance samples
    """
    supervised = False

    def __init__(self, num_samples):
        assert num_samples >= 1
        self.num_samples = int(num_samples)

    @wraps(Cost.expr)
    def expr(self, model, data, **kwargs):
        space, sources = self.get_data_specs(model)
        space.validate(data)
        return -model.log_likelihood_approximation(data,
                                                   self.num_samples).mean()
