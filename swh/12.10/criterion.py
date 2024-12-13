import torch
import torch.nn as nn
import torch.autograd as autograd
import torch.nn.functional as F
from torchmetrics.image import StructuralSimilarityIndexMeasure as ssim
import numpy as np

def gradient_penalty(D, real_samples, fake_samples, device):
    # 生成插值样本
    alpha = torch.rand(real_samples.size(0), 1, 1, 1).to(device)
    interpolates = (alpha * real_samples + ((1 - alpha) * fake_samples)).requires_grad_(True).to(device)
    
    # 计算判别器对插值样本的输出
    p_logits = D(interpolates)
    
    # 计算梯度
    gradients = autograd.grad(
        outputs=p_logits,
        inputs=interpolates,
        grad_outputs=torch.ones(p_logits.size()).to(device),
        create_graph=True,
        retain_graph=True,
        only_inputs=True
    )[0]
    
    # 计算梯度的L2范数
    gradients = gradients.view(gradients.size(0), -1)
    gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean()
    
    return gradient_penalty

def smoothing_loss(y_pred):
    dy = torch.abs(y_pred[:, :, 1:, :] - y_pred[:, :, :-1, :])
    dx = torch.abs(y_pred[:, :, :, 1:] - y_pred[:, :, :, :-1])

    dx = dx*dx
    dy = dy*dy
    grad = torch.mean(dx) + torch.mean(dy)
 
    return grad

# Discriminator Loss
def discriminator_loss(real_logit, fake_logit):
    real_loss = torch.mean(real_logit)
    fake_loss = torch.mean(fake_logit)
    # real_loss = (torch.mean(real_logit) - 1)**2
    # fake_loss = (torch.mean(fake_logit))**2
    # discriminator_loss = real_loss + fake_loss + gp_loss
    # gp_loss = lambda_gp * gradient_penalty
    discriminator_loss = -real_loss + fake_loss
    return discriminator_loss

# Generator Loss
def generator_loss(fake_logit):
    gen_loss = -torch.mean(fake_logit)
    # fake_loss = (torch.mean(fake_logit)-1)**2
    return gen_loss


# Correction Loss
def compute_edge(image, kernel = 'sobel', threshold=2):   
    """
    使用PyTorch计算水平和垂直梯度。
    :param image: 输入图像 (torch.Tensor, 形状 [B, 1, H, W])
    :param kernel: 梯度核，可选 'sobel' , 'prewitt' 或 'scharr',
    :return: grad_magnitude
    """

    sobel_kernel_x = torch.tensor([[-1, 0, 1], 
                                   [-2, 0, 2], 
                                   [-1, 0, 1]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)
    sobel_kernel_y = torch.tensor([[-1, -2, -1], 
                                   [0,  0,  0], 
                                   [1,  2,  1]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)


    prewitt_kernel_x = torch.tensor([[-1, -1, -1], 
                                   [0, 0, 0], 
                                   [1, 1, 1]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)
    prewitt_kernel_y = torch.tensor([[-1, 0, 1], 
                                   [-1,  0,  1], 
                                   [-1,  0,  1]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)


    scharr_kernel_x = torch.tensor([[-3, 0, 3], 
                                   [-10, 0, 10], 
                                   [-3, 0, 3]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)
    scharr_kernel_y = torch.tensor([[-3, -10, -3], 
                                   [0,  0,  0], 
                                   [3,  10,  3]], dtype=torch.float32, device=image.device).view(1, 1, 3, 3)

    # gaussian = gaussian_kernel(3, 1).unsqueeze(0).unsqueeze(0)
    # image = F.conv2d(image, gaussian, padding=1)

    if kernel == 'sobel':
        gx = F.conv2d(image, sobel_kernel_x, padding=1)  # 水平梯度
        gy = F.conv2d(image, sobel_kernel_y, padding=1)  # 垂直梯度
    elif kernel == 'prewitt':
        gx = F.conv2d(image, prewitt_kernel_x, padding=1)  # 水平梯度
        gy = F.conv2d(image, prewitt_kernel_y, padding=1)  # 垂直梯度
    elif kernel == 'scharr':
        gx = F.conv2d(image, scharr_kernel_x, padding=1)  # 水平梯度
        gy = F.conv2d(image, scharr_kernel_y, padding=1)  # 垂直梯度
    else:
        raise ValueError("Invalid kernel type. Supported types are 'sobel', 'prewitt', and 'shcarr'.")
    
    grad_magnitude = torch.sqrt(gx**2 + gy**2)
        
    strong_edges = grad_magnitude > threshold
    grad_magnitude = grad_magnitude * strong_edges.float()
    return grad_magnitude


def ssim_metric(target: object, prediction: object):
    cur_ssim = ssim(data_range=target.max() - target.min())
    return cur_ssim(target, prediction)

def psnr(img1, img2, max_val=torch.tensor(1.0)):
    mse = F.mse_loss(img1, img2).mean()
    # psnr = 20 * torch.log10(max_val) - 10 * torch.log10(mse)
    psnr = - 10 * torch.log10(mse)
    return psnr

def mse(img1, img2):
    return torch.mean((img1 - img2)**2)

def semantic_loss(pred:list, target:list):
    loss = torch.mean(torch.stack([F.cross_entropy(p, t) for p, t in zip(pred, target)]))
    return torch.mean()