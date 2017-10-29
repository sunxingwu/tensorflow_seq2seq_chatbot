import tensorflow as tf

import config
import data_processer
import train


def main(_):
    with tf.Session() as session:
        beam_search = False
        model = train.create_or_restore_model(session,
                                              config.buckets,
                                              forward_only=False,  # This should work for both True and False
                                              beam_search=beam_search,  # False for simple debug
                                              beam_size=config.beam_size)

        enc_vocab, _ = data_processer.initialize_vocabulary(config.VOCAB_ENC_TXT)
        dec_vocab, _ = data_processer.initialize_vocabulary(config.VOCAB_DEC_TXT)

        log_prob = train.log_prob(session, model, enc_vocab, dec_vocab, "hige", "ますです")
        print(log_prob)


if __name__ == '__main__':
    tf.app.run()
