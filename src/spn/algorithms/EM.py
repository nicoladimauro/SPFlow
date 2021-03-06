'''
Created on November 09, 2018

@author: Alejandro Molina
@author: Robert Peharz
'''

from scipy.special import logsumexp

from spn.algorithms.Inference import log_likelihood

from spn.structure.leaves.parametric.Parametric import Gaussian

from spn.structure.Base import eval_spn_top_down, Sum, Product, get_nodes_by_type, get_number_of_nodes
import numpy as np


def gradient_backward(spn, data, lls_per_node):
    node_gradients = {}
    node_gradients[Sum] = sum_gradient_backward
    node_gradients[Product] = prod_gradient_backward
    node_gradients[Gaussian] = gaussian_gradient_backward

    gradient_result = {}

    eval_spn_top_down(spn, node_gradients, parent_result=np.zeros((data.shape[0], 1)), gradient_result=gradient_result,
                      lls_per_node=lls_per_node)

    return gradient_result


def gaussian_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0], 1))
    gradients[:,0] = parent_result  # log_sum_exp

    gradient_result[node.id] = gradients


def sum_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0], 1))
    gradients[:] = parent_result  # log_sum_exp

    gradient_result[node.id] = gradients

    messages_to_children = []

    for i, c in enumerate(node.children):
        messages_to_children.append(gradients + np.log(node.weights[i]))

    return messages_to_children


def prod_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0], 1))
    gradients[:] = parent_result  # log_sum_exp

    gradient_result[node.id] = gradients

    messages_to_children = []

    # TODO handle zeros for efficiency, darwiche 2003

    output_ll = lls_per_node[:, node.id]

    for i, c in enumerate(node.children):
        messages_to_children.append(output_ll - lls_per_node[:, c.id])

    return messages_to_children


def EM_optimization(spn, data, iterations=5):
    for _ in range(iterations):
        lls_per_node = np.zeros((data.shape[0], get_number_of_nodes(spn)))

        # one pass bottom up evaluating the likelihoods
        log_likelihood(spn, data, dtype=data.dtype, lls_matrix=lls_per_node)

        gradients = gradient_backward(spn, data, lls_per_node)

        R = lls_per_node[:, 0]

        for sum_node in get_nodes_by_type(spn, Sum):
            RinvGrad = (gradients[sum_node.id] - R)
            for i, c in enumerate(sum_node.children):
                new_w = RinvGrad + lls_per_node[:, c.id] + np.log(sum_node.weights[i])
                sum_node.weights[i] = logsumexp(new_w)
            total_weight = np.sum(sum_node.weights)
            sum_node.weights = (sum_node.weights / total_weight).tolist()
