import cv2 as cv
import numpy as np
import scipy.io as sio
import torch
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
import dlib
from config import device
from misc import ensure_folder
from utils.ddfa import ToTensorGjz, NormalizeGjz
from utils.estimate_pose import parse_pose
from utils.inference import predict_68pts, parse_roi_box_from_bbox, predict_dense, dump_to_ply, get_suffix, get_colors, \
    write_obj_with_colors

if __name__ == '__main__':
    checkpoint = 'BEST_checkpoint.tar'
    print('loading {}...'.format(checkpoint))
    checkpoint = torch.load(checkpoint)
    model = checkpoint['model'].module

    cudnn.benchmark = True
    model = model.to(device)
    model.eval()

    face_detector = dlib.get_frontal_face_detector()
    transform = transforms.Compose([ToTensorGjz(), NormalizeGjz(mean=127.5, std=128)])

    filename = 'images/0008.png'
    img = cv.imread(filename)
    rects = face_detector(img, 1)
    rect = rects[0]
    bbox = [rect.left(), rect.top(), rect.right(), rect.bottom()]
    print('bbox: ' + str(bbox))
    roi_box = parse_roi_box_from_bbox(bbox)
    print('roi_box: ' + str(roi_box))

    img = cv.resize(img, (120, 120), interpolation=cv.INTER_LINEAR)
    input = transform(img).unsqueeze(0)
    input = input.to(device)

    with torch.no_grad():
        param = model(input)
        param = param.squeeze().cpu().numpy().flatten().astype(np.float32)

    print('param: ' + str(param))

    # 68 pts
    # bbox = [0, 0, 120, 120]
    # roi_box = parse_roi_box_from_bbox(bbox)
    pts68 = predict_68pts(param, roi_box)
    # print('pts68: ' + str(pts68))
    print('pts68.shape: ' + str(pts68.shape))

    P, pose = parse_pose(param)
    # print('P: ' + str(P))
    print('P.shape: ' + str(P.shape))
    print('pose: ' + str(pose))

    vertices = predict_dense(param, roi_box)
    # print('vertices: ' + str(vertices))
    print('vertices.shape: ' + str(vertices.shape))

    ensure_folder('result')
    suffix = get_suffix(filename)
    print('suffix: ' + suffix)
    tri = sio.loadmat('visualize/tri.mat')['tri']
    dump_to_ply(vertices, tri, '{}.ply'.format(filename.replace(suffix, '')))

    wfp = '{}.obj'.format(filename.replace(suffix, ''))
    colors = get_colors(img, vertices)
    write_obj_with_colors(wfp, vertices, tri, colors)
    print('Dump obj with sampled texture to {}'.format(wfp))
