import logging
import os
from typing import Optional, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from omegaconf import DictConfig, OmegaConf
from pytorch_lightning.core.lightning import LightningModule
from torch.utils.data import Dataset

from defs.data import build_loaders, build_datasets
from .. import logits_to_scalar, DGCNNHist
from ..metrics.mfpr import MFPR
from ..metrics.mrecall import MRecall
from ..metrics.rmse import MRMSE, Q95RMSE
from ...optim import get_params_for_optimizer
from ...utils.comm import is_main_process, synchronize
from ...utils.hydra import instantiate, call

log = logging.getLogger(__name__)


class DEFPointsRegression(LightningModule):

    def __init__(self, cfg: DictConfig):
        super().__init__()
        self.hparams = cfg
        self.configs = cfg
        self.datasets: Dict[str, Optional[List[Tuple[str, Dataset]]]] = {'train': None, 'val': None, 'test': None}
        self.model = instantiate(self.hparams.model.model_class)
        self.example_input_array = instantiate(self.hparams.model.example_input_array)

        self.save_predictions = self.hparams.datasets.save_predictions
        if self.save_predictions:
            self.save_dir = os.path.join(os.getcwd(), 'predictions')
            if is_main_process() and not os.path.exists(self.save_dir):
                os.mkdir(self.save_dir)
            log.info(f"The predictions will be saved in {self.save_dir}")
            synchronize()

        self.compute_metrics = self.hparams.datasets.compute_metrics
        mrmse_all: Dict[str, nn.ModuleList] = {}
        q95rmse_all: Dict[str, nn.ModuleList] = {}
        mrecall_1r: Dict[str, nn.ModuleList] = {}
        mfpr_1r: Dict[str, nn.ModuleList] = {}
        mrecall_4r: Dict[str, nn.ModuleList] = {}
        mfpr_4r: Dict[str, nn.ModuleList] = {}
        if self.compute_metrics and self.hparams.datasets.val is not None and len(self.hparams.datasets.val) > 0:
            mrmse_all['val'] = nn.ModuleList([MRMSE() for _ in range(len(self.hparams.datasets.val))])
            q95rmse_all['val'] = nn.ModuleList([Q95RMSE() for _ in range(len(self.hparams.datasets.val))])
            mrecall_1r['val'] = nn.ModuleList([MRecall() for _ in range(len(self.hparams.datasets.val))])
            mfpr_1r['val'] = nn.ModuleList([MFPR() for _ in range(len(self.hparams.datasets.val))])
            mrecall_4r['val'] = nn.ModuleList([MRecall() for _ in range(len(self.hparams.datasets.val))])
            mfpr_4r['val'] = nn.ModuleList([MFPR() for _ in range(len(self.hparams.datasets.val))])
        if self.compute_metrics and self.hparams.datasets.test is not None and len(self.hparams.datasets.test) > 0:
            mrmse_all['test'] = nn.ModuleList([MRMSE() for _ in range(len(self.hparams.datasets.test))])
            q95rmse_all['test'] = nn.ModuleList([Q95RMSE() for _ in range(len(self.hparams.datasets.test))])
            mrecall_1r['test'] = nn.ModuleList([MRecall() for _ in range(len(self.hparams.datasets.test))])
            mfpr_1r['test'] = nn.ModuleList([MFPR() for _ in range(len(self.hparams.datasets.test))])
            mrecall_4r['test'] = nn.ModuleList([MRecall() for _ in range(len(self.hparams.datasets.test))])
            mfpr_4r['test'] = nn.ModuleList([MFPR() for _ in range(len(self.hparams.datasets.test))])

        if len(mrecall_4r) > 0:
            self.mrmse_all = nn.ModuleDict(mrmse_all)
            self.q95rmse_all = nn.ModuleDict(q95rmse_all)
            self.mrecall_1r = nn.ModuleDict(mrecall_1r)
            self.mfpr_1r = nn.ModuleDict(mfpr_1r)
            self.mrecall_4r = nn.ModuleDict(mrecall_4r)
            self.mfpr_4r = nn.ModuleDict(mfpr_4r)

    def forward(self, x, clamp=True):
        out: Dict[str, torch.Tensor] = {}

        output = self.model(x)  # (B, N, C)
        for output_element in self.hparams.model.output_elements:
            key = output_element['key']
            left, right = output_element['channel_range']
            out[key] = output[:, :, left:right]

        ##### post-process distances

        # convert logits to scalar if the output is a histogram
        if not self.training and isinstance(self.model, DGCNNHist):
            out['distances'] = logits_to_scalar(out['distances'], self.model.a, self.model.b, self.model.discretization,
                                                self.model.margin)  # (B, N, C) -> (B, N, 1)
        if clamp:
            out['distances'] = out['distances'].clamp(0.0, 1.0)
        out['distances'] = out['distances'].squeeze(2)  # (B, N, 1) -> (B, N)

        ##### post-process normals
        if 'normals' in out:
            assert out['normals'].size(2) == 3
            out['normals'] = F.normalize(out['normals'], dim=2)

        ##### post-process directions
        if 'directions' in out:
            assert out['directions'].size(2) == 3
            out['directions'] = F.normalize(out['directions'], dim=2)

        return out

    def _check_range(self, tensor, left=0.0, right=1.0):
        min_value, max_value = tensor.min().item(), tensor.max().item()
        if not (left <= min_value and max_value <= right):
            log.warning(f"The violation of assumed range: min={min_value}, max={max_value}")

    def training_step(self, batch, batch_idx: int):
        if self.hparams.system.eval_mode:
            self.model.eval()

        self._check_range(batch['distances'])
        outputs = self.forward(batch['points'], clamp=False)

        loss = 0
        loss_dict = {}
        for loss_param in self.hparams.system.losses:
            if loss_param.out_key == 'directions':
                batch_size, num_points = batch['distances'].shape
                mask = (batch['distances'] < 1.0).unsqueeze(2).expand_as(batch['directions'])
                loss_value = call(
                    loss_param.loss_func,
                    torch.masked_select(outputs['directions'], mask),
                    torch.masked_select(batch['directions'], mask), reduction='sum')
                loss_value = loss_value / (batch_size * num_points)
            else:
                loss_value = call(loss_param.loss_func, outputs[loss_param.out_key], batch[loss_param.gt_key])

            loss_dict[loss_param.name] = loss_value  # log original loss value for easy comparison
            loss += loss_value * loss_param['lambda']

        self.log('train_loss', loss, prog_bar=True, sync_dist=True)
        return loss

    def _shared_eval_step(self, batch, batch_idx: int, dataloader_idx: Optional[int], partition: str):
        result = self.forward(batch['points'])

        if self.save_predictions:
            for i, index in enumerate(batch['index']):
                dataset_name, _ = self.datasets[partition][dataloader_idx]
                np.save(os.path.join(self.save_dir, f"{dataset_name}_{index.item()}.npy"),
                        result['distances'][i].cpu().numpy())

        if not self.compute_metrics:
            return
        self._check_range(batch['distances'])
        resolution = self.hparams.datasets.resolution_q
        self.mrmse_all[partition][dataloader_idx].update(result['distances'], batch['distances'])
        self.q95rmse_all[partition][dataloader_idx].update(result['distances'], batch['distances'])
        self.mrecall_1r[partition][dataloader_idx].update(result['distances'] < 1 * resolution, batch['distances'] < 1 * resolution)
        self.mfpr_1r[partition][dataloader_idx].update(result['distances'] < 1 * resolution, batch['distances'] < 1 * resolution)
        self.mrecall_4r[partition][dataloader_idx].update(result['distances'] < 4 * resolution, batch['distances'] < 4 * resolution)
        self.mfpr_4r[partition][dataloader_idx].update(result['distances'] < 4 * resolution, batch['distances'] < 4 * resolution)


    def _shared_eval_epoch_end(self, outputs, partition: str):
        if not self.compute_metrics:
            return
        for i, (dataset_name, _) in enumerate(self.datasets[partition]):
            self.mrmse_all[partition][i].rmse_sum = self.mrmse_all[partition][i].rmse_sum.to(self.device)
            self.mrmse_all[partition][i].total = self.mrmse_all[partition][i].total.to(self.device)
            self.log(f'mRMSE-ALL/{dataset_name}',
                     self.mrmse_all[partition][i].compute(),
                     prog_bar=True, logger=True)

            self.q95rmse_all[partition][i].rmses = self.q95rmse_all[partition][i].rmses.to(self.device)
            self.log(f'q95RMSE-ALL/{dataset_name}',
                     self.q95rmse_all[partition][i].compute(),
                     prog_bar=True, logger=True)

            self.mrecall_1r[partition][i].recall_sum = self.mrecall_1r[partition][i].recall_sum.to(self.device)
            self.mrecall_1r[partition][i].total = self.mrecall_1r[partition][i].total.to(self.device)
            self.log(f'mRecall(1r)/{dataset_name}',
                     self.mrecall_1r[partition][i].compute(),
                     prog_bar=True, logger=True)

            self.mfpr_1r[partition][i].fpr_sum = self.mfpr_1r[partition][i].fpr_sum.to(self.device)
            self.mfpr_1r[partition][i].total = self.mfpr_1r[partition][i].total.to(self.device)
            self.log(f'mFPR(1r)/{dataset_name}',
                     self.mfpr_1r[partition][i].compute(),
                     prog_bar=True, logger=True)

            self.mrecall_4r[partition][i].recall_sum = self.mrecall_4r[partition][i].recall_sum.to(self.device)
            self.mrecall_4r[partition][i].total = self.mrecall_4r[partition][i].total.to(self.device)
            self.log(f'mRecall(4r)/{dataset_name}',
                     self.mrecall_4r[partition][i].compute(),
                     prog_bar=True, logger=True)

            self.mfpr_4r[partition][i].fpr_sum = self.mfpr_4r[partition][i].fpr_sum.to(self.device)
            self.mfpr_4r[partition][i].total = self.mfpr_4r[partition][i].total.to(self.device)
            self.log(f'mFPR(4r)/{dataset_name}',
                     self.mfpr_4r[partition][i].compute(),
                     prog_bar=True, logger=True)
        return {}

    def validation_step(self, batch, batch_idx: int, *args):
        dataloader_idx = args[0] if len(args) == 1 else 0
        return self._shared_eval_step(batch, batch_idx, dataloader_idx, 'val')

    def test_step(self, batch, batch_idx: int, *args):
        dataloader_idx = args[0] if len(args) == 1 else 0
        return self._shared_eval_step(batch, batch_idx, dataloader_idx, 'test')

    def train_epoch_end(self, outputs):
        if self.datasets['train'] is not None:
            for _, dataset in self.datasets['train']:
                dataset.unload()

    def validation_epoch_end(self, outputs):
        if self.datasets['val'] is not None:
            for _, dataset in self.datasets['val']:
                dataset.unload()
        return self._shared_eval_epoch_end(outputs, 'val')

    def test_epoch_end(self, outputs):
        if self.datasets['test'] is not None:
            for _, dataset in self.datasets['test']:
                dataset.unload()
        return self._shared_eval_epoch_end(outputs, 'test')

    # def on_fit_end(self, *args, **kwargs):
    #     for stage in ['train', 'val']:
    #         if self.datasets[stage] is not None:
    #             for _, dataset in self.datasets[stage]:
    #                 dataset.unload()
    #
    # def on_test_end(self, *args, **kwargs):
    #     if self.datasets['test'] is not None:
    #         for _, dataset in self.datasets['test']:
    #             dataset.unload()

    def configure_optimizers(self):
        params = get_params_for_optimizer(self.model, self.hparams.opt.lr, self.hparams.opt.weight_decay,
                                          self.hparams.opt.weight_decay_norm)
        opt_param = OmegaConf.to_container(self.hparams.opt, resolve=True)
        del opt_param['weight_decay']
        del opt_param['weight_decay_norm']
        opt_param = DictConfig(opt_param)
        optimizer = instantiate(opt_param, params=params, lr=self.hparams.opt.lr)
        if 'scheduler' in self.hparams:
            scheduler = instantiate(self.hparams.scheduler, optimizer=optimizer)
            return [optimizer], [scheduler]
        return optimizer

    def train_dataloader(self):
        self.datasets['train'] = build_datasets(self.hparams, 'train')
        loaders = build_loaders(self.hparams, self.datasets['train'], 'train')
        assert len(loaders) == 1, "There must be only one train dataloader"
        return loaders[0]

    def val_dataloader(self):
        self.datasets['val'] = build_datasets(self.hparams, 'val')
        return build_loaders(self.hparams, self.datasets['val'], 'val')

    def test_dataloader(self):
        self.datasets['test'] = build_datasets(self.hparams, 'test')
        return build_loaders(self.hparams, self.datasets['test'], 'test')
