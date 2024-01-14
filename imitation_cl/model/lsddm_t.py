import logging
import math

import torch
import torch.nn.functional as F
from torch import nn

logger = logging.getLogger(__file__)

#
# From StableDynamics.ipynb; Zico Kolter
#

# You can use this to compensate for numeric error:
VERIFY = False
V_SCALE = 0.01

global V_WRAP, SCALE_FX
V_WRAP = False
SCALE_FX = False

class Dynamics(nn.Module):
    def __init__(self, fhat, V, alpha=0.01):
        super().__init__()
        self.fhat = fhat
        self.V = V
        self.alpha = alpha

    def forward(self, x):
        fx = self.fhat(x)

        # Insert 1 as the last output
        extra_ones = torch.ones((fx.shape[0], 1)).to(fx.device)
        fx = torch.cat((fx, extra_ones), dim=-1)

        Vx = self.V(x)

        # autograd.grad computes the gradients and returns them without
        # populating the .grad field of the leaves of the computation graph
        gV = torch.autograd.grad([a for a in Vx], [x], create_graph=True, only_inputs=True, allow_unused=True)[0]

        # Implementation of equation 10 from paper
        rv = fx - gV * (F.relu((gV*fx).sum(dim=1) + self.alpha*Vx[:,0])/(gV**2).sum(dim=1))[:,None]

        # Remove the last dimension
        rv = rv[:, :-1]

        return rv

    def get_param_shapes(self):
        param_names = list()
        param_shapes = list()
        for n, p in self.named_parameters():
            if p.requires_grad:
                param_names.append(n)
                param_shapes.append(list(p.shape))
        return param_names, param_shapes

    def set_weights(self, hn_params, param_names):
        """
        Sets the parameters generated by the hypernetwork into the networks
        of this class

        Args:
            hn_params (_type_): _description_
            param_names (_type_): _description_

        Returns:
            _type_: _description_
        """

        for name, value in zip(param_names, hn_params):
            setattr(self, name, value)


class ICNN(nn.Module):
    def __init__(self, layer_sizes, activation=F.relu_):
        super().__init__()
        self.W = nn.ParameterList([nn.Parameter(torch.Tensor(l, layer_sizes[0])) 
                                   for l in layer_sizes[1:]])
        self.U = nn.ParameterList([nn.Parameter(torch.Tensor(layer_sizes[i+1], layer_sizes[i]))
                                   for i in range(1,len(layer_sizes)-1)])
        self.bias = nn.ParameterList([nn.Parameter(torch.Tensor(l)) for l in layer_sizes[1:]])
        self.act = activation
        self.reset_parameters()
        #logger.info(f"Initialized ICNN with {self.act} activation")

    def reset_parameters(self):
        # copying from PyTorch Linear
        for W in self.W:
            nn.init.kaiming_uniform_(W, a=5**0.5)
        for U in self.U:
            nn.init.kaiming_uniform_(U, a=5**0.5)
        for i,b in enumerate(self.bias):
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.W[i])
            bound = 1 / (fan_in**0.5)
            nn.init.uniform_(b, -bound, bound)

    def forward(self, x):
        z = F.linear(x, self.W[0], self.bias[0])
        z = self.act(z)

        for W,b,U in zip(self.W[1:-1], self.bias[1:-1], self.U[:-1]):
            z = F.linear(x, W, b) + F.linear(z, F.softplus(U)) / U.shape[0]
            z = self.act(z)

        return F.linear(x, self.W[-1], self.bias[-1]) + F.linear(z, F.softplus(self.U[-1])) / self.U[-1].shape[0]



class ReHU(nn.Module):
    """ Rectified Huber unit"""
    def __init__(self, d):
        super().__init__()
        self.a = 1/d
        self.b = -d/2

    def forward(self, x):
        return torch.max(torch.clamp(torch.sign(x)*self.a/2*x**2,min=0,max=-self.b),x+self.b)

class MakePSD(nn.Module):
    def __init__(self, f, n, eps=0.01, d=1.0):
        super().__init__()
        self.f = f
        self.zero = torch.nn.Parameter(f(torch.zeros(1,n)), requires_grad=False)
        self.eps = eps
        self.d = d
        self.rehu = ReHU(self.d)

    def forward(self, x):
        smoothed_output = self.rehu(self.f(x) - self.zero)
        quadratic_under = self.eps*(x**2).sum(1,keepdim=True)
        return smoothed_output + quadratic_under

