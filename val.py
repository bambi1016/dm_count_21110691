import argparse
import torch
import os
import numpy as np
import datasets.crowd as crowd
from models import vgg19
import pandas as pd

def run():
    torch.multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description='Test ')
    parser.add_argument('--device', default='0', help='assign device')
    parser.add_argument('--crop-size', type=int, default=512,
                        help='the crop size of the train image')
    parser.add_argument('--model-path', type=str, default='pretrained_models/',
                        help='saved model path')
    parser.add_argument('--data-path', type=str,
                        default='data/ShanghaiTech/part_A/',
                        help='saved model path')
    parser.add_argument('--dataset', type=str, default='sha',
                        help='dataset name: sha, shb')
    parser.add_argument('--pred-density-map-path', type=str, default='',
                        help='save predicted density maps when pred-density-map-path is not empty.')


    args = parser.parse_args()

    os.environ['CUDA_VISIBLE_DEVICES'] = args.device  # set vis gpu
    device = torch.device('cuda')

    model_path = args.model_path
    crop_size = args.crop_size
    data_path = args.data_path

    if args.dataset.lower() == 'sha' or args.dataset.lower() == 'shb':
        dataset = crowd.Crowd_sh(os.path.join(data_path, 'val_data'), crop_size, 8, method='val')
    else:
        raise NotImplementedError
    dataloader = torch.utils.data.DataLoader(dataset, 1, shuffle=False,
                                             num_workers=1, pin_memory=True)

    if args.pred_density_map_path:
        import cv2
        if not os.path.exists(args.pred_density_map_path):
            os.makedirs(args.pred_density_map_path)

    model = vgg19()
    model.to(device)
    model.load_state_dict(torch.load(model_path, device))
    model.eval()
    image_errs = []
    croud_count = []
    for inputs, count, name in dataloader:
        inputs = inputs.to(device)
        assert inputs.size(0) == 1, 'the batch size should equal to 1'
        with torch.set_grad_enabled(False):
            outputs, _ = model(inputs)
        img_err = count[0].item() - torch.sum(outputs).item()

        image_errs.append(img_err)

        if args.pred_density_map_path:
            vis_img = outputs[0, 0].cpu().numpy()
            # normalize density map values from 0 to 1, then map it to 0-255.
            vis_img = (vis_img - vis_img.min()) / (vis_img.max() - vis_img.min() + 1e-5)
            vis_img = (vis_img * 255).astype(np.uint8)
            vis_img = cv2.applyColorMap(vis_img, cv2.COLORMAP_JET)
            cv2.imwrite(os.path.join(args.pred_density_map_path, str(name[0]) + '.png'), vis_img)

        #print('name : {}, Croud Count : {} : '.format(name, torch.sum(outputs).item()))

        #croud_count.append(torch.sum(outputs).item())

    result = pd.DataFrame({'id': range(0, len(croud_count)), 'label': croud_count})

    image_errs = np.array(image_errs)
    mse = np.sqrt(np.mean(np.square(image_errs)))
    mae = np.mean(np.abs(image_errs))
    print('{}: mae {}, mse {}\n'.format(model_path, mae, mse))

    #result.to_csv('result/submission.csv', index=False, encoding='utf-8-sig')

if __name__ == '__main__':
    run()
