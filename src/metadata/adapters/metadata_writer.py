import logging
from concurrent import futures
from odin.adapters.adapter import (ApiAdapter, ApiAdapterRequest, ApiAdapterResponse,
                                   request_types, response_types)
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.util import decode_request_body
from os import path
from json.decoder import JSONDecodeError

import h5py


CONFIG_FILE_NAME = "file_name"
DEFAULT_FILE_NAME = "test_0001.h5"


class MetadataWriterAdapter(ApiAdapter):
    """Metadata Writer Adapter Class for the Odin Server

    """

    def __init__(self, **kwargs):
        """Init the Adapter"""

        super(MetadataWriterAdapter, self).__init__(**kwargs)

        file_name = self.options.get(CONFIG_FILE_NAME, DEFAULT_FILE_NAME)
        metadata = {}
        self.metadata_writer = MetadataWriter(file_name, metadata)


    @response_types("application/json", default="application/json")
    def get(self, path, request, with_metadata=False):
        """
        Handle a HTTP GET request from a client, passing this to the Metadata Writer object.

        :param path: The path to the resource requested by the GET request
        :param request: Additional request parameters
        :return: The requested resource, or an error message and code if the request was invalid.
        """
        try:
            response = self.metadata_writer.get(path, with_metadata)
            status_code = 200
        except ParameterTreeError as err:
            response = {'error': str(err)}
            status_code = 400

        return ApiAdapterResponse(response, content_type='application/json', status_code=status_code)

    @request_types("application/json", "application/vnd.odin-native")
    @response_types("application/json", default="application/json")
    def put(self, path, request):
        """
        Handle a HTTP PUT i.e. set request.

        :param path: the URI path to the resource
        :param data: the data to PUT to the resource
        """
        try:
            data = decode_request_body(request)
            self.metadata_writer.set(path, data)
            response = self.metadata_writer.get(path)
            status_code = 200
        except (ParameterTreeError, JSONDecodeError) as err:
            response = {'error': str(err)}
            status_code = 400

        return ApiAdapterResponse(response, content_type='application/json', status_code=status_code)


class MetadataWriter(object):

    def __init__(self, file_name, metadata_init):

        self.file_name = file_name
        self.metadata_tree = ParameterTree(metadata_init, mutable=True)
        self.dir = ""

        self.param_tree = ParameterTree({
            "name": "Metadata Writer",
            "file": (lambda: self.file_name, self.set_file),
            "file_dir": (lambda: self.dir, self.set_file_dir),
            "metadata": self.metadata_tree,
            "write": (None, self.write_metadata)
        })

        self.status_code = 200
        self.status_message = ""

    def get(self, path, with_metadata=False):
        """
        Handle a HTTP get request.

        Checks if the request is for the image or another resource, and responds accordingly.
        :param path: the URI path to the resource requested
        :param request: Additional request parameters.
        :return: the requested resource,or an error message and code, if the request is invalid.
        """

        return self.param_tree.get(path, with_metadata)

    def set(self, path, data):

        self.param_tree.set(path, data)

    def set_file(self, file_name):
        """
        Set the name of the file. Does not check if the file exists yet, as this could be set before
        the file is created.
        """
        if file_name.endswith((".h5", ".hdf5")):
            self.file_name = file_name

    def set_file_dir(self, dir):
        """
        Set the location of the file. Does not check if the directory exists yet, as this can be set
        before the directory is created if need be.
        """
        self.dir = dir

    def write_metadata(self, data):
        """
        Writes the metadata to the h5 file. Will set the status code to an error if opening the file
        fails
        """
        try:
            file_path = path.join(self.dir, self.file_name)
            logging.debug("Opening file at location %s", file_path)
            hdf_file = h5py.File(file_path, 'r+')
        except IOError as err:
            logging.error("Failed to open file: %s", err)
            return
        try:
            metadata_group = hdf_file.create_group("metadata")
        except ValueError:
            metadata_group = hdf_file["metadata"]
        self.add_metadata_to_group(self.metadata_tree.get(""), metadata_group)

        hdf_file.close()

    def add_metadata_to_group(self, metadata, group):
        """
        This method adds metadata to a metadata group. It allows for recursive calls
        in case nested metadata groups exist
        """
        for key in metadata:
            if isinstance(metadata[key], dict):
                logging.debug("Creating Metadata Subgroup: %s", key)
                try:
                    sub_group = group.create_group(key)
                except ValueError:
                    sub_group = group[key]
                self.add_metadata_to_group(metadata[key], sub_group)
            else:
                logging.debug("Writing metadata to key %s", key)
                group.attrs[key] = metadata[key]
