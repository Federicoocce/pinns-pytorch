from model import PINN
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from train import train
from dataset import DomainDataset, ICDataset


#components: [x, ic_p_0, ic_p_1, ic_p_2, ic_v_0, ic_v_1, ic_v_2, t]
epochs = 100

def hard_constraint(x, y):
    return x[:, 0:1] * (1 - x[:, 0:1]) * y


def pde_fn(prediction, sample):
    grads = torch.zeros_like(prediction)
    grads[:, 0] = 1
    d = torch.autograd.grad(prediction, sample, grad_outputs=grads,create_graph = True)[0]
    dd = torch.autograd.grad(d, sample, grad_outputs=torch.ones_like(d),create_graph = True)[0]
    a = 1
    return dd[:, -1] - a*dd[:, 0]

def interpolate(x, points, ic_points):
    if x in points:
        return ic_points[points.index(x)]
    selected_points = []
    for i in range(len(points)-1):
        if points[i] <= x and points[i+1] >= x:
            selected_points = [i, i+1]
    u_ic= (x - points[selected_points[0]])*(ic_points[selected_points[1]]-ic_points[selected_points[0]])/(points[selected_points[1]] - points[selected_points[0]]) + ic_points[selected_points[0]]
    return u_ic

def ic_fn_pos(prediction, sample):
    x = sample[:, 0]
    points = [0, 0.25, 0.5, 0.75, 1]
    ics = []
    for i in range(x.shape[0]):
        ic_points = [0, sample[i, 1], sample[i, 2], sample[i, 3], 0]
        ic = interpolate(x[i], points, ic_points)
        ics.append(ic)
    ics = torch.Tensor(ics).to(device=prediction.device)#.reshape(prediction.shape)
    return prediction[:, 0], ics

def ic_fn_vel(prediction, sample):
    x = sample[:, 0]
    points = [0, 0.25, 0.5, 0.75, 1]
    ics = []
    for i in range(x.shape[0]):
        ic_points = [0, sample[0][4], sample[0][5], sample[0][6], 0]
        ic = interpolate(x[i], points, ic_points)
        ics.append(ic)
    #dudt = torch.autograd.grad(prediction, sample, grad_outputs=torch.ones_like(prediction),create_graph = True,only_inputs=True)[0][:, -1]
    # dudt = dudt.reshape((1,1))  
    ics = torch.Tensor(ics).to(device=prediction.device)#.reshape(dudt.shape)
    return prediction[:, -1], ics



batchsize = 128
learning_rate = 1e-3 

domainDataset = DomainDataset([0.0]*8, [1.0]*7 + [0.05], 1000)
icDataset = ICDataset([0.0]*8, [1.0]*8, 1000)

model = PINN([8] + [100]*3 + [1], nn.Tanh, hard_constraint).to(torch.device('cuda:0'))

def init_normal(m):
    if type(m) == torch.nn.Linear:
        torch.nn.init.kaiming_normal_(m.weight)

model.apply(init_normal)
# optimizer = optim.Adam(model.parameters(), lr=learning_rate, betas = (0.9,0.99),eps = 10**-15)
optimizer = optim.Adam(model.parameters(), lr=0.01)
# optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)

train("main", model, epochs, batchsize, optimizer, pde_fn, [ic_fn_pos, ic_fn_vel], domainDataset, icDataset)
