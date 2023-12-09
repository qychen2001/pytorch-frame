import pytest
import torch
from torch.nn import ReLU

import torch_frame
from torch_frame import NAStrategy, stype
from torch_frame.config import ModelConfig
from torch_frame.config.text_embedder import TextEmbedderConfig
from torch_frame.config.text_tokenizer import TextTokenizerConfig
from torch_frame.data.dataset import Dataset
from torch_frame.data.stats import StatType
from torch_frame.datasets import FakeDataset
from torch_frame.nn import (
    EmbeddingEncoder,
    ExcelFormerEncoder,
    LinearBucketEncoder,
    LinearEmbeddingEncoder,
    LinearEncoder,
    LinearModelEncoder,
    LinearPeriodicEncoder,
    MultiCategoricalEmbeddingEncoder,
    StackEncoder,
    TimestampEncoder,
)
from torch_frame.testing.text_embedder import HashTextEmbedder
from torch_frame.testing.text_tokenizer import (
    RandomTextModel,
    WhiteSpaceHashTokenizer,
)


@pytest.mark.parametrize("encoder_cls_kwargs", [(EmbeddingEncoder, {})])
def test_categorical_feature_encoder(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, with_nan=False)
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.categorical]
    ]
    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.categorical,
        **encoder_cls_kwargs[1],
    )
    feat_cat = tensor_frame.feat_dict[stype.categorical]
    col_names = tensor_frame.col_names_dict[stype.categorical]
    x = encoder(feat_cat, col_names)
    assert x.shape == (feat_cat.size(0), feat_cat.size(1), 8)

    # Perturb the first column
    num_categories = len(stats_list[0][StatType.COUNT])
    feat_cat[:, 0] = (feat_cat[:, 0] + 1) % num_categories
    x_perturbed = encoder(feat_cat, col_names)
    # Make sure other column embeddings are unchanged
    assert (x_perturbed[:, 1:, :] == x[:, 1:, :]).all()


@pytest.mark.parametrize('encoder_cls_kwargs', [
    (LinearEncoder, {}),
    (LinearEncoder, {
        'post_module': ReLU(),
    }),
    (LinearBucketEncoder, {}),
    (LinearBucketEncoder, {
        'post_module': ReLU()
    }),
    (LinearEncoder, {
        'post_module': ReLU()
    }),
    (LinearPeriodicEncoder, {
        'n_bins': 4
    }),
    (LinearPeriodicEncoder, {
        'n_bins': 4,
        'post_module': ReLU(),
    }),
    (ExcelFormerEncoder, {
        'post_module': ReLU(),
    }),
    (StackEncoder, {}),
])
def test_numerical_feature_encoder(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, with_nan=False)
    dataset.materialize()
    tensor_frame = dataset.tensor_frame

    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.numerical]
    ]
    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.numerical,
        **encoder_cls_kwargs[1],
    )
    feat_num = tensor_frame.feat_dict[stype.numerical]
    col_names = tensor_frame.col_names_dict[stype.numerical]
    x = encoder(feat_num, col_names)
    assert x.shape == (feat_num.size(0), feat_num.size(1), 8)
    if "post_module" in encoder_cls_kwargs[1]:
        assert encoder.post_module is not None
    else:
        assert encoder.post_module is None

    # Perturb the first column
    feat_num[:, 0] = feat_num[:, 0] + 10.0
    x_perturbed = encoder(feat_num, col_names)
    # Make sure other column embeddings are unchanged
    assert (x_perturbed[:, 1:, :] == x[:, 1:, :]).all()


@pytest.mark.parametrize(
    "encoder_cls_kwargs",
    [
        (MultiCategoricalEmbeddingEncoder, {
            "mode": "mean"
        }),
        (MultiCategoricalEmbeddingEncoder, {
            "mode": "sum"
        }),
        (MultiCategoricalEmbeddingEncoder, {
            "mode": "max"
        }),
    ],
)
def test_multicategorical_feature_encoder(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10,
                                   stypes=[stype.multicategorical],
                                   with_nan=False)
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.multicategorical]
    ]
    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.multicategorical,
        **encoder_cls_kwargs[1],
    )
    feat_multicat = tensor_frame.feat_dict[stype.multicategorical]
    col_names = tensor_frame.col_names_dict[stype.multicategorical]
    x = encoder(feat_multicat, col_names)
    assert x.shape == (feat_multicat.size(0), feat_multicat.size(1), 8)

    # Perturb the first column
    num_categories = len(stats_list[0][StatType.MULTI_COUNT])
    feat_multicat[:,
                  0].values = (feat_multicat[:, 0].values + 1) % num_categories
    x_perturbed = encoder(feat_multicat, col_names)
    # Make sure other column embeddings are unchanged
    assert (x_perturbed[:, 1:, :] == x[:, 1:, :]).all()