class PosDefICNN(nn.Module):
    def __init__(self, layer_sizes, eps=0.1, negative_slope=0.05):
        super().__init__()
        self.W = nn.ParameterList([nn.Parameter(torch.Tensor(l, layer_sizes[0])) 
                                   for l in layer_sizes[1:]])
        self.U = nn.ParameterList([nn.Parameter(torch.Tensor(layer_sizes[i+1], layer_sizes[i]))
                                   for i in range(1,len(layer_sizes)-1)])
        self.eps = eps
        self.negative_slope = negative_slope
        self.reset_parameters()

    def reset_parameters(self):
        # copying from PyTorch Linear
        for W in self.W:
            nn.init.kaiming_uniform_(W, a=5**0.5)
        for U in self.U:
            nn.init.kaiming_uniform_(U, a=5**0.5)

    def forward(self, x):
        z = F.linear(x, self.W[0])
        F.leaky_relu_(z, negative_slope=self.negative_slope)

        for W,U in zip(self.W[1:-1], self.U[:-1]):
            z = F.linear(x, W) + F.linear(z, F.softplus(U))*self.negative_slope
            z = F.leaky_relu_(z, negative_slope=self.negative_slope)

        z = F.linear(x, self.W[-1]) + F.linear(z, F.softplus(self.U[-1]))
        return F.relu(z) + self.eps*(x**2).sum(1)[:,None]

def loss(Ypred, Yactual, X):
    # Force smoothness in V:
    # penalty for new_V being larget than old V:
    Vloss = torch.tensor(0)
    if SMOOTH_V:
        V = model.V
        # Successor to X:
        succ_X = (X + V_SCALE * Yactual).detach()
        if V_WRAP:
            while torch.any(succ_X < -math.pi):
                succ_X[succ_X < -math.pi] = succ_X[succ_X < -math.pi] + 2 * math.pi
            while torch.any(succ_X >= math.pi):
                succ_X[succ_X >= math.pi] = succ_X[succ_X >= math.pi] - 2 * math.pi
            succ_X.requires_grad_()

        Vloss = (V(succ_X) - V(X)).clamp(min=0).mean()

    l2loss = ((Ypred - Yactual)**2).mean()

    return (l2loss + SMOOTH_V * Vloss, l2loss, Vloss)

global model, SMOOTH_V
model = None
SMOOTH_V = 0

def loss_flatten(l):
    return l

def loss_labels():
    return ["loss", "l2", "V"]

def summary(*a, **kw):
    pass

def configure(props):
    #logger.info(props)
    lsd = int(props["latent_space_dim"])

    # Do we consider an explicit time input
    explicit_time = int(props["explicit_time"])

    #logger.info(f"Set latent space dimenson to {lsd}")

    h_dim = int(props["h"]) if "h" in props else 100
    ph_dim = int(props["hp"]) if "hp" in props else 40
    #logger.info(f"Set hidden layer size to {h_dim} and hidden layer in projection to {ph_dim}")

    if "scale_fx" in props and props["scale_fx"] not in ["false", "False"]:
        #logger.info(f"Scaling fx to prevent errors from too-large steps in Euler integration")
        SCALE_FX = True

    # The function to learn
    # This network can have a direct time input
    # The output is [dot_x0, dot_x1, ..., dot_xn, 1]
    # fhat = nn.Sequential(nn.Linear(lsd+explicit_time, h_dim), nn.ReLU(),
    #                      nn.Linear(h_dim, h_dim), nn.ReLU(),
    #                      nn.Linear(h_dim, h_dim), nn.ReLU(),
    #                      nn.Linear(h_dim, h_dim), nn.ReLU(),
    #                      nn.Linear(h_dim, lsd))

    # Hidden layer dims for fhat is configurable via args
    fhat_layers = int(props["fhat_layers"])
    fhat = nn.Sequential()
    fhat.add_module('layer_0', nn.Linear(lsd+explicit_time, h_dim))
    fhat.add_module('relu_0', nn.ReLU())
    for l in range(1,fhat_layers):
        fhat.add_module(f'layer_{l}', nn.Linear(h_dim, h_dim))
        fhat.add_module(f'relu_{l}', nn.ReLU())
    fhat.add_module('layer_out', nn.Linear(h_dim, lsd))


    ## The convex function to project onto:
    projfn_eps = float(props["projfn_eps"]) if "projfn_eps" in props else 0.01
    pendulum_n =   int(props["pendulum_n"]) if "pendulum_n" in props else None
    if "projfn" in props:
        if props["projfn"] == "PSD-REHU":
            V = MakePSD(ICNN([lsd+explicit_time, ph_dim, ph_dim, 1], activation=ReHU(float(props["rehu"]) if "rehu" in props else 0.01)), lsd+explicit_time, eps=projfn_eps, d=1.0)
        else:
            logger.error(f"Projected function {props['projfn']} does not exist")

    #logger.info(f"Set Lyapunov function to {V} with param eps={projfn_eps}, n={pendulum_n}")

    alpha = float(props["a"]) if "a" in props else 0.01
    #logger.info(f"Set alpha to {alpha}")

    global SMOOTH_V, V_WRAP
    if "wrap" in props:
        V_WRAP = True

    if "smooth_v" in props:
        SMOOTH_V = float(props["smooth_v"])
        #logger.info(f"Set smooth_v loss coeff to {SMOOTH_V}")
        if V_WRAP:
            logger.warning("V_WRAP IS SET; smoothing of V will wrap from -pi to pi")

    global model
    model = Dynamics(fhat, V, alpha=alpha)

    return model
