import re
import tensorflow as tf
import config
import os
# For Japanese tokenizer
import MeCab
from tensorflow.python.platform import gfile

# The data format
#
# (A) data/tweets.txt
#   You have to parepare this file by yourself.
#   This file has many raw tweet and reply pairs. Odd lines are tweets and even lines are replies.
#   example)
#    Line 1: Hey how are you doing?
#    Line 2: @higepon doing good.
#
# Following files are generated by data_processer.py for training.
#
# (B) generated/tweets_enc.txt
#   Each lines consists of one tweet, @username and URL are removed.
#
# (C) generated/tweets_dec.txt
#   Each lines consists of one reply, @username and URL are removed.
#
# (D) generated/tweets_train_[enc|dec].txt
#   Tweets or replies train data
#
# (E) generated/tweets_val_[enc|dec].txt
#   Tweets or replies validation data
#
# (F) generated/vocab_enc.txt
#   Vocabulary for tweets.
#   Words in frequency order
#
# (G) generated/vocab_dec.txt
#   Vocabulary for replies.
#   Words in frequency order
#
# (H) generated/tweets_[train|val]_[dec|enc]_idx.txt
#   Generated from tweets_[train|val]_[enc|dec].txt.
#   All words in the source file are replaced idx to the word.
#

import sys

TWEETS_ENC_TXT = "{0}/tweets_enc.txt".format(config.GENERATED_DIR)
TWEETS_DEC_TXT = "{0}/tweets_dec.txt".format(config.GENERATED_DIR)

TWEETS_TRAIN_ENC_TXT = "{0}/tweets_train_enc.txt".format(config.GENERATED_DIR)
TWEETS_TRAIN_DEC_TXT = "{0}/tweets_train_dec.txt".format(config.GENERATED_DIR)

TWEETS_VAL_ENC_TXT = "{0}/tweets_val_enc.txt".format(config.GENERATED_DIR)
TWEETS_VAL_DEC_TXT = "{0}/tweets_val_dec.txt".format(config.GENERATED_DIR)
TWEETS_VAL_ENC_IDX_TXT = "{0}/tweets_val_enc_idx.txt".format(config.GENERATED_DIR)
TWEETS_VAL_DEC_IDX_TXT = "{0}/tweets_val_dec_idx.txt".format(config.GENERATED_DIR)

DIGIT_RE = re.compile(r"\d")

_PAD = "_PAD"
_GO = "_GO"
_EOS = "_EOS"
_UNK = "_UNK"
_START_VOCAB = [_PAD, _GO, _EOS, _UNK]

PAD_ID = 0
GO_ID = 1
EOS_ID = 2
UNK_ID = 3

tagger = MeCab.Tagger("-Owakati")


def japanese_tokenizer(sentence):
    assert type(sentence) is str
    # Mecab doesn't accept binary, but Python string (utf-8).
    result = tagger.parse(sentence)
    return result.split()


def split_tweets_replies(tweets_path, enc_path, dec_path):
    """Read data from tweets_paths and split it to tweets and replies.

    Args:
      tweets_path: original tweets data
      enc_path: path to write tweets
      dec_path: path to write replies

    Returns:
      None
    """
    i = 1
    with gfile.GFile(tweets_path, mode="rb") as f, gfile.GFile(enc_path, mode="w+") as ef, gfile.GFile(dec_path,
                                                                                                       mode="w+") as df:
        for line in f:
            if not isinstance(line, str):
                line = line.decode('utf-8')
            line = sanitize_line(line)

            # Odd lines are tweets
            if i % 2 == 1:
                ef.write(line)
                # Even lines are replies
            else:
                df.write(line)
            i = i + 1


def sanitize_line(line):
    # Remove @username
    line = re.sub(r"@([A-Za-z0-9_]+)", "", line)
    # Remove URL
    line = re.sub(r'https?:\/\/.*', "", line)
    line = re.sub(DIGIT_RE, "0", line)
    return line


def num_lines(file):
    """Return # of lines in file

    Args:
      file: Target file.

    Returns:
      # of lines in file
    """
    return sum(1 for _ in open(file))


def create_train_validation(source_path, train_path, validation_path, train_ratio=0.75):
    """Split source file into train and validation data

    Args:
      source_path: source file path
      train_path: Path to write train data
      validation_path: Path to write validatio data
      train_ratio: Train data ratio

    Returns:
      None
    """
    nb_lines = num_lines(source_path)
    nb_train = int(nb_lines * train_ratio)
    counter = 0
    with gfile.GFile(source_path, "r") as f, gfile.GFile(train_path, "w") as tf, gfile.GFile(validation_path,
                                                                                             "w") as vf:
        for line in f:
            if counter < nb_train:
                tf.write(line)
            else:
                vf.write(line)
            counter = counter + 1


# Originally from https://github.com/1228337123/tensorflow-seq2seq-chatbot
def sentence_to_token_ids(sentence, vocabulary, tokenizer=japanese_tokenizer, normalize_digits=True):
    if tokenizer:
        words = tokenizer(sentence)
    else:
        words = basic_tokenizer(sentence)
    if not normalize_digits:
        return [vocabulary.get(w, UNK_ID) for w in words]
    # Normalize digits by 0 before looking words up in the vocabulary.
    # return [vocabulary.get(re.sub(_DIGIT_RE, b"0", w), UNK_ID) for w in words] #mark added .decode by Ken
    return [vocabulary.get(w, UNK_ID) for w in words]  # added  by Ken


