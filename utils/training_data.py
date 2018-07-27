"""
Generates a training set for training an abnormality detection model from the
data directory specified by the first argument.  This uses the representations
obtained from a device classifier model specified by the second argument to
condition on
"""

import sys
import os
import json
import logging
import pickle

import numpy as np
from .RandomForestModel import RandomForestModel
from .pcap_utils import clean_session_dict
from .pcap_utils import get_source

logging.basicConfig(level=logging.INFO)

# Get model info from config
with open('opts/config.json') as config_file:
    config = json.load(config_file)
    state_size = config['state size']
    duration = config['duration']
    time_const = config['time constant']

def average_representation(rep, timestamp, prev_rep, prev_time):
    """
    Computes the new moving average representation from a single input
    """

    # If no previous info, the average is just the input
    if prev_rep is None or prev_time is None:
        return rep, timestamp

    #Otherwise, compute the moving average
    delta_t = timestamp.timestamp() - prev_time.timestamp()
    alpha = 1 - np.exp(-delta_t/time_const)
    new_rep = prev_rep + alpha*(rep - prev_rep)

    return new_rep, timestamp

def create_dataset(
                    data_dir,
                    model_path='/models/OneLayerModel.pkl'
                  ):
    logger = logging.getLogger(__name__)

    # Load the model
    logger.info("Loading model")
    model = RandomForestModel(duration=None, hidden_size=None)
    model.load(model_path)

    # Get all the pcaps in the training directory
    logger.info("Getting pcaps")
    pcaps = []
    for dirpath, dirnames, filenames in os.walk(data_dir):
        for filename in filenames:
            name, ext = os.path.splitext(filename)
            if ext == '.pcap':
                pcaps.append(os.path.join(dirpath,filename))

    # Get and store the representations using the supplied model
    # Representations will be computed separately for each pcap
    representations = {}
    for pcap in pcaps:
        logger.info("Working on %s", pcap)
        reps, _, timestamps, _, _ = model.get_representation(
                                                            pcap,
                                                            mean=False
                                                                    )
        sessions = model.sessions
        source_address = get_source(sessions)

        # Compute the mean representations
        prev_rep = None
        prev_time = None
        model_outputs = {}

        if timestamps is not None:
            for i, timestamp in enumerate(timestamps):
                rep = reps[i]
                new_rep, time = average_representation(
                                                       rep,
                                                       timestamp,
                                                       prev_rep,
                                                       prev_time
                                                      )
                preds = model.classify_representation(new_rep)
                model_outputs[timestamp] = {
                                            "classification": list(preds),
                                            "representation": list(rep),
                                            "mean representation": list(new_rep)
                                           }
                prev_rep, prev_time = new_rep, time

        # Clean the sessions and merge them into a single session dict
        session_rep_pairs = []
        for session_dict in sessions:
            clean_dict, _ = clean_session_dict(session_dict, source_address)
            # Go through the sessions and pair them with a representation that
            # preceeds them by as little as possible
            for key, value in clean_dict.items():
                first_time = value[0][0].timestamp()
                prior_time = None
                for timestamp in timestamps:
                    time = timestamp.timestamp()
                    if first_time > time:
                        prior_time = timestamp
                if prior_time == None:
                    prior_time = timestamps[0]
                pair = {
                        "model outputs": model_outputs[prior_time],
                        "packets": clean_dict[key],
                        "key": key
                       }
                session_rep_pairs.append(pair)

        representations[pcap] = session_rep_pairs
    byte_size = sys.getsizeof(pickle.dumps(representations))
    logger.info(
                "created training data of size %f mb",
                round(byte_size/1000000, 3)
               )

    return representations