@pytest.mark.parametrize(
    "encoder_cls_kwargs",
    [(
        TimestampEncoder,
        {},
    )],
)
def test_timestamp_feature_encoder(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, stypes=[stype.timestamp])
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.timestamp]
    ]

    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.timestamp,
        **encoder_cls_kwargs[1],
    )
    feat_timestamp = tensor_frame.feat_dict[stype.timestamp]
    col_names = tensor_frame.col_names_dict[stype.timestamp]
    x = encoder(feat_timestamp, col_names)
    assert x.shape == (feat_timestamp.size(0), feat_timestamp.size(1), 8)


@pytest.mark.parametrize('encoder_cls_kwargs', [
    (EmbeddingEncoder, {
        'na_strategy': NAStrategy.MOST_FREQUENT,
    }),
])
def test_categorical_feature_encoder_with_nan(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, with_nan=True)
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.categorical]
    ]

    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.categorical,
        **encoder_cls_kwargs[1],
    )
    feat_cat = tensor_frame.feat_dict[stype.categorical]
    col_names = tensor_frame.col_names_dict[stype.categorical]
    isnan_mask = feat_cat == -1
    x = encoder(feat_cat, col_names)
    assert x.shape == (feat_cat.size(0), feat_cat.size(1), 8)
    # Make sure there's no NaNs in x
    assert (~torch.isnan(x)).all()
    # Make sure original data is not modified
    assert (feat_cat[isnan_mask] == -1).all()


@pytest.mark.parametrize('encoder_cls_kwargs', [
    (LinearEncoder, {
        'na_strategy': NAStrategy.ZEROS,
    }),
    (LinearEncoder, {
        'na_strategy': NAStrategy.MEAN,
    }),
])
def test_numerical_feature_encoder_with_nan(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, with_nan=True)
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.numerical]
    ]
    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.numerical,
        **encoder_cls_kwargs[1],
    )
    feat_num = tensor_frame.feat_dict[stype.numerical]
    col_names = tensor_frame.col_names_dict[stype.numerical]
    isnan_mask = feat_num.isnan()
    x = encoder(feat_num, col_names)
    assert x.shape == (feat_num.size(0), feat_num.size(1), 8)
    # Make sure there's no NaNs in x
    assert (~torch.isnan(x)).all()
    # Make sure original data is not modified
    assert feat_num[isnan_mask].isnan().all()


@pytest.mark.parametrize(
    "encoder_cls_kwargs",
    [(
        MultiCategoricalEmbeddingEncoder,
        {
            "mode": "mean",
            "na_strategy": NAStrategy.ZEROS
        },
    )],
)
def test_multicategorical_feature_encoder_with_nan(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10,
                                   stypes=[stype.multicategorical],
                                   with_nan=True)
    dataset.materialize()
    assert len(dataset.df) != len(dataset.df.dropna())
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.multicategorical]
    ]

    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.multicategorical,
        **encoder_cls_kwargs[1],
    )
    feat_multicat = tensor_frame.feat_dict[stype.multicategorical]
    col_names = tensor_frame.col_names_dict[stype.multicategorical]
    isnan_mask = feat_multicat.values == -1
    x = encoder(feat_multicat, col_names)
    assert x.shape == (feat_multicat.size(0), feat_multicat.size(1), 8)
    # Make sure there's no NaNs in x
    assert (~torch.isnan(x)).all()
    # Make sure original data is not modified
    assert (feat_multicat.values[isnan_mask] == -1).all()


