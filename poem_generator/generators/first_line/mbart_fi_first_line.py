import logging
from typing import List

import torch
from transformers import (
    MBartTokenizer,
    MBartForConditionalGeneration,
)

from poem_generator.io.candidates import PoemLine, PoemLineList
from poem_generator.utils import remove_punct

# This file contains the code for generating the next line with all supported models.
# In future, it can become a package with several file (one for each implementation)

BASE_MODEL = "facebook/mbart-large-cc25"
MODEL_FILE = "models/first-line-fi-20-epochs/pytorch_model.bin"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def get_tokenizer():
    tokenizer = MBartTokenizer.from_pretrained(
        BASE_MODEL,
        src_lang="fi_FI",
        tgt_lang="fi_FI",
    )

    return tokenizer

def get_model():
    tokenizer = MBartTokenizer.from_pretrained(
        BASE_MODEL,
        src_lang="fi_FI",
        tgt_lang="fi_FI",
    )

    logging.info("Loading base model {}".format(BASE_MODEL))
    model = MBartForConditionalGeneration.from_pretrained(BASE_MODEL)
    model.config.decoder_start_token_id = tokenizer.lang_code_to_id["fi_FI"]

    model.resize_token_embeddings(len(tokenizer))  # is this really necessary here?
    logging.info("Model vocab size is {}".format(model.config.vocab_size))
    model.load_state_dict(torch.load(MODEL_FILE, map_location=torch.device(DEVICE)))
    model.to(DEVICE)

    return model


def filter_candidates(candidates: List[str]):
    out = [
        candidate for candidate in candidates if remove_punct(candidate)
    ]  # make sure that lines containing only punctuation are excluded
    return list(set(out))


def generate(keywords, tokenizer, model) -> PoemLineList:
    """
    Implementation of the first line poem generator using mbart for Finnish language
    :return:
    """
    source = keywords
    encoded = tokenizer.encode(
        source, padding="max_length", max_length=32, truncation=True
    )
    encoded = torch.tensor(encoded).unsqueeze(0).to(DEVICE)

    sample_outputs = model.generate(
        encoded,
        do_sample=True,
        max_length=16,
        num_beams=5,
        # repetition_penalty=5.0,
        early_stopping=True,
        num_return_sequences=5,
    )

    candidates = [
        tokenizer.decode(sample_output, skip_special_tokens=True)
        for sample_output in sample_outputs
    ]
    logging.info("Generated candidates {}".format(candidates))

    return PoemLineList(
        [PoemLine(text=candidate) for candidate in filter_candidates(candidates)]
    )