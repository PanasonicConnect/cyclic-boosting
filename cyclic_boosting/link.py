"""This module contains some general/canonical link-mean-function pairs such as

- :class:`~LogLinkMixin`
- :class:`~LogitLinkMixin`
- :class:`~InverseSquaredLinkMixin`
- :class:`~InverseLinkMixin`
"""

from __future__ import absolute_import, division, print_function

import abc

import numexpr
import numpy as np
import six


@six.add_metaclass(abc.ABCMeta)
class LinkFunction(object):
    r"""Abstract base class for link function computations.

    Link functions (:meth:`~link_func`) are meant for transformating
    statistically distributed data to make it suitable for sstatistical
    algorithms with assumptions about data distribution. The corresponding
    inverse transformation (:meth:`~unlink_func`) is called the "mean function".

    http://en.wikipedia.org/wiki/Generalized_linear_model#Link_function

    """

    @abc.abstractmethod
    def is_in_range(self, values):
        "Check if values can be transformed by the link function."
        pass

    @abc.abstractmethod
    def link_func(self, m):
        """Transform values in m to link space"""
        pass

    @abc.abstractmethod
    def unlink_func(self, l):
        """Inverse of :meth:`~link_func`"""
        pass


class LogLinkMixin(LinkFunction):
    r"""Link function and mean function for example for Poisson-distributed
    data.

    Supported values are in the range :math:`x > 0`"""

    def unlink_func(self, l):
        r"""Calculates the inverse of the link function

        .. math::

           \mu = \exp(l)
        """
        return numexpr.evaluate("exp(l)")

    def is_in_range(self, m):
        return np.all(m > 0.0)

    def link_func(self, m):
        r"""Calculates the log-link

        .. math::

           l = \log(\mu)
        """
        return numexpr.evaluate("log(m)")

    def unlink_func_da(self, l):
        r"""Calculates the inverse of the link function

        .. math::

           \mu = \exp(l)
        """
        from dask import array as da

        return da.exp(l)

    def link_func_da(self, m):
        r"""Calculates the log-link

        .. math::

           l = \log(\mu)
        """
        from dask import array as da

        return da.log(m)


class Log2LinkMixin(LinkFunction):
    r"""Link function and mean function for example for Poisson-distributed
    data. Using log to base 2.

    Supported values are in the range :math:`x > 0`"""

    def unlink_func(self, l):
        r"""Calculates the inverse of the link function

        .. math::

           \mu = 2^l
        """
        return numexpr.evaluate("2**l")

    def is_in_range(self, m):
        return np.all(m > 0.0)

    def link_func(self, m):
        r"""Calculates the log-link

        .. math::

           l = \log2(\mu)
        """
        return numexpr.evaluate("log(m)/log(2)")

    def unlink_func_da(self, l):
        r"""Calculates the inverse of the link function

        .. math::

           \mu = 2^l
        """
        return 2 ** l

    def link_func_da(self, m):
        r"""Calculates the log-link

        .. math::

           l = \log2(\mu)
        """
        from dask import array as da

        return da.log2(m)


class LogitLinkMixin(LinkFunction):
    r"""Link for the logit transformation.

    Supported values are in the range :math:`0 \leq x \leq 1`
    """

    def is_in_range(self, p):
        return np.all(numexpr.evaluate("(p >= 0.0) & (p <= 1.0)"))

    def link_func(self, p):
        r"""Calculates the logit-link

        .. math::

           l = \log(\frac{p}{1-p})
        """
        return numexpr.evaluate("log(p / (1. - p))")

    def unlink_func(self, l):
        r"""Inverse of logit-link

        .. math::

           p = \frac{1}{1+ \exp(-l)}
        """
        return numexpr.evaluate("1. / (1. + exp(-l))")


class InverseSquaredLinkMixin(LinkFunction):
    """Inverse squared link mixin"""

    def is_in_range(self, m):
        return np.all(numexpr.evaluate("m != 0.0"))

    def link_func(self, m):
        r"""Calculates the logit-link

        .. math::

           l = - \frac{1}{m^2}
        """
        return numexpr.evaluate("- 1. / m ** -2.")

    def unlink_func(self, l):
        r"""Calculates the inverse of the logit-link

        .. math::

           \mu = \sqrt{-l}
        """
        return numexpr.evaluate("sqrt(-l)")


class InverseLinkMixin(LinkFunction):
    """Inverse link mixin"""

    def is_in_range(self, m):
        return np.all(numexpr.evaluate("m != 0.0"))

    def link_func(self, m):
        r"""Calculates the logit-link

        .. math::

           l = - \frac{1}{m^2}
        """
        return numexpr.evaluate("-1. / m")

    def unlink_func(self, l):
        r"""Calculates the inverse of the logit-link

        .. math::

           \mu = -\frac{1}{l}
        """
        return numexpr.evaluate("-1. / l")


class IdentityLinkMixin(LinkFunction):
    """Identity link"""

    def is_in_range(self, m):
        return True

    def link_func(self, m):
        r"""Returns a copy of the input"""
        return m.copy()

    def unlink_func(self, l):
        r"""Returns a copy of the input"""
        return l.copy()


__all__ = [
    "LinkFunction",
    "LogLinkMixin",
    "Log2LinkMixin",
    "LogitLinkMixin",
    # "InverseSquaredLinkMixin",
    # "InverseLinkMixin",
    "IdentityLinkMixin",
]