@pytest.mark.parametrize(
    "encoder_cls_kwargs",
    [
        (TimestampEncoder, {
            "na_strategy": NAStrategy.NEWEST_TIMESTAMP
        }),
        (TimestampEncoder, {
            "na_strategy": NAStrategy.MEDIAN_TIMESTAMP
        }),
        (TimestampEncoder, {
            "na_strategy": NAStrategy.OLDEST_TIMESTAMP
        }),
    ],
)
def test_timestamp_feature_encoder_with_nan(encoder_cls_kwargs):
    dataset: Dataset = FakeDataset(num_rows=10, stypes=[stype.timestamp],
                                   with_nan=True)
    dataset.materialize()
    assert len(dataset.df) != len(dataset.df.dropna())
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.timestamp]
    ]
    encoder = encoder_cls_kwargs[0](
        8,
        stats_list=stats_list,
        stype=stype.timestamp,
        **encoder_cls_kwargs[1],
    )
    feat_timestamp = tensor_frame.feat_dict[stype.timestamp]
    col_names = tensor_frame.col_names_dict[stype.timestamp]
    x = encoder(feat_timestamp, col_names)
    assert x.shape == (feat_timestamp.size(0), feat_timestamp.size(1), 8)
    assert (~torch.isnan(x)).all()


def test_text_embedded_encoder():
    num_rows = 20
    text_emb_channels = 10
    out_channels = 5
    dataset = FakeDataset(
        num_rows=num_rows,
        stypes=[
            torch_frame.text_embedded,
        ],
        col_to_text_embedder_cfg=TextEmbedderConfig(
            text_embedder=HashTextEmbedder(text_emb_channels),
            batch_size=None),
    )
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.text_embedded]
    ]
    encoder = LinearEmbeddingEncoder(
        out_channels=out_channels,
        stats_list=stats_list,
        stype=stype.text_embedded,
    )
    feat_text = tensor_frame.feat_dict[stype.text_embedded]
    col_names = tensor_frame.col_names_dict[stype.text_embedded]
    feat = encoder(feat_text, col_names)
    assert feat.shape == (
        num_rows,
        len(tensor_frame.col_names_dict[stype.text_embedded]),
        out_channels,
    )


def test_embedding_encoder():
    num_rows = 20
    out_channels = 5
    dataset = FakeDataset(
        num_rows=num_rows,
        stypes=[
            torch_frame.embedding,
        ],
    )
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.embedding]
    ]
    encoder = LinearEmbeddingEncoder(
        out_channels=out_channels,
        stats_list=stats_list,
        stype=stype.embedding,
    )
    feat_text = tensor_frame.feat_dict[stype.embedding]
    col_names = tensor_frame.col_names_dict[stype.embedding]
    x = encoder(feat_text, col_names)
    assert x.shape == (
        num_rows,
        len(tensor_frame.col_names_dict[stype.embedding]),
        out_channels,
    )


def test_text_tokenized_encoder():
    num_rows = 20
    num_hash_bins = 10
    out_channels = 5
    text_emb_channels = 15
    dataset = FakeDataset(
        num_rows=num_rows,
        stypes=[
            torch_frame.text_tokenized,
        ],
        col_to_text_tokenizer_cfg=TextTokenizerConfig(
            text_tokenizer=WhiteSpaceHashTokenizer(
                num_hash_bins=num_hash_bins),
            batch_size=None,
        ),
    )
    dataset.materialize()
    tensor_frame = dataset.tensor_frame
    stats_list = [
        dataset.col_stats[col_name]
        for col_name in tensor_frame.col_names_dict[stype.text_tokenized]
    ]
    model = RandomTextModel(text_emb_channels=text_emb_channels)
    col_to_model_cfg = {
        col_name: ModelConfig(model=model, out_channels=text_emb_channels)
        for col_name in tensor_frame.col_names_dict[stype.text_tokenized]
    }
    encoder = LinearModelEncoder(
        out_channels=out_channels,
        stats_list=stats_list,
        stype=stype.text_tokenized,
        col_to_model_cfg=col_to_model_cfg,
    )
    feat_text = tensor_frame.feat_dict[stype.text_tokenized]
    col_names = tensor_frame.col_names_dict[stype.text_tokenized]
    x = encoder(feat_text, col_names)
    assert x.shape == (
        num_rows,
        len(tensor_frame.col_names_dict[stype.text_tokenized]),
        out_channels,
    )