# Originally from https://github.com/1228337123/tensorflow-seq2seq-chatbot
def data_to_token_ids(data_path, target_path, vocabulary_path,
                      tokenizer=japanese_tokenizer, normalize_digits=True):
    if not gfile.Exists(target_path):
        print("Tokenizing data in %s" % data_path)
        vocab, _ = initialize_vocabulary(vocabulary_path)
        with gfile.GFile(data_path, mode="rb") as data_file:
            with gfile.GFile(target_path, mode="wb") as tokens_file:  # edit w to wb
                counter = 0
                for line in data_file:
#                    line = tf.compat.as_bytes(line)  # added by Ken
                    counter += 1
                    if counter % 100000 == 0:
                        print("  tokenizing line %d" % counter)
                    # line is binary here
                    line = line.decode('utf-8')
                    token_ids = sentence_to_token_ids(line, vocab, tokenizer,
                                                      normalize_digits)
                    tokens_file.write(" ".join([str(tok) for tok in token_ids]) + "\n")


# Originally from https://github.com/1228337123/tensorflow-seq2seq-chatbot
def initialize_vocabulary(vocabulary_path):
    if gfile.Exists(vocabulary_path):
        rev_vocab = []
        with gfile.GFile(vocabulary_path, mode="r") as f:
            rev_vocab.extend(f.readlines())
        rev_vocab = [line.strip() for line in rev_vocab]
        # Dictionary of (word, idx)
        vocab = dict([(x, y) for (y, x) in enumerate(rev_vocab)])
        return vocab, rev_vocab
    else:
        raise ValueError("Vocabulary file %s not found.", vocabulary_path)


# From https://github.com/1228337123/tensorflow-seq2seq-chatbot
def create_vocabulary(source_path, vocabulary_path, max_vocabulary_size, tokenizer=japanese_tokenizer):
    """Create vocabulary file. Please see comments in head for file format

    Args:
      source_path: source file path
      vocabulary_path: Path to write vocabulary
      max_vocabulary_size: Max vocabulary size
      tokenizer: tokenizer used for tokenize each lines

    Returns:
      None
    """
    if gfile.Exists(vocabulary_path):
        print("Found vocabulary file")
        return
    with gfile.GFile(source_path, mode="r") as f:
        counter = 0
        vocab = {}  # (word, word_freq)
        for line in f:
            counter += 1
            words = tokenizer(line)
            if counter % 5000 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
            for word in words:
                # Normalize numbers. Not sure if it's necessary.
                word = re.sub(DIGIT_RE, "0", word)
                if word in vocab:
                    vocab[word] += 1
                else:
                    vocab[word] = 1
        vocab_list = _START_VOCAB + sorted(vocab, key=vocab.get, reverse=True)
        if len(vocab_list) > max_vocabulary_size:
            vocab_list = vocab_list[:max_vocabulary_size]
        with gfile.GFile(vocabulary_path, mode="w") as vocab_file:
            for w in vocab_list:
                vocab_file.write(w + "\n")
        print("\n")


def main(argv):
    if not os.path.exists(config.GENERATED_DIR):
        os.makedirs(config.GENERATED_DIR)
    print("Splitting into tweets and replies...")
    split_tweets_replies(config.TWEETS_TXT, TWEETS_ENC_TXT, TWEETS_DEC_TXT)
    print("Done")

    print("Splitting into train and validation data...")
    create_train_validation(TWEETS_ENC_TXT, TWEETS_TRAIN_ENC_TXT, TWEETS_VAL_ENC_TXT)
    create_train_validation(TWEETS_DEC_TXT, TWEETS_TRAIN_DEC_TXT, TWEETS_VAL_DEC_TXT)
    print("Done")

    print("Creating vocabulary files...")
    create_vocabulary(TWEETS_ENC_TXT, config.VOCAB_ENC_TXT, config.MAX_ENC_VOCABULARY)
    create_vocabulary(TWEETS_DEC_TXT, config.VOCAB_DEC_TXT, config.MAX_DEC_VOCABULARY)
    print("Done")

    print("Creating sentence idx files...")
    data_to_token_ids(TWEETS_TRAIN_ENC_TXT, config.TWEETS_TRAIN_ENC_IDX_TXT, config.VOCAB_ENC_TXT)
    data_to_token_ids(TWEETS_TRAIN_DEC_TXT, config.TWEETS_TRAIN_DEC_IDX_TXT, config.VOCAB_DEC_TXT)
    data_to_token_ids(TWEETS_VAL_ENC_TXT, TWEETS_VAL_ENC_IDX_TXT, config.VOCAB_ENC_TXT)
    data_to_token_ids(TWEETS_VAL_DEC_TXT, TWEETS_VAL_DEC_IDX_TXT, config.VOCAB_DEC_TXT)
    print("Done")


if __name__ == '__main__':
    tf.app.run()
