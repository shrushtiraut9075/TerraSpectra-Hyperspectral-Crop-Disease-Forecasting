from typing import Optional, Tuple

import torch
import torch.nn as nn


class TransformerEncoderLayer(nn.Module):
    """Pre-norm Transformer Encoder Layer with attention weight output."""

    def __init__(
        self, d_model: int = 128, n_heads: int = 4, mlp_ratio: float = 2.0, dropout: float = 0.1
    ):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.mha = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model)

        mlp_dim = int(d_model * mlp_ratio)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, mlp_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_dim, d_model),
            nn.Dropout(dropout),
        )

    def forward(
        self, x: torch.Tensor, return_attn: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        # Pre-norm attention
        norm_x = self.norm1(x)
        attn_out, attn_weights = self.mha(
            norm_x, norm_x, norm_x, need_weights=return_attn, average_attn_weights=True
        )
        x = x + attn_out
        # Pre-norm MLP
        x = x + self.mlp(self.norm2(x))
        return x, attn_weights


class ViTEncoder(nn.Module):
    """Vision Transformer Encoder across sequence of spatial-spectral tokens."""

    def __init__(
        self,
        seq_len: int,
        d_model: int = 128,
        n_layers: int = 4,
        n_heads: int = 4,
        mlp_ratio: float = 2.0,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.d_model = d_model

        # Learned [CLS] token and positional embedding
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        self.pos_embed = nn.Parameter(torch.zeros(1, seq_len + 1, d_model))
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

        self.pos_drop = nn.Dropout(p=dropout)

        self.layers = nn.ModuleList(
            [
                TransformerEncoderLayer(
                    d_model=d_model, n_heads=n_heads, mlp_ratio=mlp_ratio, dropout=dropout
                )
                for _ in range(n_layers)
            ]
        )
        self.norm = nn.LayerNorm(d_model)

    def forward(
        self, token_embeddings: torch.Tensor, return_attn: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        # token_embeddings: (N, seq_len, d_model)
        b = token_embeddings.shape[0]
        cls_tokens = self.cls_token.expand(b, -1, -1)  # (N, 1, d_model)
        x = torch.cat((cls_tokens, token_embeddings), dim=1)  # (N, seq_len + 1, d_model)
        x = self.pos_drop(x + self.pos_embed[:, : x.size(1), :])

        last_attn = None
        for i, layer in enumerate(self.layers):
            is_last = i == len(self.layers) - 1
            x, attn = layer(x, return_attn=(return_attn and is_last))
            if is_last and return_attn:
                last_attn = attn

        x = self.norm(x)
        cls_out = x[:, 0]  # (N, d_model)
        return cls_out, last_attn
