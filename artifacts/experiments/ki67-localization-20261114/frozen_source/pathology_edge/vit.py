"""Compact, from-scratch ViT-style binary segmentation baseline.

Uses patch tokens and a Transformer encoder, with a per-token pixel head in
place of a classification token. This small segmentation adaptation is not an
official ViT paper reproduction or a pretrained pathology foundation model.
"""

import torch
from torch import nn
from torch.nn import functional as F


class SmallViTSegmenter(nn.Module):
    """Map floating RGB BCHW images to raw B1HW binary segmentation logits.

    Non-overlapping 8x8 patches become 32-dimensional tokens. Each token predicts
    the 64 pixels in its patch. Right/bottom zero padding is removed from the
    output. Learned 2D positions are interpolated for other patch-grid sizes.
    Inputs are limited to 1024 tokens per image; slide inference should use tiles.
    """

    def __init__(self):
        super().__init__()
        config = self.config
        self.patch_size = config["patch_size"]
        self.max_tokens = config["max_tokens"]
        embed_dim = config["embed_dim"]
        reference_grid = config["reference_image_size"] // self.patch_size

        # Kernel == stride: a shared linear projection of flattened RGB patches.
        self.patch_embed = nn.Conv2d(
            3, embed_dim, kernel_size=self.patch_size, stride=self.patch_size
        )
        self.position_embedding = nn.Parameter(
            torch.empty(1, embed_dim, reference_grid, reference_grid)
        )
        nn.init.trunc_normal_(self.position_embedding, std=0.02)
        # Construct layers separately; TransformerEncoder clones one layer and
        # otherwise gives every depth the same initial parameter values.
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=embed_dim,
                nhead=config["num_heads"],
                dim_feedforward=config["mlp_dim"],
                dropout=config["dropout"],
                activation="gelu",
                batch_first=True,
                norm_first=True,
            )
            for _ in range(config["depth"])
        ])
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, self.patch_size ** 2)

    @property
    def config(self):
        """Return a fresh, JSON-serializable description of the fixed design."""
        return {
            "patch_size": 8,
            "embed_dim": 32,
            "depth": 2,
            "num_heads": 4,
            "mlp_dim": 64,
            "dropout": 0.0,
            "reference_image_size": 128,
            "max_tokens": 1024,
            "activation": "gelu",
            "norm_first": True,
            "position_embedding": "learned_2d_bicubic",
            "head": "linear_unpatchify",
        }

    def _unpatchify(self, token_logits, grid_height, grid_width):
        """Restore row-major tokens and row-major pixels to a single-channel image."""
        batch = token_logits.shape[0]
        patches = token_logits.reshape(
            batch, grid_height, grid_width, self.patch_size, self.patch_size
        )
        return patches.permute(0, 1, 3, 2, 4).reshape(
            batch, 1, grid_height * self.patch_size, grid_width * self.patch_size
        )

    def forward(self, x):
        if not isinstance(x, torch.Tensor) or x.ndim != 4:
            raise ValueError("Expected a BCHW tensor of floating RGB images")
        if x.shape[1] != 3 or any(size == 0 for size in x.shape):
            raise ValueError("Expected nonempty BCHW RGB images with three channels")
        if not x.is_floating_point():
            raise ValueError("Expected floating RGB images")

        height, width = x.shape[-2:]
        pad_height = (-height) % self.patch_size
        pad_width = (-width) % self.patch_size
        grid_height = (height + pad_height) // self.patch_size
        grid_width = (width + pad_width) // self.patch_size
        token_count = grid_height * grid_width
        # Check before padding, embedding, or quadratic attention allocations.
        if token_count > self.max_tokens:
            raise ValueError(
                f"Input requires {token_count} tokens, exceeding the "
                f"{self.max_tokens} token limit; use smaller image tiles"
            )
        x = F.pad(x, (0, pad_width, 0, pad_height))
        tokens = self.patch_embed(x).flatten(2).transpose(1, 2)
        positions = self.position_embedding
        if positions.shape[-2:] != (grid_height, grid_width):
            positions = F.interpolate(
                positions, size=(grid_height, grid_width),
                mode="bicubic", align_corners=False,
            )
        tokens = tokens + positions.flatten(2).transpose(1, 2)
        for layer in self.layers:
            tokens = layer(tokens)
        token_logits = self.head(self.norm(tokens))
        logits = self._unpatchify(token_logits, grid_height, grid_width)
        return logits[:, :, :height, :width]
