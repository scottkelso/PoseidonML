import os
import sys
import json
import logging
import numpy as np
import tensorflow as tf
from pkg_resources import working_set
from pkg_resources import Requirement
from .SoSmodel import SoSModel
from .session_sequence import create_dataset
from .session_iterator import BatchIterator

logging.basicConfig(level=logging.INFO)
tf.logging.set_verbosity(tf.logging.ERROR)


def eval_pcap(pcap, labels, time_const, label=None, rnn_size=100):
    logger = logging.getLogger(__name__)
    data = create_dataset(pcap, time_const, label=label)
    # Create an iterator
    iterator = BatchIterator(
                             data,
                             labels,
                             perturb_types=['random data']
                            )
    logger.debug("Created iterator")
    rnnmodel = SoSModel(rnn_size=rnn_size)
    logger.debug("Created model")
    rnnmodel.load(os.path.join(working_set.find(Requirement.parse('poseidonml')).location, 'poseidonml/models/SoSmodel'))
    logger.debug("Loaded model")

    X_list = iterator.X
    L_list = iterator.L
    sessions = iterator.sessions

    num_total = 0
    max_score = 0
    scores = {}
    for i, X in enumerate(X_list):
        L = L_list[i]
        out = rnnmodel.get_output(
                                    np.expand_dims(X, axis=0),
                                    np.expand_dims(L, axis=0),
                                 )
        for j,o in enumerate(out):
            for k,s in enumerate(o):
                num_total += 1
                session = sessions[i][k]['session info']
                p = session['protocol']
                if p == '06': p = 'TCP'
                if p == '17': p = 'UDP'
                if p == '01': p = 'ICMP'
                flowlike = p + ' '
                if session['initiated by source']:
                    flowlike += session['source']+' to '+session['destination']
                else:
                    flowlike += session['destination']+' to '+session['source']
                scores[num_total] = str(s)
                if s > max_score:
                    max_score = s

    return max_score

if __name__ == '__main__':
    # Path to training data
    pcap = sys.argv[1]
    if len(sys.argv) == 3:
        label = sys.argv[2]
    else:
        label = None

    # Load info from config
    with open('opts/config.json') as config_file:
        config = json.load(config_file)
        rnn_size = config['rnn size']
        labels = config['labels']
        time_const = config['time constant']

    mean_score = eval_pcap(pcap, labels, time_const, label=label, rnn_size=rnn_size)
    print(mean_score)
