#
# Uber, Inc. (c) 2018
#

import json
import numpy as np
import os
import tensorflow as tf

from neuropods.backends.neuropod_executor import NeuropodExecutor


class TensorflowNeuropodExecutor(NeuropodExecutor):
    """
    Executes a Tensorflow neuropod
    """

    def __init__(self, neuropod_path):
        """
        Load a Tensorflow neuropod

        :param  neuropod_path:  The path to a python neuropod package
        """
        super(TensorflowNeuropodExecutor, self).__init__(neuropod_path)

        # Load the model
        with tf.gfile.GFile(os.path.join(neuropod_path, "0", "data", "model.pb"), "rb") as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())

        # Setup the graph from the definition
        self.graph = tf.Graph()
        with self.graph.as_default():
            tf.import_graph_def(graph_def, name="")

        # Create a session
        self.sess = tf.Session(graph=self.graph)

        # Load the TF specific config
        with open(os.path.join(neuropod_path, "0", "config.json"), "r") as config_file:
            model_config = json.load(config_file)

            # Get the node name mapping and store it
            self.node_name_mapping = model_config["node_name_mapping"]

    def forward(self, inputs):
        """
        Run inference using the specifed inputs.

        :param  inputs:     A dict mapping input names to values. This must match the input
                            spec in the neuropod config for the loaded model.
                            Ex: {'x1': np.array([5]), 'x2': np.array([6])}
                            *Note:* all the keys in this dict must be strings and all the
                            values must be numpy arrays

        :returns:   A dict mapping output names to values. All the keys
                    in this dict are strings and all the values are numpy arrays.
        """

        # get the input and output nodes
        output_dict = {}
        feed_dict = {}

        # Get the output nodes
        for node in self.neuropod_config["output_spec"]:
            neuropod_name = node["name"]

            # Get the graph node
            tf_name = self.node_name_mapping[neuropod_name]
            tf_node = self.graph.get_tensor_by_name(tf_name)

            # Add it to the output nodes
            output_dict[neuropod_name] = tf_node

        # Get the input nodes
        for node in self.neuropod_config["input_spec"]:
            neuropod_name = node["name"]

            # Get the graph node
            tf_name = self.node_name_mapping[neuropod_name]
            tf_node = self.graph.get_tensor_by_name(tf_name)

            # Add it to the feed_dict
            feed_dict[tf_node] = inputs[neuropod_name]

        # Run inference
        outputs = self.sess.run(output_dict, feed_dict=feed_dict)

        # TensorFlow returns string tensors with type object
        for spec in self.neuropod_config["output_spec"]:
            name = spec["name"]
            dtype = np.dtype(spec["dtype"])
            if dtype.type == np.string_ and outputs[name].dtype == 'object' and type(outputs[name].item(0)) == str:
                # If the tensor is supposed to be of type string, is of type object, and contains strings
                outputs[name] = outputs[name].astype('string')

        return outputs
