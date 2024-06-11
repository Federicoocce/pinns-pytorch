from pinns_v2.model import PINN
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
#from pinns.train import train
from pinns_v2.train import train
from pinns_v2.gradient import _jacobian, _hessian
from pinns_v2.dataset import DomainDataset, ICDataset

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

epochs = 2000
num_inputs = 4 #x, x_f, f, t

u_min = -0.21
u_max = 0.0
x_min = 0.0
x_max = 1.0
t_f = 10
f_min = -3.0
f_max = 0.0
delta_u = u_max - u_min
delta_x = x_max - x_min
delta_f = f_max - f_min

params = {
    "u_min": u_min,
    "u_max": u_max,
    "x_min": x_min,
    "x_max": x_max,
    "t_f": t_f,
    "f_min": f_min,
    "f_max": f_max
}

def hard_constraint(x, y):
    X = x[0]
    tau = x[-1]
    U = ((X-1)*X*(delta_x**2)*t_f*tau)*(y+(u_min/delta_u)) - (u_min/delta_u)
    return U

def f(sample):
    x = sample[0]*(delta_x) + x_min
    x_f = sample[1]*(delta_x) + x_min
    h = sample[2]*(delta_f) + f_min
    
    z = h * torch.exp(-400*((x-x_f)**2))
    return z


def pde_fn(model, sample):
    T = 1
    mu = 1
    k = 1
    alpha_2 = (T/mu)*(t_f**2)/(delta_x**2)
    beta = (t_f**2)/delta_u
    K = k * t_f
    J, d = _jacobian(model, sample)
    dX = J[0][0]
    dtau = J[0][-1]
    H = _jacobian(d, sample)[0]
    ddX = H[0][0, 0]
    ddtau = H[0][-1, -1]
    return ddtau - alpha_2*ddX - beta*f(sample) + K*dtau


def ic_fn_vel(model, sample):
    J, d = _jacobian(model, sample)
    dtau = J[0][-1]
    dt = dtau*delta_u/t_f
    ics = torch.zeros_like(dt)
    return dt, ics


batchsize = 512
learning_rate = 1e-3

print("Building Domain Dataset")
domainDataset = DomainDataset([0.0]*num_inputs,[1.0]*num_inputs, 1024, batchsize=batchsize, period = 3)
print("Building IC Dataset")
icDataset = ICDataset([0.0]*(num_inputs-1),[1.0]*(num_inputs-1), 1024, batchsize=batchsize, period = 3)
print("Building Validation Dataset")
validationDataset = DomainDataset([0.0]*num_inputs,[1.0]*num_inputs, batchsize, shuffle = False)
print("Building Validation IC Dataset")
validationicDataset = ICDataset([0.0]*(num_inputs-1),[1.0]*(num_inputs-1), batchsize, shuffle = False)

model = PINN([num_inputs] + [100]*3 + [1], nn.Tanh, hard_constraint, ff=True, sigma = 0.5)

def init_normal(m):
    if type(m) == torch.nn.Linear:
        torch.nn.init.xavier_uniform_(m.weight)

model = model.apply(init_normal)
model = model.to(device)
# optimizer = optim.Adam(model.parameters(), lr=learning_rate, betas = (0.9,0.99),eps = 10**-15)
optimizer = optim.Adam(model.parameters(), lr=learning_rate)
#scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=20, factor=0.5)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=750, gamma=0.1)
# optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)

data = {
    "name": "string_4inputs_nostiffness_force_damping_ic0hard_icv0_causality_t10.0_rff_0.5",
    #"name": "prova",
    "model": model,
    "epochs": epochs,
    "batchsize": batchsize,
    "optimizer": optimizer,
    "scheduler": scheduler,
    "pde_fn": pde_fn,
    "ic_fns": [ic_fn_vel],
    "eps_time": 100,
    "domain_dataset": domainDataset,
    "ic_dataset": icDataset,
    "validation_domain_dataset": validationDataset,
    "validation_ic_dataset": validationicDataset,
    "additional_data": params
}

train(data)
